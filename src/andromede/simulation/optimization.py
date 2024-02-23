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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, List, Optional, Type, Union

import ortools.linear_solver.pywraplp as lp

from andromede.expression import (
    EvaluationVisitor,
    ExpressionNode,
    ParameterValueProvider,
    ValueProvider,
    resolve_parameters,
    visit,
)
from andromede.expression.context_adder import add_component_context
from andromede.expression.indexing import IndexingStructureProvider, compute_indexation
from andromede.expression.indexing_structure import IndexingStructure
from andromede.expression.port_resolver import PortFieldKey, resolve_port
from andromede.expression.scenario_operator import Expectation
from andromede.expression.time_operator import TimeEvaluation, TimeShift, TimeSum
from andromede.model.common import ProblemContext, ValueType
from andromede.model.constraint import Constraint
from andromede.model.model import (
    BlockBoundariesDynamics,
    MergedProblemStrategy,
    ModelSelectionStrategy,
    PortFieldId,
)
from andromede.simulation.linear_expression import LinearExpression, Term
from andromede.simulation.linearize import linearize_expression
from andromede.simulation.time_block import TimeBlock, TimestepComponentVariableKey
from andromede.study.data import DataBase
from andromede.study.network import Component, Network
from andromede.utils import get_or_add


def _get_parameter_value(
    context: "OptimizationContext",
    block_timestep: int,
    scenario: int,
    component_id: str,
    name: str,
) -> float:
    data = context.database.get_data(component_id, name)
    absolute_timestep = context.block_timestep_to_absolute_timestep(block_timestep)
    return data.get_value(absolute_timestep, scenario)


# TODO: Maybe add the notion of constant parameter in the model
# TODO : And constant over scenarios ?
def _parameter_is_constant_over_time(
    component: Component,
    name: str,
    context: "OptimizationContext",
    block_timestep: int,
    scenario: int,
) -> bool:
    data = context.database.get_data(component.id, name)
    return data.get_value(block_timestep, scenario) == IndexingStructure(
        time=False, scenario=False
    )


class TimestepValueProvider(ABC):
    """
    Interface which provides numerical values for individual timesteps.
    """

    @abstractmethod
    def get_value(self, block_timestep: int, scenario: int) -> float:
        raise NotImplementedError()


def _make_value_provider(
    context: "OptimizationContext",
    block_timestep: int,
    scenario: int,
    component: Component,
) -> ValueProvider:
    """
    Create a value provider which takes its values from
    the parameter values as defined in the network data.

    Cannot evaluate expressions which contain variables.
    """

    class Provider(ValueProvider):
        def get_component_variable_value(self, component_id: str, name: str) -> float:
            raise NotImplementedError(
                "Cannot provide variable value at problem build time."
            )

        def get_component_parameter_value(self, component_id: str, name: str) -> float:
            return _get_parameter_value(
                context, block_timestep, scenario, component_id, name
            )

        def get_variable_value(self, name: str) -> float:
            raise NotImplementedError(
                "Cannot provide variable value at problem build time."
            )

        def get_parameter_value(self, name: str) -> float:
            raise ValueError(
                "Parameter must be associated to its component before resolution."
            )

        def parameter_is_constant_over_time(self, name: str) -> bool:
            return not component.model.parameters[name].structure.time

    return Provider()


@dataclass(frozen=True)
class ExpressionTimestepValueProvider(TimestepValueProvider):
    context: "OptimizationContext"
    component: Component
    expression: ExpressionNode

    # OptimizationContext has knowledge of the block, so that get_value only needs block_timestep and scenario to get the correct data value

    def get_value(self, block_timestep: int, scenario: int) -> float:
        param_value_provider = _make_value_provider(
            self.context, block_timestep, scenario, self.component
        )
        visitor = EvaluationVisitor(param_value_provider)
        return visit(self.expression, visitor)


def _make_parameter_value_provider(
    context: "OptimizationContext",
    block_timestep: int,
    scenario: int,
) -> ParameterValueProvider:
    """
    A value provider which takes its values from
    the parameter values as defined in the network data.

    Cannot evaluate expressions which contain variables.
    """

    class Provider(ParameterValueProvider):
        def get_component_parameter_value(self, component_id: str, name: str) -> float:
            return _get_parameter_value(
                context, block_timestep, scenario, component_id, name
            )

        def get_parameter_value(self, name: str) -> float:
            raise ValueError(
                "Parameters should have been associated with their component before resolution."
            )

    return Provider()


def _make_data_structure_provider(
    network: Network, component: Component
) -> IndexingStructureProvider:
    """
    Retrieve information in data structure (parameter and variable) from the model
    """

    class Provider(IndexingStructureProvider):
        def get_component_variable_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            return network.get_component(component_id).model.variables[name].structure

        def get_component_parameter_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            return network.get_component(component_id).model.parameters[name].structure

        def get_parameter_structure(self, name: str) -> IndexingStructure:
            return component.model.parameters[name].structure

        def get_variable_structure(self, name: str) -> IndexingStructure:
            return component.model.variables[name].structure

    return Provider()


@dataclass(frozen=True)
class ComponentContext:
    """
    Helper class to fill the optimization problem with component-related equations and variables.
    """

    opt_context: "OptimizationContext"
    component: Component

    def get_values(self, expression: ExpressionNode) -> TimestepValueProvider:
        """
        The returned value provider will evaluate the provided expression.
        """
        return ExpressionTimestepValueProvider(
            self.opt_context, self.component, expression
        )

    def add_variable(
        self,
        block_timestep: int,
        scenario: int,
        model_var_name: str,
        variable: lp.Variable,
    ) -> None:
        self.opt_context.register_component_variable(
            block_timestep, scenario, self.component.id, model_var_name, variable
        )

    def get_variable_or_init_cond(
        self,
        block_timestep: int,
        scenario: int,
        variable_name: str,
        variable_structure: IndexingStructure,
    ) -> Union[lp.Variable, float, None]:
        if not variable_structure.scenario:
            scenario = 0

        if self.component.model.inter_block_dyn == BlockBoundariesDynamics.CYCLE:
            if variable_structure.time:
                block_timestep = block_timestep % self.opt_context.block_length()
            else:
                block_timestep = 0
        elif (
            self.component.model.inter_block_dyn
            == BlockBoundariesDynamics.IGNORE_BOUNDARIES
        ):
            if block_timestep not in range(self.opt_context.block_length()):
                # The corresponding variable does not belong to the current block
                return None
            elif not variable_structure.time:
                block_timestep = 0

        elif (
            self.component.model.inter_block_dyn
            == BlockBoundariesDynamics.INTERBLOCK_DYNAMICS
        ):
            if block_timestep not in range(self.opt_context.block_length()):
                # The corresponding variable does not belong to the current block, we use the solution value from previous block
                if block_timestep > 0:
                    raise ValueError(
                        "Cannot retrieve solution value for timesteps in future blocks."
                    )

                if (
                    self.opt_context._orchestration_method
                    == OrchestrationMethod.SEQUENTIAL
                ):
                    if variable_structure.time:
                        if self.opt_context._previous_block is not None:
                            previous_block_step = (
                                len(self.opt_context._previous_block) + block_timestep
                            )
                        elif self.opt_context._block.id == 1:
                            # Ignore init condition for first block
                            return None
                        else:
                            raise ValueError(
                                f"Previous block must be specified to get variable solution value for {TimestepComponentVariableKey(self.component.id, variable_name, block_timestep, scenario)}."
                            )
                    else:
                        previous_block_step = 0

                    if self.opt_context._initial_variables is not None:
                        return self.opt_context._initial_variables[
                            TimestepComponentVariableKey(
                                self.component.id,
                                variable_name,
                                previous_block_step,
                                scenario,
                            )
                        ].solution_value()
                    else:
                        raise ValueError(
                            f"Cannot retrieve initial condition for variable {TimestepComponentVariableKey(self.component.id, variable_name, previous_block_step, scenario)}."
                        )
                elif (
                    self.opt_context._orchestration_method
                    == OrchestrationMethod.SLIDING_WINDOW
                ):
                    # TODO : Get correct relative block index of previous block given the slide length, note that sliding window with slide size = window size -> Sequential mode
                    raise NotImplementedError
                else:
                    raise NotImplementedError
            elif not variable_structure.time:
                block_timestep = 0
        else:
            raise NotImplementedError

        return self.opt_context.get_component_variable(
            block_timestep,
            scenario,
            self.component.id,
            variable_name,
        )

    def linearize_expression(
        self,
        block_timestep: int,
        scenario: int,
        expression: ExpressionNode,
    ) -> LinearExpression:
        parameters_valued_provider = _make_parameter_value_provider(
            self.opt_context, block_timestep, scenario
        )
        evaluated_expr = resolve_parameters(expression, parameters_valued_provider)

        value_provider = _make_value_provider(
            self.opt_context, block_timestep, scenario, self.component
        )
        structure_provider = _make_data_structure_provider(
            self.opt_context.network, self.component
        )

        return linearize_expression(evaluated_expr, structure_provider, value_provider)


class OrchestrationMethod(Enum):
    """
    Defines methods that can be used to process the optimization over several time blocks :
        - SEQUENTIAL : Each time block is processed sequentially, while taking into account the interblock dynamics for the components that require it
        - SLIDING_WINDOW : Defines a time window within which to perform the optimization, while retaining the results only on a subwindow. The optimization window is then moved of some timesteps and the process goes on until the horizon is reached.
    """

    SEQUENTIAL = "SEQUENTIAL"
    SLIDING_WINDOW = "SLIDING_WINDOW"


@dataclass
class SolverVariableInfo:
    """
    Helper class for constructing the structure file
    for Benders solver. It keeps track of the corresponding
    column of the variable in the MPS format as well as if it is
    present in the objective function or not
    """

    name: str
    column_id: int
    is_in_objective: bool


class OptimizationContext:
    """
    Helper class to build the optimization problem.
    Maintains some mappings between model and solver objects.
    Also provides navigation method in the model (components by node ...).
    """

    def __init__(
        self,
        network: Network,
        database: DataBase,
        block: TimeBlock,
        previous_block: Optional[TimeBlock],
        scenarios: int,
        orchestration_method: OrchestrationMethod,
        initial_variables: Optional[
            Dict[TimestepComponentVariableKey, lp.Variable]
        ] = None,
    ):
        self._network = network
        self._database = database
        self._block = block
        self._previous_block = previous_block
        self._scenarios = scenarios
        self._orchestration_method = orchestration_method
        self._initial_variables = initial_variables

        # TODO: The flow and components variables will be very similar between blocks, is there a way to construct them once ?
        self._component_variables: Dict[TimestepComponentVariableKey, lp.Variable] = {}
        self._solver_variables: Dict[lp.Variable, SolverVariableInfo] = {}
        self._connection_fields_expressions: Dict[
            PortFieldKey, List[ExpressionNode]
        ] = {}

    @property
    def network(self) -> Network:
        return self._network

    @property
    def scenarios(self) -> int:
        return self._scenarios

    def block_length(self) -> int:
        return len(self._block)

    @property
    def connection_fields_expressions(self) -> Dict[PortFieldKey, List[ExpressionNode]]:
        return self._connection_fields_expressions

    # TODO: Need to think about data processing when creating blocks with varying or inequal time steps length (aggregation, sum ?, mean of data ?)
    def block_timestep_to_absolute_timestep(self, block_timestep: int) -> int:
        return self._block.timesteps[block_timestep]

    @property
    def database(self) -> DataBase:
        return self._database

    def get_time_indices(self, index_structure: IndexingStructure) -> Iterable[int]:
        return range(self.block_length()) if index_structure.time else range(1)

    def get_scenario_indices(self, index_structure: IndexingStructure) -> Iterable[int]:
        return range(self.scenarios) if index_structure.scenario else range(1)

    # TODO: API to improve, variable_structure guides which of the indices block_timestep and scenario should be used
    def get_component_variable(
        self,
        block_timestep: int,
        scenario: int,
        component_id: str,
        variable_name: str,
    ) -> lp.Variable:
        """
        Retrieves the solver variable for a component at given timestep and scenario. It returns None if the timesteps and border management strategy make the requested variable belong to another optimization block.
        """

        return self._component_variables[
            TimestepComponentVariableKey(
                component_id, variable_name, block_timestep, scenario
            )
        ]

    def get_all_component_variables(
        self,
    ) -> Dict[TimestepComponentVariableKey, lp.Variable]:
        return self._component_variables

    def register_component_variable(
        self,
        block_timestep: int,
        scenario: int,
        component_id: str,
        variable_name: str,
        variable: lp.Variable,
    ) -> None:
        key = TimestepComponentVariableKey(
            component_id, variable_name, block_timestep, scenario
        )
        if key not in self._component_variables:
            self._solver_variables[variable] = SolverVariableInfo(
                variable.name(), len(self._solver_variables), False
            )
        self._component_variables[key] = variable

    def get_component_context(self, component: Component) -> ComponentContext:
        return ComponentContext(self, component)

    def register_connection_fields_expressions(
        self,
        component_id: str,
        port_name: str,
        field_name: str,
        expression: ExpressionNode,
    ) -> None:
        key = PortFieldKey(component_id, PortFieldId(port_name, field_name))
        get_or_add(self._connection_fields_expressions, key, lambda: []).append(
            expression
        )


def _get_indexing(
    constraint: Constraint, provider: IndexingStructureProvider
) -> IndexingStructure:
    return (
        compute_indexation(constraint.expression, provider)
        or compute_indexation(constraint.lower_bound, provider)
        or compute_indexation(constraint.upper_bound, provider)
    )


def _compute_indexing_structure(
    context: ComponentContext, constraint: Constraint
) -> IndexingStructure:
    data_structure_provider = _make_data_structure_provider(
        context.opt_context.network, context.component
    )
    constraint_indexing = _get_indexing(constraint, data_structure_provider)
    return constraint_indexing


def _instantiate_model_expression(
    model_expression: ExpressionNode,
    component_id: str,
    optimization_context: OptimizationContext,
) -> ExpressionNode:
    """
    Performs common operations that are necessary on model expressions before their actual use:
     1. add component ID for variables and parameters of THIS component
     2. replace port fields by their definition
    """
    with_component = add_component_context(component_id, model_expression)
    with_component_and_ports = resolve_port(
        with_component, component_id, optimization_context.connection_fields_expressions
    )
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

    # Perf: Perform linearization (tree traversing) without timesteps so that we can get the number of instances for the expression (from the time_ids of operators)
    linear_expr = context.linearize_expression(0, 0, constraint.expression)
    # Will there be cases where instances > 1 ? If not, maybe just a check that get_number_of_instances == 1 is sufficient ? Anyway, the function should be implemented
    instances_per_time_step = linear_expr.number_of_instances()

    for block_timestep in context.opt_context.get_time_indices(constraint_indexing):
        for scenario in context.opt_context.get_scenario_indices(constraint_indexing):
            linear_expr_at_t = context.linearize_expression(
                block_timestep, scenario, constraint.expression
            )
            # What happens if there is some time_operator in the bounds ?
            constraint_data = ConstraintData(
                name=constraint.name,
                lower_bound=context.get_values(constraint.lower_bound).get_value(
                    block_timestep, scenario
                ),
                upper_bound=context.get_values(constraint.upper_bound).get_value(
                    block_timestep, scenario
                ),
                expression=linear_expr_at_t,
            )
            make_constraint(
                solver,
                context.opt_context,
                block_timestep,
                scenario,
                constraint_data,
                instances_per_time_step,
            )


def _create_objective(
    solver: lp.Solver,
    opt_context: OptimizationContext,
    component: Component,
    component_context: ComponentContext,
    objective_contribution: ExpressionNode,
) -> None:
    instantiated_expr = _instantiate_model_expression(
        objective_contribution, component.id, opt_context
    )
    # We have already checked in the model creation that the objective contribution is neither indexed by time nor by scenario
    linear_expr = component_context.linearize_expression(0, 0, instantiated_expr)

    obj: lp.Objective = solver.Objective()
    out_of_block_offset: float = 0
    for term in linear_expr.terms.values():
        # TODO : How to handle the scenario operator in a general manner ?
        if isinstance(term.scenario_operator, Expectation):
            weight = 1 / opt_context.scenarios
            scenario_ids = range(opt_context.scenarios)
        else:
            weight = 1
            scenario_ids = range(1)

        for scenario in scenario_ids:
            # TODO: here we may only be interested in solver vars and no on initial conditions ?
            var_and_init_cond = _get_solver_vars_and_init_cond(
                term,
                opt_context,
                0,
                scenario,
                0,
            )

            for solver_var in var_and_init_cond.solver_vars:
                opt_context._solver_variables[solver_var].is_in_objective = True
                obj.SetCoefficient(
                    solver_var,
                    obj.GetCoefficient(solver_var) + weight * term.coefficient,
                )
            # TODO: Maybe useless ?
            for init_cond in var_and_init_cond.initial_conditions_from_previous_block:
                out_of_block_offset += init_cond

    # This should have no effect on the optimization
    obj.SetOffset(linear_expr.constant + out_of_block_offset + obj.offset())


@dataclass
class ConstraintData:
    name: str
    lower_bound: float
    upper_bound: float
    expression: LinearExpression


@dataclass
class ConstraintVarAndInitialCondition:
    solver_vars: List[lp.Variable]
    initial_conditions_from_previous_block: List[float]


def _get_solver_vars_and_init_cond(
    term: Term,
    context: OptimizationContext,
    block_timestep: int,
    scenario: int,
    instance: int,
) -> ConstraintVarAndInitialCondition:
    solver_vars: List[lp.Variable] = []
    init_cond: List[float] = []
    constraint_var_and_init_cond = ConstraintVarAndInitialCondition(
        solver_vars, init_cond
    )
    component_context = context.get_component_context(
        context.network.get_component(term.component_id)
    )
    if isinstance(term.time_aggregator, TimeSum):
        if isinstance(term.time_operator, TimeShift):
            for time_id in term.time_operator.time_ids:
                fill_constraint_var_and_init_cond(
                    term,
                    block_timestep + time_id,
                    scenario,
                    component_context,
                    constraint_var_and_init_cond,
                )
        elif isinstance(term.time_operator, TimeEvaluation):
            for time_id in term.time_operator.time_ids:
                fill_constraint_var_and_init_cond(
                    term,
                    time_id,
                    scenario,
                    component_context,
                    constraint_var_and_init_cond,
                )
        else:  # time_operator is None, retrieve variable for each time step of the block. What happens if we do x.sum() with x not being indexed by time ? Is there a check that it is a valid expression ?
            for time_id in range(context.block_length()):
                fill_constraint_var_and_init_cond(
                    term,
                    block_timestep + time_id,
                    scenario,
                    component_context,
                    constraint_var_and_init_cond,
                )

    else:  # time_aggregator is None
        if isinstance(term.time_operator, TimeShift):
            fill_constraint_var_and_init_cond(
                term,
                block_timestep + term.time_operator.time_ids[instance],
                scenario,
                component_context,
                constraint_var_and_init_cond,
            )
        elif isinstance(term.time_operator, TimeEvaluation):
            fill_constraint_var_and_init_cond(
                term,
                term.time_operator.time_ids[instance],
                scenario,
                component_context,
                constraint_var_and_init_cond,
            )
        else:  # time_operator is None
            fill_constraint_var_and_init_cond(
                term,
                block_timestep,
                scenario,
                component_context,
                constraint_var_and_init_cond,
            )
    return constraint_var_and_init_cond


def fill_constraint_var_and_init_cond(
    term: Term,
    block_timestep: int,
    scenario: int,
    component_context: ComponentContext,
    constraint_var_and_init_cond: ConstraintVarAndInitialCondition,
) -> None:
    output = component_context.get_variable_or_init_cond(
        block_timestep,
        scenario,
        term.variable_name,
        term.structure,
    )
    if isinstance(output, lp.Variable):
        constraint_var_and_init_cond.solver_vars.append(output)
    elif isinstance(output, float):
        constraint_var_and_init_cond.initial_conditions_from_previous_block.append(
            output
        )


def make_constraint(
    solver: lp.Solver,
    context: OptimizationContext,
    block_timestep: int,
    scenario: int,
    data: ConstraintData,
    instances: int,
) -> Dict[str, lp.Constraint]:
    """
    Adds constraint to the solver.
    """
    solver_constraints = {}
    constraint_name = data.name
    for instance in range(instances):
        if instances > 1:
            constraint_name += f"_{instance}"

        solver_constraint: lp.Constraint = solver.Constraint(constraint_name)
        constant: float = 0
        rhs_offset: float = 0
        for term in data.expression.terms.values():
            var_and_init_cond = _get_solver_vars_and_init_cond(
                term,
                context,
                block_timestep,
                scenario,
                instance,
            )
            for solver_var in var_and_init_cond.solver_vars:
                coefficient = term.coefficient + solver_constraint.GetCoefficient(
                    solver_var
                )
                solver_constraint.SetCoefficient(solver_var, coefficient)
            for init_cond in var_and_init_cond.initial_conditions_from_previous_block:
                rhs_offset += init_cond
        constant += data.expression.constant

        solver_constraint.SetBounds(
            data.lower_bound - constant - rhs_offset,
            data.upper_bound - constant - rhs_offset,
        )

        # TODO: this dictionary does not make sense, we override the content when there are multiple instances
        solver_constraints[constraint_name] = solver_constraint
    return solver_constraints


class OptimizationProblem:
    name: str
    solver: lp.Solver
    context: OptimizationContext
    strategy: Type[ModelSelectionStrategy]

    def __init__(
        self,
        name: str,
        solver: lp.Solver,
        opt_context: OptimizationContext,
        build_strategy: Type[ModelSelectionStrategy] = MergedProblemStrategy,
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
                instantiated_expression = add_component_context(
                    master_port.component.id, expression_node
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

            for model_var in self.strategy.get_variables(model):
                var_indexing = IndexingStructure(
                    model_var.structure.time, model_var.structure.scenario
                )
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
                for block_timestep in self.context.get_time_indices(var_indexing):
                    for scenario in self.context.get_scenario_indices(var_indexing):
                        lower_bound = -self.solver.infinity()
                        upper_bound = self.solver.infinity()
                        if instantiated_lb_expr:
                            lower_bound = component_context.get_values(
                                instantiated_lb_expr
                            ).get_value(block_timestep, scenario)
                        if instantiated_ub_expr:
                            upper_bound = component_context.get_values(
                                instantiated_ub_expr
                            ).get_value(block_timestep, scenario)

                        # Externally, for the Solver, this variable will have a full name
                        # Internally, it will be indexed by a structure that into account
                        # the component id, variable name, timestep and scenario separately
                        if model_var.data_type == ValueType.FLOAT:
                            solver_var = self.solver.NumVar(
                                lower_bound,
                                upper_bound,
                                f"{component.id}_{model_var.name}_{block_timestep}_{scenario}",
                            )
                        else:
                            solver_var = self.solver.IntVar(
                                lower_bound,
                                upper_bound,
                                f"{component.id}_{model_var.name}_{block_timestep}_{scenario}",
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
                        component_context,
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
    orchestration_method: OrchestrationMethod = OrchestrationMethod.SEQUENTIAL,
    previous_block: Optional[TimeBlock] = None,
    initial_variables: Optional[Dict[TimestepComponentVariableKey, lp.Variable]] = None,
    solver_id: str = "GLOP",
    problem_strategy: Type[ModelSelectionStrategy] = MergedProblemStrategy,
) -> OptimizationProblem:
    """
    Entry point to build the optimization problem for a time period.
    """
    solver: lp.Solver = lp.Solver.CreateSolver(solver_id)

    database.requirements_consistency(network)

    opt_context = OptimizationContext(
        network,
        database,
        block,
        previous_block,
        scenarios,
        orchestration_method,
        initial_variables,
    )

    return OptimizationProblem(problem_name, solver, opt_context, problem_strategy)
