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
from typing import List, Union, cast

from .expression import (
    ComparisonNode,
    ComponentParameterNode,
    ComponentVariableNode,
    DecisionTreeParameterNode,
    DecisionTreeVariableNode,
    ExpressionNode,
    ExpressionRange,
    InstancesTimeIndex,
    LiteralNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    TimeAggregatorNode,
    TimeOperatorNode,
    VariableNode,
)
from .visitor import ExpressionVisitor, ExpressionVisitorOperations, T, visit


@dataclass(frozen=True)
class CopyVisitor(ExpressionVisitorOperations[ExpressionNode]):
    """
    Simply copies the whole AST.
    """

    def literal(self, node: LiteralNode) -> ExpressionNode:
        return LiteralNode(node.value)

    def comparison(self, node: ComparisonNode) -> ExpressionNode:
        return ComparisonNode(
            visit(node.left, self), visit(node.right, self), node.comparator
        )

    def variable(self, node: VariableNode) -> ExpressionNode:
        return VariableNode(node.name)

    def parameter(self, node: ParameterNode) -> ExpressionNode:
        return ParameterNode(node.name)

    def comp_variable(self, node: ComponentVariableNode) -> ExpressionNode:
        return ComponentVariableNode(node.component_id, node.name)

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNode:
        return ComponentParameterNode(node.component_id, node.name)

    def dt_variable(self, node: DecisionTreeVariableNode) -> ExpressionNode:
        return DecisionTreeVariableNode(
            node.decision_tree_id, node.component_id, node.name
        )

    def dt_parameter(self, node: DecisionTreeParameterNode) -> ExpressionNode:
        return DecisionTreeParameterNode(
            node.decision_tree_id, node.component_id, node.name
        )

    def copy_expression_range(
        self, expression_range: ExpressionRange
    ) -> ExpressionRange:
        return ExpressionRange(
            start=visit(expression_range.start, self),
            stop=visit(expression_range.stop, self),
            step=visit(expression_range.step, self)
            if expression_range.step is not None
            else None,
        )

    def copy_instances_index(
        self, instances_index: InstancesTimeIndex
    ) -> InstancesTimeIndex:
        expressions = instances_index.expressions
        if isinstance(expressions, ExpressionRange):
            return InstancesTimeIndex(self.copy_expression_range(expressions))
        if isinstance(expressions, list):
            expressions_list = cast(List[ExpressionNode], expressions)
            copy = [visit(e, self) for e in expressions_list]
            return InstancesTimeIndex(copy)
        raise ValueError("Unexpected type in instances index")

    def time_operator(self, node: TimeOperatorNode) -> ExpressionNode:
        return TimeOperatorNode(
            visit(node.operand, self),
            node.name,
            self.copy_instances_index(node.instances_index),
        )

    def time_aggregator(self, node: TimeAggregatorNode) -> ExpressionNode:
        return TimeAggregatorNode(visit(node.operand, self), node.name, node.stay_roll)

    def scenario_operator(self, node: ScenarioOperatorNode) -> ExpressionNode:
        return ScenarioOperatorNode(visit(node.operand, self), node.name)

    def port_field(self, node: PortFieldNode) -> ExpressionNode:
        return PortFieldNode(node.port_name, node.field_name)

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> ExpressionNode:
        return PortFieldAggregatorNode(visit(node.operand, self), node.aggregator)


def copy_expression(expression: ExpressionNode) -> ExpressionNode:
    return visit(expression, CopyVisitor())
