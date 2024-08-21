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

import operator
from dataclasses import dataclass, field
from typing import Callable, Dict, List

from .expression_efficient import (
    AdditionNode,
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
    ScenarioOperatorName,
    ScenarioOperatorNode,
    SubstractionNode,
    TimeAggregatorName,
    TimeAggregatorNode,
    TimeOperatorName,
    TimeOperatorNode,
)
from .indexing_structure import RowIndex
from .value_provider import TimeScenarioIndex, TimeScenarioIndices, ValueProvider
from .visitor import ExpressionVisitor, visit


# TODO: (almost) same function as in linear_expression _merge_dicts
def _merge_dicts(
    lhs: Dict[TimeScenarioIndex, float],
    rhs: Dict[TimeScenarioIndex, float],
    merge_func: Callable[[float, float], float],
    neutral: float,
) -> Dict[TimeScenarioIndex, float]:
    res = {}
    for k, v in lhs.items():
        res[k] = merge_func(v, rhs.get(k, neutral))
    for k, v in rhs.items():
        if k not in lhs:
            res[k] = merge_func(neutral, v)
    return res


# It is better to return a list of float than a single float to minimize the number of calls to the visit function. We access values of the parameters at different time steps with a single visit of the tree
@dataclass(frozen=True)
class ParameterEvaluationVisitor(ExpressionVisitor[Dict[TimeScenarioIndex, float]]):
    """
    Evaluates the expression with respect to the provided context
    (variables and parameters values).
    """

    context: ValueProvider
    # Useful to keep track of row id for time shift
    row_id: RowIndex  # TODO to be included in ValueProvider ?
    time_scenario_indices: TimeScenarioIndices = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "time_scenario_indices",
            TimeScenarioIndices([self.row_id.time], [self.row_id.scenario]),
        )

    # Redefine common operations so that it works as expected on lists (i.e. summing element wise rather than appending to it)
    def negation(self, node: NegationNode) -> Dict[TimeScenarioIndex, float]:
        return {k: -v for k, v in visit(node.operand, self).items()}

    def addition(self, node: AdditionNode) -> Dict[TimeScenarioIndex, float]:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        result = _merge_dicts(left_value, right_value, operator.add, 0)
        return result

    def substraction(self, node: SubstractionNode) -> Dict[TimeScenarioIndex, float]:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        result = _merge_dicts(left_value, right_value, operator.sub, 0)
        return result

    def multiplication(
        self, node: MultiplicationNode
    ) -> Dict[TimeScenarioIndex, float]:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        result = _merge_dicts(left_value, right_value, operator.mul, 1)
        return result

    def division(self, node: DivisionNode) -> Dict[TimeScenarioIndex, float]:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        result = _merge_dicts(left_value, right_value, operator.truediv, 1)
        return result

    def literal(self, node: LiteralNode) -> Dict[TimeScenarioIndex, float]:
        result = {}
        for time in self.time_scenario_indices.time_indices:
            for scenario in self.time_scenario_indices.scenario_indices:
                result[TimeScenarioIndex(time, scenario)] = node.value
        return result

    def comparison(self, node: ComparisonNode) -> Dict[TimeScenarioIndex, float]:
        raise ValueError("Cannot evaluate comparison operator.")

    def parameter(self, node: ParameterNode) -> Dict[TimeScenarioIndex, float]:
        return self.context.get_parameter_value(node.name, self.time_scenario_indices)

    def comp_parameter(
        self, node: ComponentParameterNode
    ) -> Dict[TimeScenarioIndex, float]:
        return self.context.get_component_parameter_value(
            node.component_id, node.name, self.time_scenario_indices
        )

    def time_operator(self, node: TimeOperatorNode) -> Dict[TimeScenarioIndex, float]:
        self.time_scenario_indices.time_indices = get_time_ids_from_instances_index(
            node.instances_index, self.context, self.row_id
        )
        if node.name == TimeOperatorName.SHIFT:
            self.time_scenario_indices.time_indices = [
                self.row_id.time + op_id
                for op_id in self.time_scenario_indices.time_indices
            ]
        elif node.name != TimeOperatorName.EVALUATION:
            return NotImplemented
        return visit(node.operand, self)

    def time_aggregator(
        self, node: TimeAggregatorNode
    ) -> Dict[TimeScenarioIndex, float]:
        if node.name == TimeAggregatorName.TIME_SUM:
            if not isinstance(node.operand, TimeOperatorNode):
                # Sum over all time block
                self.time_scenario_indices.time_indices = list(
                    range(self.context.block_length())
                )
            # Time indices for the case where node.operand is a TimeOperatorNode are handled in time_operator function directly
            operand_dict = visit(node.operand, self)
            result = {}
            for scenario in self.time_scenario_indices.scenario_indices:
                result[TimeScenarioIndex(self.row_id.time, scenario)] = sum(
                    operand_dict[k]
                    for k in operand_dict.keys()
                    if k.scenario == scenario
                )
            # As the sum aggregates on time, time indices on which to evaluate parent expression collapses on row_id.time
            self.time_scenario_indices.time_indices = [self.row_id.time]
            return result
        else:
            return NotImplemented

    def scenario_operator(
        self, node: ScenarioOperatorNode
    ) -> Dict[TimeScenarioIndex, float]:
        if node.name == ScenarioOperatorName.EXPECTATION:
            self.time_scenario_indices.scenario_indices = list(
                range(self.context.scenarios())
            )
            operand_dict = visit(node.operand, self)
            result = {}
            for time in self.time_scenario_indices.time_indices:
                # TODO: Make this more general to consider weighted expectations
                result[TimeScenarioIndex(time, self.row_id.scenario)] = (
                    1
                    / self.context.scenarios()
                    * sum(
                        operand_dict[k] for k in operand_dict.keys() if k.time == time
                    )
                )
            # As the expectation aggregates on scenario, scenario indices on which to evaluate parent expression collapses on row_id.scenario
            self.time_scenario_indices.scenario_indices = [self.row_id.scenario]
            return result

        else:
            return NotImplemented

    def port_field(self, node: PortFieldNode) -> Dict[TimeScenarioIndex, float]:
        raise ValueError("Port fields must be resolved before evaluating parameters")

    def port_field_aggregator(
        self, node: PortFieldAggregatorNode
    ) -> Dict[TimeScenarioIndex, float]:
        raise ValueError("Port fields must be resolved before evaluating parameters")


def check_resolved_expr(
    resolved_expr: Dict[TimeScenarioIndex, float], row_id: RowIndex
) -> None:
    # Check that the resolved expression has been correctly time and scenario aggregated so that only a float is left
    if len(resolved_expr) != 1:
        raise ValueError("Evaluation of expression cannot be reduced to a float value")
    if TimeScenarioIndex(row_id.time, row_id.scenario) not in resolved_expr:
        raise ValueError(
            "Expression has a time operator but not time aggregator, maybe you are missing a sum(), necessary even on one element"
        )


def resolve_coefficient(
    expression: ExpressionNodeEfficient, value_provider: ValueProvider, row_id: RowIndex
) -> float:
    result = visit(expression, ParameterEvaluationVisitor(value_provider, row_id))
    check_resolved_expr(result, row_id)
    return result[TimeScenarioIndex(row_id.time, row_id.scenario)]


@dataclass(frozen=True)
class InstancesIndexVisitor(ParameterEvaluationVisitor):
    """
    Evaluates an expression given as instances index which should have no variable and constant parameter values.
    """

    # def variable(self, node: VariableNode) -> float:
    #     raise ValueError("An instance index expression cannot contain variable")

    # Probably useless as parameter nodes should have already be replaced by component parameter nodes ?
    def parameter(self, node: ParameterNode) -> Dict[TimeScenarioIndex, float]:
        if not self.context.parameter_is_constant_over_time(node.name):
            raise ValueError(
                "Parameter given in an instance index expression must be constant over time"
            )

        return self.context.get_parameter_value(node.name, self.time_scenario_indices)

    def comp_parameter(
        self, node: ComponentParameterNode
    ) -> Dict[TimeScenarioIndex, float]:
        if not self.context.parameter_is_constant_over_time(node.name):
            raise ValueError(
                "Parameter given in an instance index expression must be constant over time"
            )
        return self.context.get_component_parameter_value(
            node.component_id, node.name, self.time_scenario_indices
        )

    def time_operator(self, node: TimeOperatorNode) -> Dict[TimeScenarioIndex, float]:
        raise ValueError("An instance index expression cannot contain time operator")

    def time_aggregator(
        self, node: TimeAggregatorNode
    ) -> Dict[TimeScenarioIndex, float]:
        raise ValueError("An instance index expression cannot contain time aggregator")


def float_to_int(value: float) -> int:
    if isinstance(value, int) or value.is_integer():
        return int(value)
    else:
        raise ValueError(f"{value} is not an integer.")


def evaluate_time_id(
    expr: ExpressionNodeEfficient, value_provider: ValueProvider, row_id: RowIndex
) -> int:
    float_time_id_in_list = visit(expr, InstancesIndexVisitor(value_provider, row_id))
    check_resolved_expr(float_time_id_in_list, row_id)
    try:
        time_id = float_to_int(
            float_time_id_in_list[TimeScenarioIndex(row_id.time, row_id.scenario)]
        )
    except ValueError:
        print(f"{expr} does not represent an integer time index.")
    return time_id


def get_time_ids_from_instances_index(
    instances_index: InstancesTimeIndex, value_provider: ValueProvider, row_id: RowIndex
) -> List[int]:
    time_ids = []
    if isinstance(instances_index.expressions, list):  # List[ExpressionNode]
        for expr in instances_index.expressions:
            time_ids.append(evaluate_time_id(expr, value_provider, row_id))

    elif isinstance(instances_index.expressions, ExpressionRange):  # ExpressionRange
        start_id = evaluate_time_id(
            instances_index.expressions.start, value_provider, row_id
        )
        stop_id = evaluate_time_id(
            instances_index.expressions.stop, value_provider, row_id
        )
        step_id = 1
        if instances_index.expressions.step is not None:
            step_id = evaluate_time_id(
                instances_index.expressions.step, value_provider, row_id
            )
        # ExpressionRange includes stop_id whereas range excludes it
        time_ids = list(range(start_id, stop_id + 1, step_id))

    return time_ids
