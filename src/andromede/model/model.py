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
The model module defines the data model for user-defined models.
A model allows to define the behaviour for components, by
defining parameters, variables, and equations.
"""
import itertools
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

# from andromede.expression.expression import (
#     BinaryOperatorNode,
#     ComponentParameterNode,
#     ComponentVariableNode,
#     PortFieldAggregatorNode,
#     PortFieldNode,
#     ScenarioOperatorNode,
#     TimeAggregatorNode,
#     TimeOperatorNode,
# )
from andromede.expression.expression_efficient import (
    AdditionNode,
    BinaryOperatorNode,
    ComparisonNode,
    ComponentParameterNode,
    DivisionNode,
    LiteralNode,
    MultiplicationNode,
    NegationNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    SubstractionNode,
    TimeAggregatorNode,
    TimeOperatorNode,
)
from andromede.expression.indexing import IndexingStructureProvider, compute_indexation
from andromede.expression.indexing_structure import IndexingStructure
from andromede.expression.linear_expression_efficient import (
    LinearExpressionEfficient,
    is_linear,
    wrap_in_linear_expr,
    wrap_in_linear_expr_if_present,
)
from andromede.expression.visitor import ExpressionVisitor, visit
from andromede.model.common import ValueOrExprNodeOrLinearExpr
from andromede.model.constraint import Constraint
from andromede.model.parameter import Parameter
from andromede.model.port import PortType
from andromede.model.variable import Variable

# from andromede.expression import (
#     AdditionNode,
#     ComparisonNode,
#     DivisionNode,
#     ExpressionNode,
#     ExpressionVisitor,
#     LiteralNode,
#     MultiplicationNode,
#     NegationNode,
#     ParameterNode,
#     SubstractionNode,
#     VariableNode,
# )
# from andromede.expression.expression_efficient import (
#     AdditionNode,
#     BinaryOperatorNode,
#     ComparisonNode,
#     ComponentParameterNode,
#     DivisionNode,
#     ExpressionNodeEfficient,
#     LiteralNode,
#     MultiplicationNode,
#     NegationNode,
#     ParameterNode,
#     PortFieldAggregatorNode,
#     PortFieldNode,
#     ScenarioOperatorNode,
#     SubstractionNode,
#     TimeAggregatorNode,
#     TimeOperatorNode,
# )


# TODO: Introduce bool_variable ?
def _make_structure_provider(model: "Model") -> IndexingStructureProvider:
    class Provider(IndexingStructureProvider):
        def get_parameter_structure(self, name: str) -> IndexingStructure:
            return model.parameters[name].structure

        def get_variable_structure(self, name: str) -> IndexingStructure:
            return model.variables[name].structure

        def get_component_parameter_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            raise NotImplementedError(
                "Cannot have parameters associated to components in models."
            )

        def get_component_variable_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            raise NotImplementedError(
                "Cannot have variables associated to components in models."
            )

    return Provider()


def _is_objective_contribution_valid(
    model: "Model", objective_contribution: LinearExpressionEfficient
) -> bool:
    if not is_linear(objective_contribution):
        raise ValueError("Objective contribution must be a linear expression.")

    data_structure_provider = _make_structure_provider(model)
    objective_structure = objective_contribution.compute_indexation(
        data_structure_provider
    )

    if objective_structure != IndexingStructure(time=False, scenario=False):
        raise ValueError("Objective contribution should be a real-valued expression.")
    # TODO: We should also check that the number of instances is equal to 1, but this would require a linearization here, do not want to do that for now...
    return True


@dataclass(frozen=True)
class ModelPort:
    """
    Instance of a port as a model member.

    A model may carry multiple ports of the same type.
    For example, the 2 ports at line extremities.
    """

    port_type: PortType
    port_name: str


@dataclass(frozen=True)
class PortFieldId:
    port_name: str
    field_name: str


@dataclass(frozen=True)
class PortFieldDefinition:
    """
    Defines the values of one port field
    """

    port_field: PortFieldId
    definition: LinearExpressionEfficient

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition", wrap_in_linear_expr(self.definition))
        _validate_port_field_expression(self)


def port_field_def(
    port_name: str, field_name: str, definition: LinearExpressionEfficient
) -> PortFieldDefinition:
    return PortFieldDefinition(PortFieldId(port_name, field_name), definition)


@dataclass(frozen=True)
class Model:
    """
    Defines a model that can be referenced by actual components.
    A model defines the behaviour of those components.
    """

    id: str
    constraints: Dict[str, Constraint] = field(default_factory=dict)
    binding_constraints: Dict[str, Constraint] = field(default_factory=dict)
    inter_block_dyn: bool = False
    parameters: Dict[str, Parameter] = field(default_factory=dict)
    variables: Dict[str, Variable] = field(default_factory=dict)
    objective_operational_contribution: Optional[LinearExpressionEfficient] = None
    objective_investment_contribution: Optional[LinearExpressionEfficient] = None
    ports: Dict[str, ModelPort] = field(default_factory=dict)  # key = port name
    port_fields_definitions: Dict[PortFieldId, PortFieldDefinition] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.objective_operational_contribution:
            _is_objective_contribution_valid(
                self, self.objective_operational_contribution
            )

        if self.objective_investment_contribution:
            _is_objective_contribution_valid(
                self, self.objective_investment_contribution
            )

        for definition in self.port_fields_definitions.values():
            port_name = definition.port_field.port_name
            port_field = definition.port_field.field_name
            port = self.ports.get(port_name, None)
            if port is None:
                raise ValueError(f"Invalid port in port field definition: {port_name}")
            if port_field not in [f.name for f in port.port_type.fields]:
                raise ValueError(
                    f"Invalid port field in port field definition: {port_field}"
                )

    def get_all_constraints(self) -> Iterable[Constraint]:
        """
        Get binding constraints and inner constraints altogether.
        """
        return itertools.chain(
            self.binding_constraints.values(), self.constraints.values()
        )


def model(
    id: str,
    constraints: Optional[Iterable[Constraint]] = None,
    binding_constraints: Optional[Iterable[Constraint]] = None,
    parameters: Optional[Iterable[Parameter]] = None,
    variables: Optional[Iterable[Variable]] = None,
    objective_operational_contribution: Optional[ValueOrExprNodeOrLinearExpr] = None,
    objective_investment_contribution: Optional[ValueOrExprNodeOrLinearExpr] = None,
    inter_block_dyn: bool = False,
    ports: Optional[Iterable[ModelPort]] = None,
    port_fields_definitions: Optional[Iterable[PortFieldDefinition]] = None,
) -> Model:
    """
    Utility method to create Models from relaxed arguments
    """
    existing_port_names = {}
    if ports:
        for port in ports:
            port_name = port.port_name
            if port_name not in existing_port_names:
                existing_port_names[port_name] = port
            else:
                raise ValueError(
                    f"2 ports have the same name inside the model, it's not authorized : {port_name}"
                )
    return Model(
        id=id,
        constraints={c.name: c for c in constraints} if constraints else {},
        binding_constraints=(
            {c.name: c for c in binding_constraints} if binding_constraints else {}
        ),
        parameters={p.name: p for p in parameters} if parameters else {},
        variables={v.name: v for v in variables} if variables else {},
        objective_operational_contribution=wrap_in_linear_expr_if_present(
            objective_operational_contribution
        ),
        objective_investment_contribution=wrap_in_linear_expr_if_present(
            objective_investment_contribution
        ),
        inter_block_dyn=inter_block_dyn,
        ports=existing_port_names,
        port_fields_definitions=(
            {d.port_field: d for d in port_fields_definitions}
            if port_fields_definitions
            else {}
        ),
    )


class _PortFieldExpressionChecker(ExpressionVisitor[None]):
    """
    Visits the whole expression to check there is no:
    comparison, other port field, component-associated parametrs or variables...
    """

    def literal(self, node: LiteralNode) -> None:
        pass

    def negation(self, node: NegationNode) -> None:
        visit(node.operand, self)

    def _visit_binary_op(self, node: BinaryOperatorNode) -> None:
        visit(node.left, self)
        visit(node.right, self)

    def addition(self, node: AdditionNode) -> None:
        self._visit_binary_op(node)

    def substraction(self, node: SubstractionNode) -> None:
        self._visit_binary_op(node)

    def multiplication(self, node: MultiplicationNode) -> None:
        self._visit_binary_op(node)

    def division(self, node: DivisionNode) -> None:
        self._visit_binary_op(node)

    def comparison(self, node: ComparisonNode) -> None:
        raise ValueError("Port definition cannot contain a comparison operator.")

    # def variable(self, node: VariableNode) -> None:
    #     pass

    def parameter(self, node: ParameterNode) -> None:
        pass

    def comp_parameter(self, node: ComponentParameterNode) -> None:
        raise ValueError(
            "Port definition must not contain a parameter associated to a component."
        )

    # def comp_variable(self, node: ComponentVariableNode) -> None:
    #     raise ValueError(
    #         "Port definition must not contain a variable associated to a component."
    #     )

    def time_operator(self, node: TimeOperatorNode) -> None:
        visit(node.operand, self)

    def time_aggregator(self, node: TimeAggregatorNode) -> None:
        visit(node.operand, self)

    def scenario_operator(self, node: ScenarioOperatorNode) -> None:
        visit(node.operand, self)

    def port_field(self, node: PortFieldNode) -> None:
        raise ValueError("Port definition cannot reference another port field.")

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> None:
        raise ValueError("Port definition cannot contain port field aggregation.")


def _validate_port_field_expression(definition: PortFieldDefinition) -> None:
    if not isinstance(definition.definition, LinearExpressionEfficient):
        raise TypeError(
            f"Port field definition should be a LinearExpression, not a {type(definition.definition)}"
        )

    for term in definition.definition.terms.values():
        visit(term.coefficient, _PortFieldExpressionChecker())
    visit(definition.definition.constant, _PortFieldExpressionChecker())
