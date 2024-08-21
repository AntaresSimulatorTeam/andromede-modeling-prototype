# Copyright (c) 2024, RTE (https://www.rte-france.com)
#
# See AUTHORS.txt
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# SPDX-License-Identifier: MPL-2.0
#
# This file is part of the Antares project.

"""
The optimization module contains the logic to translate the input model
into a mathematical optimization problem.
"""

import math
from dataclasses import dataclass

import ortools.linear_solver.pywraplp as lp

from andromede.expression.indexing import IndexingStructureProvider
from andromede.expression.indexing_structure import IndexingStructure
from andromede.expression.linear_expression_efficient import (
    LinearExpressionEfficient,
    RowIndex,
)
from andromede.model.common import ValueType
from andromede.model.constraint import Constraint
from andromede.model.model import PortFieldId
from andromede.study.data import DataBase
from andromede.study.network import Component, Network

from .linear_expression_resolver import LinearExpressionResolver
from .optimization_context import (
    BlockBorderManagement,
    ComponentContext,
    OptimizationContext,
    make_data_structure_provider,
    make_value_provider,
)
from .resolved_linear_expression import ResolvedLinearExpression
from .strategy import MergedProblemStrategy, ModelSelectionStrategy
from .time_block import TimeBlock


def _get_indexing(
    constraint: Constraint, provider: IndexingStructureProvider
) -> IndexingStructure:
    return (
        constraint.expression.compute_indexation(provider)
        or constraint.lower_bound.compute_indexation(provider)
        or constraint.upper_bound.compute_indexation(provider)
    )


def _compute_indexing_structure(
    context: ComponentContext, constraint: Constraint
) -> IndexingStructure:
    data_structure_provider = make_data_structure_provider(
        context.opt_context.network, context.component
    )
    constraint_indexing = _get_indexing(constraint, data_structure_provider)
    return constraint_indexing


def _instantiate_model_expression(
    model_expression: LinearExpressionEfficient,
    component_id: str,
    optimization_context: OptimizationContext,
) -> LinearExpressionEfficient:
    """
    Performs common operations that are necessary on model expressions before their actual use:
     1. add component ID for variables and parameters of THIS component
     2. replace port fields by their definition
    """
    # We need to resolve ports before adding component context as binding constraints with ports may involve parameters from the current component
    with_ports = model_expression.resolve_port(
        component_id, optimization_context.connection_fields_expressions
    )
    with_component_and_ports = with_ports.add_component_context(component_id)
    return with_component_and_ports


def _create_constraint(
    solver: lp.Solver,
    context: ComponentContext,
    constraint: Constraint,
) -> None:
    """
    Adds a component-related constraint to the solver.
    """
    constraint_indexing = _compute_indexing_structure(context, constraint)

    value_provider = make_value_provider(context.opt_context, context.component)
    expression_resolver = LinearExpressionResolver(context.opt_context, value_provider)

    for block_timestep in context.opt_context.get_time_indices(constraint_indexing):
        for scenario in context.opt_context.get_scenario_indices(constraint_indexing):
            row_id = RowIndex(block_timestep, scenario)

            resolved_expr = expression_resolver.resolve(constraint.expression, row_id)
            resolved_lb = expression_resolver.resolve_constant_expr(
                constraint.lower_bound, row_id
            )
            resolved_ub = expression_resolver.resolve_constant_expr(
                constraint.upper_bound, row_id
            )

            # What happens if there is some time_operator in the bounds ? -> Pb réglé avec le nouveau design !
            constraint_data = ConstraintData(
                name=constraint.name,
                lower_bound=resolved_lb,
                upper_bound=resolved_ub,
                expression=resolved_expr,
            )
            make_constraint(solver, row_id, constraint_data)


def _create_objective(
    solver: lp.Solver,
    opt_context: OptimizationContext,
    component: Component,
    objective_contribution: LinearExpressionEfficient,
) -> None:
    instantiated_expr = _instantiate_model_expression(
        objective_contribution, component.id, opt_context
    )
    # We have already checked in the model creation that the objective contribution is neither indexed by time nor by scenario

    value_provider = make_value_provider(opt_context, component)
    expression_resolver = LinearExpressionResolver(opt_context, value_provider)
    resolved_expr = expression_resolver.resolve(instantiated_expr, RowIndex(0, 0))

    obj: lp.Objective = solver.Objective()
    for term in resolved_expr.terms:
        opt_context._solver_variables[term.variable].is_in_objective = True
        obj.SetCoefficient(
            term.variable,
            obj.GetCoefficient(term.variable) + term.coefficient,
        )

    # This should have no effect on the optimization
    obj.SetOffset(resolved_expr.constant + obj.offset())


@dataclass
class ConstraintData:
    name: str
    lower_bound: float
    upper_bound: float
    expression: ResolvedLinearExpression


def make_constraint(
    solver: lp.Solver,
    row_id: RowIndex,
    data: ConstraintData,
) -> lp.Constraint:
    """
    Adds constraint to the solver.
    """

    constraint_name = f"{data.name}_{str(row_id)}"

    solver_constraint: lp.Constraint = solver.Constraint(constraint_name)
    constant: float = 0

    for term in data.expression.terms:
        solver_constraint.SetCoefficient(
            term.variable,
            term.coefficient + solver_constraint.GetCoefficient(term.variable),
        )
    constant += data.expression.constant

    solver_constraint.SetBounds(
        data.lower_bound - constant, data.upper_bound - constant
    )

    return solver_constraint


class OptimizationProblem:
    name: str
    solver: lp.Solver
    context: OptimizationContext
    strategy: ModelSelectionStrategy

    def __init__(
        self,
        name: str,
        solver: lp.Solver,
        opt_context: OptimizationContext,
        build_strategy: ModelSelectionStrategy = MergedProblemStrategy(),
    ) -> None:
        self.name = name
        self.solver = solver
        self.context = opt_context
        self.strategy = build_strategy

        self._register_connection_fields_definitions()
        self._create_variables()
        self._create_constraints()
        self._create_objectives()

    def _register_connection_fields_definitions(self) -> None:
        for cnx in self.context.network.connections:
            for field_name in list(cnx.master_port.keys()):
                master_port = cnx.master_port[field_name]
                port_definition = (
                    master_port.component.model.port_fields_definitions.get(
                        PortFieldId(
                            port_name=master_port.port_id, field_name=field_name.name
                        )
                    )
                )
                expression_node = port_definition.definition  # type: ignore
                instantiated_expression = expression_node.add_component_context(
                    master_port.component.id
                )
                self.context.register_connection_fields_expressions(
                    component_id=cnx.port1.component.id,
                    port_name=cnx.port1.port_id,
                    field_name=field_name.name,
                    expression=instantiated_expression,
                )
                self.context.register_connection_fields_expressions(
                    component_id=cnx.port2.component.id,
                    port_name=cnx.port2.port_id,
                    field_name=field_name.name,
                    expression=instantiated_expression,
                )

    def _create_variables(self) -> None:
        for component in self.context.network.all_components:
            component_context = self.context.get_component_context(component)
            model = component.model

            value_provider = make_value_provider(self.context, component)
            expression_resolver = LinearExpressionResolver(self.context, value_provider)

            for model_var in self.strategy.get_variables(model):
                var_indexing = model_var.structure
                instantiated_lb_expr = None
                instantiated_ub_expr = None

                if model_var.lower_bound:
                    instantiated_lb_expr = _instantiate_model_expression(
                        model_var.lower_bound, component.id, self.context
                    )
                if model_var.upper_bound:
                    instantiated_ub_expr = _instantiate_model_expression(
                        model_var.upper_bound, component.id, self.context
                    )

                var_name: str = f"{model_var.name}"
                component_prefix = f"{component.id}_" if component.id else ""

                for block_timestep in self.context.get_time_indices(var_indexing):
                    block_suffix = (
                        f"_t{block_timestep}"
                        if var_indexing.is_time_varying()
                        and (self.context.block_length() > 1)
                        else ""
                    )

                    for scenario in self.context.get_scenario_indices(var_indexing):
                        lower_bound = -self.solver.infinity()
                        upper_bound = self.solver.infinity()
                        if instantiated_lb_expr:
                            lower_bound = expression_resolver.resolve_constant_expr(
                                instantiated_lb_expr, RowIndex(block_timestep, scenario)
                            )
                        if instantiated_ub_expr:
                            upper_bound = expression_resolver.resolve_constant_expr(
                                instantiated_ub_expr, RowIndex(block_timestep, scenario)
                            )

                        scenario_suffix = (
                            f"_s{scenario}"
                            if var_indexing.is_scenario_varying()
                            and (self.context.scenarios > 1)
                            else ""
                        )

                        # Set solver var name
                        # Externally, for the Solver, this variable will have a full name
                        # Internally, it will be indexed by a structure that into account
                        # the component id, variable name, timestep and scenario separately
                        solver_var = None
                        solver_var_name = f"{component_prefix}{var_name}{block_suffix}{scenario_suffix}"

                        if math.isclose(lower_bound, upper_bound):
                            raise ValueError(
                                f"Upper and lower bounds of variable {solver_var_name} have the same value: {lower_bound}"
                            )
                        elif lower_bound > upper_bound:
                            raise ValueError(
                                f"Upper bound ({upper_bound}) must be strictly greater than lower bound ({lower_bound}) for variable {solver_var_name}"
                            )

                        if model_var.data_type == ValueType.BOOL:
                            solver_var = self.solver.BoolVar(
                                solver_var_name,
                            )
                        elif model_var.data_type == ValueType.INTEGER:
                            solver_var = self.solver.IntVar(
                                lower_bound,
                                upper_bound,
                                solver_var_name,
                            )
                        else:
                            solver_var = self.solver.NumVar(
                                lower_bound,
                                upper_bound,
                                solver_var_name,
                            )

                        component_context.add_variable(
                            block_timestep, scenario, model_var.name, solver_var
                        )

    def _create_constraints(self) -> None:
        for component in self.context.network.all_components:
            for constraint in self.strategy.get_constraints(component.model):
                instantiated_expr = _instantiate_model_expression(
                    constraint.expression, component.id, self.context
                )
                instantiated_lb = _instantiate_model_expression(
                    constraint.lower_bound, component.id, self.context
                )
                instantiated_ub = _instantiate_model_expression(
                    constraint.upper_bound, component.id, self.context
                )

                instantiated_constraint = Constraint(
                    name=f"{component.id}_{constraint.name}",
                    expression=instantiated_expr,
                    lower_bound=instantiated_lb,
                    upper_bound=instantiated_ub,
                )
                _create_constraint(
                    self.solver,
                    self.context.get_component_context(component),
                    instantiated_constraint,
                )

    def _create_objectives(self) -> None:
        for component in self.context.network.all_components:
            component_context = self.context.get_component_context(component)
            model = component.model

            for objective in self.strategy.get_objectives(model):
                if objective is not None:
                    _create_objective(
                        self.solver,
                        self.context,
                        component,
                        objective,
                    )

    def export_as_mps(self) -> str:
        return self.solver.ExportModelAsMpsFormat(fixed_format=True, obfuscated=False)

    def export_as_lp(self) -> str:
        return self.solver.ExportModelAsLpFormat(obfuscated=False)


def build_problem(
    network: Network,
    database: DataBase,
    block: TimeBlock,
    scenarios: int,
    *,
    problem_name: str = "optimization_problem",
    border_management: BlockBorderManagement = BlockBorderManagement.CYCLE,
    solver_id: str = "SCIP",
    problem_strategy: ModelSelectionStrategy = MergedProblemStrategy(),
) -> OptimizationProblem:
    """
    Entry point to build the optimization problem for a time period.
    """
    solver: lp.Solver = lp.Solver.CreateSolver(solver_id)

    database.requirements_consistency(network)

    opt_context = OptimizationContext(
        network, database, block, scenarios, border_management
    )

    return OptimizationProblem(problem_name, solver, opt_context, problem_strategy)
