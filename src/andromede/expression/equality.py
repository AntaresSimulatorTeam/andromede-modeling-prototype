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

import math
from dataclasses import dataclass
from typing import Optional

from andromede.expression.expression_efficient import (
    AdditionNode,
    BinaryOperatorNode,
    ComparisonNode,
    ComponentParameterNode,
    DivisionNode,
    ExpressionNodeEfficient,
    ExpressionRange,
    InstancesTimeIndex,
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

# from andromede.expression import (
#     AdditionNode,
#     ComparisonNode,
#     DivisionNode,
#     ExpressionNode,
#     LiteralNode,
#     MultiplicationNode,
#     NegationNode,
#     ParameterNode,
#     SubstractionNode,
#     VariableNode,
# )
# from andromede.expression.expression import (
#     BinaryOperatorNode,
#     ExpressionRange,
#     InstancesTimeIndex,
#     PortFieldAggregatorNode,
#     PortFieldNode,
#     ScenarioOperatorNode,
#     TimeAggregatorNode,
#     TimeOperatorNode,
# )


@dataclass(frozen=True)
class EqualityVisitor:
    abs_tol: float = 0
    rel_tol: float = 0

    def __post_init__(self) -> None:
        if self.abs_tol < 0:
            raise ValueError(
                f"Absolute comparison tolerance must be >= 0, got {self.abs_tol}"
            )
        if self.rel_tol < 0:
            raise ValueError(
                f"Relative comparison tolerance must be >= 0, got {self.rel_tol}"
            )

    def visit(
        self, left: ExpressionNodeEfficient, right: ExpressionNodeEfficient
    ) -> bool:
        if left.__class__ != right.__class__:
            return False
        if isinstance(left, LiteralNode) and isinstance(right, LiteralNode):
            return self.literal(left, right)
        if isinstance(left, NegationNode) and isinstance(right, NegationNode):
            return self.negation(left, right)
        if isinstance(left, AdditionNode) and isinstance(right, AdditionNode):
            return self.addition(left, right)
        if isinstance(left, SubstractionNode) and isinstance(right, SubstractionNode):
            return self.substraction(left, right)
        if isinstance(left, DivisionNode) and isinstance(right, DivisionNode):
            return self.division(left, right)
        if isinstance(left, MultiplicationNode) and isinstance(
            right, MultiplicationNode
        ):
            return self.multiplication(left, right)
        if isinstance(left, ComparisonNode) and isinstance(right, ComparisonNode):
            return self.comparison(left, right)
        # if isinstance(left, VariableNode) and isinstance(right, VariableNode):
        #     return self.variable(left, right)
        if isinstance(left, ParameterNode) and isinstance(right, ParameterNode):
            return self.parameter(left, right)
        if isinstance(left, ComponentParameterNode) and isinstance(right, ComponentParameterNode):
            return self.comp_parameter(left, right)
        if isinstance(left, TimeOperatorNode) and isinstance(right, TimeOperatorNode):
            return self.time_operator(left, right)
        if isinstance(left, TimeAggregatorNode) and isinstance(
            right, TimeAggregatorNode
        ):
            return self.time_aggregator(left, right)
        if isinstance(left, ScenarioOperatorNode) and isinstance(
            right, ScenarioOperatorNode
        ):
            return self.scenario_operator(left, right)
        if isinstance(left, PortFieldNode) and isinstance(right, PortFieldNode):
            return self.port_field(left, right)
        if isinstance(left, PortFieldAggregatorNode) and isinstance(
            right, PortFieldAggregatorNode
        ):
            return self.port_field_aggregator(left, right)
        raise NotImplementedError(f"Equality not implemented for {left.__class__}")

    def literal(self, left: LiteralNode, right: LiteralNode) -> bool:
        return math.isclose(
            left.value, right.value, abs_tol=self.abs_tol, rel_tol=self.rel_tol
        )

    def _visit_operands(
        self, left: BinaryOperatorNode, right: BinaryOperatorNode
    ) -> bool:
        return self.visit(left.left, right.left) and self.visit(left.right, right.right)

    def negation(self, left: NegationNode, right: NegationNode) -> bool:
        return self.visit(left.operand, right.operand)

    def addition(self, left: AdditionNode, right: AdditionNode) -> bool:
        return self._visit_operands(left, right)

    def substraction(self, left: SubstractionNode, right: SubstractionNode) -> bool:
        return self._visit_operands(left, right)

    def multiplication(
        self, left: MultiplicationNode, right: MultiplicationNode
    ) -> bool:
        return self._visit_operands(left, right)

    def division(self, left: DivisionNode, right: DivisionNode) -> bool:
        return self._visit_operands(left, right)

    def comparison(self, left: ComparisonNode, right: ComparisonNode) -> bool:
        return left.comparator == right.comparator and self._visit_operands(left, right)

    # def variable(self, left: VariableNode, right: VariableNode) -> bool:
    #     return left.name == right.name

    def parameter(self, left: ParameterNode, right: ParameterNode) -> bool:
        return left.name == right.name
    
    def comp_parameter(self, left: ComponentParameterNode, right: ComponentParameterNode) -> bool:
        return left.component_id == right.component_id and left.name == right.name

    def expression_range(self, left: ExpressionRange, right: ExpressionRange) -> bool:
        if not self.visit(left.start, right.start):
            return False
        if not self.visit(left.stop, right.stop):
            return False
        if left.step is not None and right.step is not None:
            return self.visit(left.step, right.step)
        return left.step is None and right.step is None

    def instances_index(self, lhs: InstancesTimeIndex, rhs: InstancesTimeIndex) -> bool:
        if isinstance(lhs.expressions, ExpressionRange) and isinstance(
            rhs.expressions, ExpressionRange
        ):
            return self.expression_range(lhs.expressions, rhs.expressions)
        if isinstance(lhs.expressions, list) and isinstance(rhs.expressions, list):
            return len(lhs.expressions) == len(rhs.expressions) and all(
                self.visit(l, r) for l, r in zip(lhs.expressions, rhs.expressions)
            )
        return False

    def time_operator(self, left: TimeOperatorNode, right: TimeOperatorNode) -> bool:
        return (
            left.name == right.name
            and self.instances_index(left.instances_index, right.instances_index)
            and self.visit(left.operand, right.operand)
        )

    def time_aggregator(
        self, left: TimeAggregatorNode, right: TimeAggregatorNode
    ) -> bool:
        return (
            left.name == right.name
            and left.stay_roll == right.stay_roll
            and self.visit(left.operand, right.operand)
        )

    def scenario_operator(
        self, left: ScenarioOperatorNode, right: ScenarioOperatorNode
    ) -> bool:
        return left.name == right.name and self.visit(left.operand, right.operand)

    def port_field(self, left: PortFieldNode, right: PortFieldNode) -> bool:
        return left.port_name == right.port_name and left.field_name == right.field_name

    def port_field_aggregator(
        self, left: PortFieldAggregatorNode, right: PortFieldAggregatorNode
    ) -> bool:
        return left.aggregator == right.aggregator and self.visit(
            left.operand, right.operand
        )


def expressions_equal(
    left: ExpressionNodeEfficient,
    right: ExpressionNodeEfficient,
    abs_tol: float = 0,
    rel_tol: float = 0,
) -> bool:
    """
    True if both expression nodes are equal. Literal values may be compared with absolute or relative tolerance.
    """
    return EqualityVisitor(abs_tol, rel_tol).visit(left, right)


def expressions_equal_if_present(
    lhs: Optional[ExpressionNodeEfficient], rhs: Optional[ExpressionNodeEfficient]
) -> bool:
    if lhs is None and rhs is None:
        return True
    elif lhs is None or rhs is None:
        return False
    else:
        return expressions_equal(lhs, rhs)
