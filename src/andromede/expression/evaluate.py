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

from dataclasses import dataclass, field
from typing import Dict

from .expression_efficient import (
    ComparisonNode,
    ComponentParameterNode,
    ExpressionNodeEfficient,
    LiteralNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    TimeAggregatorNode,
    TimeOperatorNode,
)
from .value_provider import TimeScenarioIndex, TimeScenarioIndices, ValueProvider
from .visitor import ExpressionVisitorOperations, visit


# Used only for tests
@dataclass(frozen=True)
class EvaluationContext(ValueProvider):
    """
    Simple value provider relying on dictionaries.
    Does not support component variables/parameters.
    """

    variables: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, float] = field(default_factory=dict)

    def get_variable_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        return {TimeScenarioIndex(0, 0): self.variables[name]}

    def get_parameter_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        return {TimeScenarioIndex(0, 0): self.parameters[name]}

    def get_component_variable_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        raise NotImplementedError()

    def get_component_parameter_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        raise NotImplementedError()

    def parameter_is_constant_over_time(self, name: str) -> bool:
        raise NotImplementedError()

    @staticmethod
    def block_length() -> int:
        raise NotImplementedError()

    @staticmethod
    def scenarios() -> int:
        raise NotImplementedError()


@dataclass(frozen=True)
class EvaluationVisitor(ExpressionVisitorOperations[float]):
    """
    Evaluates the expression with respect to the provided context
    (variables and parameters values).
    """

    context: ValueProvider

    def literal(self, node: LiteralNode) -> float:
        return node.value

    def comparison(self, node: ComparisonNode) -> float:
        raise ValueError("Cannot evaluate comparison operator.")

    def parameter(self, node: ParameterNode) -> float:
        return self.context.get_parameter_value(node.name)

    def comp_parameter(self, node: ComponentParameterNode) -> float:
        return self.context.get_component_parameter_value(node.component_id, node.name)

    def time_operator(self, node: TimeOperatorNode) -> float:
        raise NotImplementedError()

    def time_aggregator(self, node: TimeAggregatorNode) -> float:
        raise NotImplementedError()

    def scenario_operator(self, node: ScenarioOperatorNode) -> float:
        raise NotImplementedError()

    def port_field(self, node: PortFieldNode) -> float:
        raise NotImplementedError()

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> float:
        raise NotImplementedError()


def evaluate(
    expression: ExpressionNodeEfficient, value_provider: ValueProvider
) -> float:
    return visit(expression, EvaluationVisitor(value_provider))


@dataclass(frozen=True)
class InstancesIndexVisitor(EvaluationVisitor):
    """
    Evaluates an expression given as instances index which should have no variable and constant parameter values.
    """

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
