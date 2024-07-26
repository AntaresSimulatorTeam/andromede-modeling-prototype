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
from typing import Dict

from andromede.expression.expression import VariableNode
from andromede.expression.expression_efficient import (
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

from .visitor import ExpressionVisitor, ExpressionVisitorOperations, T, visit


class ValueProvider(ABC):
    """
    Implementations are in charge of mapping parameters and variables to their values.
    Depending on the implementation, evaluation may require a component id or not.
    """

    # @abstractmethod
    # def get_variable_value(self, name: str) -> float:
    #     ...

    @abstractmethod
    def get_parameter_value(self, name: str) -> float:
        ...

    # @abstractmethod
    # def get_component_variable_value(self, component_id: str, name: str) -> float:
        # ...

    @abstractmethod
    def get_component_parameter_value(self, component_id: str, name: str) -> float:
        ...

    # TODO: Should this really be an abstract method ? Or maybe, only the Provider in _make_value_provider should implement it. And the context attribute in the InstancesIndexVisitor is a ValueProvider that implements the parameter_is_constant_over_time method. Maybe create a child class of ValueProvider like TimeValueProvider ?
    @abstractmethod
    def parameter_is_constant_over_time(self, name: str) -> bool:
        ...


@dataclass(frozen=True)
class EvaluationContext(ValueProvider):
    """
    Simple value provider relying on dictionaries.
    Does not support component variables/parameters.
    """

    variables: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, float] = field(default_factory=dict)

    def get_variable_value(self, name: str) -> float:
        return self.variables[name]

    def get_parameter_value(self, name: str) -> float:
        return self.parameters[name]

    def get_component_variable_value(self, component_id: str, name: str) -> float:
        raise NotImplementedError()

    def get_component_parameter_value(self, component_id: str, name: str) -> float:
        raise NotImplementedError()

    def parameter_is_constant_over_time(self, name: str) -> bool:
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

    def variable(self, node: VariableNode) -> float:
        return self.context.get_variable_value(node.name)

    def parameter(self, node: ParameterNode) -> float:
        return self.context.get_parameter_value(node.name)

    def comp_parameter(self, node: ComponentParameterNode) -> float:
        return self.context.get_component_parameter_value(node.component_id, node.name)

    # def comp_variable(self, node: ComponentVariableNode) -> float:
    #     return self.context.get_component_variable_value(node.component_id, node.name)

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

    def variable(self, node: VariableNode) -> float:
        raise ValueError("An instance index expression cannot contain variable")

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
