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
from typing import List, cast

from .expression_efficient import (
    ComparisonNode,
    ComponentParameterNode,
    ExpressionNodeEfficient,
    ExpressionRange,
    InstancesTimeIndex,
    LiteralNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    TimeAggregatorNode,
    TimeOperatorNode,
)
from .visitor import ExpressionVisitorOperations, visit


@dataclass(frozen=True)
class CopyVisitor(ExpressionVisitorOperations[ExpressionNodeEfficient]):
    """
    Simply copies the whole AST.
    """

    def literal(self, node: LiteralNode) -> ExpressionNodeEfficient:
        return LiteralNode(node.value)

    def comparison(self, node: ComparisonNode) -> ExpressionNodeEfficient:
        return ComparisonNode(
            visit(node.left, self), visit(node.right, self), node.comparator
        )

    # def variable(self, node: VariableNode) -> ExpressionNodeEfficient:
    #     return VariableNode(node.name)

    def parameter(self, node: ParameterNode) -> ExpressionNodeEfficient:
        return ParameterNode(node.name)

    # def comp_variable(self, node: ComponentVariableNode) -> ExpressionNodeEfficient:
    #     return ComponentVariableNode(node.component_id, node.name)

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNodeEfficient:
        return ComponentParameterNode(node.component_id, node.name)

    def copy_expression_range(
        self, expression_range: ExpressionRange
    ) -> ExpressionRange:
        return ExpressionRange(
            start=visit(expression_range.start, self),
            stop=visit(expression_range.stop, self),
            step=(
                visit(expression_range.step, self)
                if expression_range.step is not None
                else None
            ),
        )

    def copy_instances_index(
        self, instances_index: InstancesTimeIndex
    ) -> InstancesTimeIndex:
        expressions = instances_index.expressions
        if isinstance(expressions, ExpressionRange):
            return InstancesTimeIndex(self.copy_expression_range(expressions))
        if isinstance(expressions, list):
            expressions_list = cast(List[ExpressionNodeEfficient], expressions)
            copy = [visit(e, self) for e in expressions_list]
            return InstancesTimeIndex(copy)
        raise ValueError("Unexpected type in instances index")

    def time_operator(self, node: TimeOperatorNode) -> ExpressionNodeEfficient:
        return TimeOperatorNode(
            visit(node.operand, self),
            node.name,
            self.copy_instances_index(node.instances_index),
        )

    def time_aggregator(self, node: TimeAggregatorNode) -> ExpressionNodeEfficient:
        return TimeAggregatorNode(visit(node.operand, self), node.name, node.stay_roll)

    def scenario_operator(self, node: ScenarioOperatorNode) -> ExpressionNodeEfficient:
        return ScenarioOperatorNode(visit(node.operand, self), node.name)

    def port_field(self, node: PortFieldNode) -> ExpressionNodeEfficient:
        return PortFieldNode(node.port_name, node.field_name)

    def port_field_aggregator(
        self, node: PortFieldAggregatorNode
    ) -> ExpressionNodeEfficient:
        return PortFieldAggregatorNode(visit(node.operand, self), node.aggregator)


def copy_expression(expression: ExpressionNodeEfficient) -> ExpressionNodeEfficient:
    return visit(expression, CopyVisitor())
