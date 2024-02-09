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
from dataclasses import dataclass
from typing import List

from andromede.expression.evaluate import InstancesIndexVisitor, ValueProvider

from .copy import CopyVisitor
from .expression import (
    ComponentParameterNode,
    ExpressionNode,
    ExpressionRange,
    InstancesTimeIndex,
    LiteralNode,
    ParameterNode,
)
from .visitor import visit


class ParameterValueProvider(ABC):
    @abstractmethod
    def get_parameter_value(self, name: str) -> float:
        ...

    @abstractmethod
    def get_component_parameter_value(self, component_id: str, name: str) -> float:
        ...


@dataclass(frozen=True)
class ParameterResolver(CopyVisitor):
    """
    Duplicates the AST with replacement of parameter nodes by literal nodes.
    """

    context: ParameterValueProvider

    def parameter(self, node: ParameterNode) -> ExpressionNode:
        value: float = self.context.get_parameter_value(node.name)
        return LiteralNode(value)

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNode:
        value: float = self.context.get_component_parameter_value(
            node.component_id, node.name
        )
        return LiteralNode(value)


def resolve_parameters(
    expression: ExpressionNode, parameter_provider: ParameterValueProvider
) -> ExpressionNode:
    return visit(expression, ParameterResolver(parameter_provider))


def float_to_int(value: float) -> int:
    if isinstance(value, int) or value.is_integer():
        return int(value)
    else:
        raise ValueError(f"{value} is not an integer.")


def evaluate_time_id(expr: ExpressionNode, value_provider: ValueProvider) -> int:
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
