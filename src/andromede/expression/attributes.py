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

from dataclasses import dataclass
from typing import List

from andromede.expression.copy import CopyVisitor
from andromede.expression.expression import (
    AdditionNode,
    ComparisonNode,
    ComponentParameterNode,
    ComponentVariableNode,
    DivisionNode,
    ExpressionNode,
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
    VariableNode,
)
from andromede.expression.visitor import ExpressionVisitor, visit


@dataclass
class VariableGetterVisitor(ExpressionVisitor[List[str]]):
    def literal(self, node: LiteralNode) -> List[str]:
        return []

    def variable(self, node: VariableNode) -> List[str]:
        return [node.name]

    def parameter(self, node: ParameterNode) -> List[str]:
        return []

    def negation(self, node: NegationNode) -> List[str]:
        return visit(node.operand, self)

    def addition(self, node: AdditionNode) -> List[str]:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return left_value + right_value

    def substraction(self, node: SubstractionNode) -> List[str]:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return left_value + right_value

    def multiplication(self, node: MultiplicationNode) -> List[str]:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return left_value + right_value

    def division(self, node: DivisionNode) -> List[str]:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return left_value + right_value

    def comparison(self, node: ComparisonNode) -> List[str]:
        raise ValueError("Visitor must not be used on comparison node")

    def comp_variable(self, node: ComponentVariableNode) -> List[str]:
        raise ValueError("Visitor must not be used on instantiated variable node")

    def comp_parameter(self, node: ComponentParameterNode) -> List[str]:
        raise ValueError("Visitor must not be used on instantiated parameter node")

    def time_operator(self, node: TimeOperatorNode) -> List[str]:
        raise ValueError("Visitor must not be used on time operator node")

    def time_aggregator(self, node: TimeAggregatorNode) -> List[str]:
        raise ValueError("Visitor must not be used on time aggregator node")

    def scenario_operator(self, node: ScenarioOperatorNode) -> List[str]:
        raise ValueError("Visitor must not be used on scenario operator node")

    def port_field(self, node: PortFieldNode) -> List[str]:
        raise ValueError("Visitor must not be used on port field node")

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> List[str]:
        raise ValueError("Visitor must not be used on prot field aggregator node")


@dataclass(frozen=True)
class VariableNamePrependerVisitor(CopyVisitor):
    prefix: str

    def variable(self, node: VariableNode) -> ExpressionNode:
        return VariableNode(f"{self.prefix}_{node.name}")
