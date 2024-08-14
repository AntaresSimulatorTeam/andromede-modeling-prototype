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
from dataclasses import dataclass, field
from typing import Dict, List

from andromede.expression.expression import VariableNode
from andromede.expression.expression_efficient import (
    ComparisonNode,
    ComponentParameterNode,
    ExpressionNodeEfficient,
    ExpressionRange,
    InstancesTimeIndex,
    LiteralNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorName,
    ScenarioOperatorNode,
    TimeAggregatorName,
    TimeAggregatorNode,
    TimeOperatorName,
    TimeOperatorNode,
)
from andromede.expression.indexing_structure import RowIndex

from .visitor import ExpressionVisitor, ExpressionVisitorOperations, T, visit


@dataclass
class TimeScenarioIndices:
    time_indices: List[int]
    scenario_indices: List[int]


class ValueProvider(ABC):
    """
    Implementations are in charge of mapping parameters and variables to their values.
    Depending on the implementation, evaluation may require a component id or not.
    """

    # @abstractmethod
    # def get_variable_value(self, name: str) -> float: ...

    @abstractmethod
    def get_parameter_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> List[float]: ...

    # @abstractmethod
    # def get_component_variable_value(self, component_id: str, name: str) -> float: ...

    @abstractmethod
    def get_component_parameter_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> List[float]: ...

    # TODO: Should this really be an abstract method ? Or maybe, only the Provider in _make_value_provider should implement it. And the context attribute in the InstancesIndexVisitor is a ValueProvider that implements the parameter_is_constant_over_time method. Maybe create a child class of ValueProvider like TimeValueProvider ?
    @abstractmethod
    def parameter_is_constant_over_time(self, name: str) -> bool: ...


@dataclass(frozen=True)
class ParameterEvaluationVisitor(ExpressionVisitorOperations[float]):
    """
    Evaluates the expression with respect to the provided context
    (variables and parameters values).
    """

    context: ValueProvider
    row_id: RowIndex  # TODO to be included in ValueProvider ?
    time_scenario_indices: TimeScenarioIndices

    def literal(self, node: LiteralNode) -> float:
        return [node.value]

    # def comparison(self, node: ComparisonNode) -> float:
    #     raise ValueError("Cannot evaluate comparison operator.")

    # def variable(self, node: VariableNode) -> float:
    #     return self.context.get_variable_value(node.name)

    def parameter(self, node: ParameterNode) -> float:
        return self.context.get_parameter_value(node.name, self.time_scenario_indices)

    def comp_parameter(self, node: ComponentParameterNode) -> float:
        return self.context.get_component_parameter_value(
            node.component_id, node.name, self.time_scenario_indices
        )

    # def comp_variable(self, node: ComponentVariableNode) -> float:
    #     return self.context.get_component_variable_value(node.component_id, node.name)

    def time_operator(self, node: TimeOperatorNode) -> float:
        self.time_scenario_indices.time_indices = get_time_ids_from_instances_index(
            node.instances_index, self.context
        )
        if node.name == TimeOperatorName.SHIFT:
            self.time_scenario_indices.time_indices = [
                self.row_id.time + op_id
                for op_id in self.time_scenario_indices.time_indices
            ]
        elif node.name != TimeOperatorName.EVALUATION:
            return NotImplemented
        return visit(node.operand, self)

    def time_aggregator(self, node: TimeAggregatorNode) -> float:
        if node.name in [TimeAggregatorName.SUM]:
            # TODO: Where is the sum ?
            return visit(node.operand, self)
        else:
            return NotImplemented

    def scenario_operator(self, node: ScenarioOperatorNode) -> float:
        if node.name in [ScenarioOperatorName.EXPECTATION]:
            return visit(node.operand, self)
        else:
            return NotImplemented

    def port_field(self, node: PortFieldNode) -> float:
        raise ValueError("Port fields must be resolved before evaluating parameters")

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> float:
        raise ValueError("Port fields must be resolved before evaluating parameters")


def resolve_coefficient(
    expression: ExpressionNodeEfficient, value_provider: ValueProvider, row_id: RowIndex
) -> float:
    return visit(expression, ParameterEvaluationVisitor(value_provider, row_id))


@dataclass(frozen=True)
class InstancesIndexVisitor(ParameterEvaluationVisitor):
    """
    Evaluates an expression given as instances index which should have no variable and constant parameter values.
    """

    # def variable(self, node: VariableNode) -> float:
    #     raise ValueError("An instance index expression cannot contain variable")

    def parameter(self, node: ParameterNode) -> float:
        if not self.context.parameter_is_constant_over_time(node.name):
            raise ValueError(
                "Parameter given in an instance index expression must be constant over time"
            )
        return self.context.get_parameter_value(node.name)

    def time_operator(self, node: TimeOperatorNode) -> float:
        raise ValueError("An instance index expression cannot contain time operator")

    def time_aggregator(self, node: TimeAggregatorNode) -> float:
        raise ValueError("An instance index expression cannot contain time aggregator")


def float_to_int(value: float) -> int:
    if isinstance(value, int) or value.is_integer():
        return int(value)
    else:
        raise ValueError(f"{value} is not an integer.")


def evaluate_time_id(
    expr: ExpressionNodeEfficient, value_provider: ValueProvider
) -> int:
    float_time_id = visit(expr, InstancesIndexVisitor(value_provider))
    try:
        time_id = float_to_int(float_time_id)
    except ValueError:
        print(f"{expr} does not represent an integer time index.")
    return time_id


def get_time_ids_from_instances_index(
    instances_index: InstancesTimeIndex, value_provider: ValueProvider
) -> List[int]:
    time_ids = []
    if isinstance(instances_index.expressions, list):  # List[ExpressionNode]
        for expr in instances_index.expressions:
            time_ids.append(evaluate_time_id(expr, value_provider))

    elif isinstance(instances_index.expressions, ExpressionRange):  # ExpressionRange
        start_id = evaluate_time_id(instances_index.expressions.start, value_provider)
        stop_id = evaluate_time_id(instances_index.expressions.stop, value_provider)
        step_id = 1
        if instances_index.expressions.step is not None:
            step_id = evaluate_time_id(instances_index.expressions.step, value_provider)
        # ExpressionRange includes stop_id whereas range excludes it
        time_ids = list(range(start_id, stop_id + 1, step_id))

    return time_ids
