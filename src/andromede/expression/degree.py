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

import andromede.expression.scenario_operator

from .expression_efficient import (
    AdditionNode,
    ComparisonNode,
    ComponentParameterNode,
    DivisionNode,
    ExpressionNodeEfficient,
    LiteralNode,
    MultiplicationNode,
    NegationNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    SubstractionNode,
    TimeAggregatorName,
    TimeAggregatorNode,
    TimeOperatorName,
    TimeOperatorNode,
)
from .visitor import ExpressionVisitor, T, visit


class ExpressionDegreeVisitor(ExpressionVisitor[int]):
    """
    Computes degree of expression with respect to variables.
    """

    def literal(self, node: LiteralNode) -> int:
        return 0

    def negation(self, node: NegationNode) -> int:
        return visit(node.operand, self)

    # TODO: Take into account simplification that can occur with literal coefficient for add, sub, mult, div
    def addition(self, node: AdditionNode) -> int:
        return max(visit(node.left, self), visit(node.right, self))

    def substraction(self, node: SubstractionNode) -> int:
        return max(visit(node.left, self), visit(node.right, self))

    def multiplication(self, node: MultiplicationNode) -> int:
        return visit(node.left, self) + visit(node.right, self)

    def division(self, node: DivisionNode) -> int:
        right_degree = visit(node.right, self)
        if right_degree != 0:
            raise ValueError("Degree computation not implemented for divisions.")
        return visit(node.left, self)

    def comparison(self, node: ComparisonNode) -> int:
        return max(visit(node.left, self), visit(node.right, self))

    # def variable(self, node: VariableNode) -> int:
    #     return 1

    def parameter(self, node: ParameterNode) -> int:
        return 0

    # def comp_variable(self, node: ComponentVariableNode) -> int:
    #     return 1

    def comp_parameter(self, node: ComponentParameterNode) -> int:
        return 0

    def time_operator(self, node: TimeOperatorNode) -> int:
        if node.name in [TimeOperatorName.SHIFT, TimeOperatorName.EVALUATION]:
            return visit(node.operand, self)
        else:
            return NotImplemented

    def time_aggregator(self, node: TimeAggregatorNode) -> int:
        if node.name in [TimeAggregatorName.TIME_SUM]:
            return visit(node.operand, self)
        else:
            return NotImplemented

    def scenario_operator(self, node: ScenarioOperatorNode) -> int:
        scenario_operator_cls = getattr(
            andromede.expression.scenario_operator, node.name
        )
        # TODO: Carefully check if this formula is correct
        return scenario_operator_cls.degree() * visit(node.operand, self)

    def port_field(self, node: PortFieldNode) -> int:
        return 1

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> int:
        return visit(node.operand, self)


def compute_degree(expression: ExpressionNodeEfficient) -> int:
    return visit(expression, ExpressionDegreeVisitor())


def is_constant(expr: ExpressionNodeEfficient) -> bool:
    """
    True if the expression has no variable.
    """
    return compute_degree(expr) == 0


def is_linear(expr: ExpressionNodeEfficient) -> bool:
    """
    True if the expression is linear with respect to variables.
    """
    return compute_degree(expr) <= 1
