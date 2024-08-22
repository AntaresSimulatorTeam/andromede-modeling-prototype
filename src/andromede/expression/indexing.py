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

from abc import ABC, abstractmethod
from dataclasses import dataclass

import andromede.expression.time_operator
from andromede.expression.indexing_structure import IndexingStructure

from .expression import (
    AdditionNode,
    ComparisonNode,
    ComponentParameterNode,
    ComponentVariableNode,
    DecisionTreeParameterNode,
    DecisionTreeVariableNode,
    DivisionNode,
    ExpressionNode,
    LiteralNode,
    MultiplicationNode,
    NegationNode,
    OptionalPortFieldNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    SubstractionNode,
    TimeAggregatorNode,
    TimeOperatorNode,
    VariableNode,
)
from .visitor import ExpressionVisitor, T, visit


class IndexingStructureProvider(ABC):
    @abstractmethod
    def get_parameter_structure(self, name: str) -> IndexingStructure:
        ...

    @abstractmethod
    def get_variable_structure(self, name: str) -> IndexingStructure:
        ...

    @abstractmethod
    def get_component_variable_structure(
        self, component_id: str, name: str
    ) -> IndexingStructure:
        ...

    @abstractmethod
    def get_component_parameter_structure(
        self, component_id: str, name: str
    ) -> IndexingStructure:
        ...


@dataclass(frozen=True)
class TimeScenarioIndexingVisitor(ExpressionVisitor[IndexingStructure]):
    """
    Determines if the expression represents a single expression or an expression that should be instantiated for all time steps.
    """

    context: IndexingStructureProvider

    def literal(self, node: LiteralNode) -> IndexingStructure:
        return IndexingStructure(False, False)

    def negation(self, node: NegationNode) -> IndexingStructure:
        return visit(node.operand, self)

    def addition(self, node: AdditionNode) -> IndexingStructure:
        return visit(node.left, self) | visit(node.right, self)

    def substraction(self, node: SubstractionNode) -> IndexingStructure:
        return visit(node.left, self) | visit(node.right, self)

    def multiplication(self, node: MultiplicationNode) -> IndexingStructure:
        return visit(node.left, self) | visit(node.right, self)

    def division(self, node: DivisionNode) -> IndexingStructure:
        return visit(node.left, self) | visit(node.right, self)

    def comparison(self, node: ComparisonNode) -> IndexingStructure:
        return visit(node.left, self) | visit(node.right, self)

    def variable(self, node: VariableNode) -> IndexingStructure:
        time = self.context.get_variable_structure(node.name).time == True
        scenario = self.context.get_variable_structure(node.name).scenario == True
        return IndexingStructure(time, scenario)

    def parameter(self, node: ParameterNode) -> IndexingStructure:
        time = self.context.get_parameter_structure(node.name).time == True
        scenario = self.context.get_parameter_structure(node.name).scenario == True
        return IndexingStructure(time, scenario)

    def comp_variable(self, node: ComponentVariableNode) -> IndexingStructure:
        return self.context.get_component_variable_structure(
            node.component_id, node.name
        )

    def comp_parameter(self, node: ComponentParameterNode) -> IndexingStructure:
        return self.context.get_component_parameter_structure(
            node.component_id, node.name
        )

    def dt_variable(self, node: DecisionTreeVariableNode) -> IndexingStructure:
        return visit(ComponentVariableNode(node.component_id, node.name), self)

    def dt_parameter(self, node: DecisionTreeParameterNode) -> IndexingStructure:
        return visit(ComponentParameterNode(node.component_id, node.name), self)

    def time_operator(self, node: TimeOperatorNode) -> IndexingStructure:
        time_operator_cls = getattr(andromede.expression.time_operator, node.name)
        if time_operator_cls.rolling():
            return visit(node.operand, self)
        else:
            return IndexingStructure(False, visit(node.operand, self).scenario)

    def time_aggregator(self, node: TimeAggregatorNode) -> IndexingStructure:
        if node.stay_roll:
            return visit(node.operand, self)
        else:
            return IndexingStructure(False, visit(node.operand, self).scenario)

    def scenario_operator(self, node: ScenarioOperatorNode) -> IndexingStructure:
        return IndexingStructure(visit(node.operand, self).time, False)

    def port_field(self, node: PortFieldNode) -> IndexingStructure:
        raise ValueError(
            "Port fields must be resolved before computing indexing structure."
        )

    def optional_port_field(self, node: OptionalPortFieldNode) -> IndexingStructure:
        raise ValueError(
            "Port fields must be resolved before computing indexing structure."
        )

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> IndexingStructure:
        raise ValueError(
            "Port fields aggregators must be resolved before computing indexing structure."
        )


def compute_indexation(
    expression: ExpressionNode, provider: IndexingStructureProvider
) -> IndexingStructure:
    return visit(expression, TimeScenarioIndexingVisitor(provider))
