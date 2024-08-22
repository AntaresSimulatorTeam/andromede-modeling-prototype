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
from andromede.expression.expression import (
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

from .visitor import ExpressionVisitor, visit


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

    def variable(self, node: VariableNode) -> int:
        return 1

    def parameter(self, node: ParameterNode) -> int:
        return 0

    def comp_variable(self, node: ComponentVariableNode) -> int:
        return 1

    def comp_parameter(self, node: ComponentParameterNode) -> int:
        return 0

    def dt_variable(self, node: DecisionTreeVariableNode) -> int:
        return 1

    def dt_parameter(self, node: DecisionTreeParameterNode) -> int:
        return 0

    def time_operator(self, node: TimeOperatorNode) -> int:
        if node.name in ["TimeShift", "TimeEvaluation"]:
            return visit(node.operand, self)
        else:
            return NotImplemented

    def time_aggregator(self, node: TimeAggregatorNode) -> int:
        if node.name in ["TimeSum"]:
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

    def optional_port_field(self, node: OptionalPortFieldNode) -> int:
        # TODO Can be zero if port_field not present but must wait
        # for port resolution to know. Since the worst case is 1,
        # we'll keep it as it is for now
        return 1

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> int:
        return visit(node.operand, self)


def compute_degree(expression: ExpressionNode) -> int:
    return visit(expression, ExpressionDegreeVisitor())


def is_constant(expr: ExpressionNode) -> bool:
    """
    True if the expression has no variable.
    """
    return compute_degree(expr) == 0


def is_linear(expr: ExpressionNode) -> bool:
    """
    True if the expression is linear with respect to variables.
    """
    return compute_degree(expr) <= 1
