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
import re
from typing import Dict

import pytest

from andromede.expression.evaluate_parameters_efficient import resolve_coefficient
from andromede.expression.expression_efficient import (
    Comparator,
    ComparisonNode,
    ExpressionNodeEfficient,
    ExpressionRange,
    InstancesTimeIndex,
    LiteralNode,
    PortFieldAggregatorName,
    PortFieldAggregatorNode,
    PortFieldNode,
    TimeOperatorName,
    TimeOperatorNode,
    comp_param,
    literal,
    param,
)
from andromede.expression.indexing_structure import IndexingStructure, RowIndex
from andromede.expression.value_provider import (
    TimeScenarioIndex,
    TimeScenarioIndices,
    ValueProvider,
)

p_values = {
    TimeScenarioIndex(0, 0): 1.0,
    TimeScenarioIndex(1, 0): 2.0,
    TimeScenarioIndex(2, 0): 3.0,
    TimeScenarioIndex(3, 0): 7.0,
    TimeScenarioIndex(0, 1): 4.0,
    TimeScenarioIndex(1, 1): 5.0,
    TimeScenarioIndex(2, 1): 6.0,
    TimeScenarioIndex(3, 1): 8.0,
}

# A time constant parameter that can be put as TimeShift arg
comp_q_values = {
    TimeScenarioIndex(0, 0): 2.0,
    TimeScenarioIndex(0, 1): 1.0,
}


def _get_data_time_key(block_timestep: int, data_indexing: IndexingStructure) -> int:
    return block_timestep if data_indexing.time else 0


def _get_data_scenario_key(scenario: int, data_indexing: IndexingStructure) -> int:
    return scenario if data_indexing.scenario else 0


class CustomValueProvider(ValueProvider):
    def get_component_variable_value(
        self,
        component_id: str,
        name: str,
        time_scenarios_indices: TimeScenarioIndices,
    ) -> Dict[TimeScenarioIndex, float]:
        raise NotImplementedError(
            "Cannot provide variable value at problem build time."
        )

    def get_component_parameter_value(
        self,
        component_id: str,
        name: str,
        time_scenarios_indices: TimeScenarioIndices,
    ) -> Dict[TimeScenarioIndex, float]:
        result = {}
        param_indexing = IndexingStructure(False, True)
        for block_timestep in time_scenarios_indices.time_indices:
            for scenario in time_scenarios_indices.scenario_indices:
                result[TimeScenarioIndex(block_timestep, scenario)] = comp_q_values[
                    TimeScenarioIndex(
                        _get_data_time_key(block_timestep, param_indexing),
                        _get_data_scenario_key(scenario, param_indexing),
                    )
                ]
        return result

    def get_variable_value(
        self,
        name: str,
        time_scenarios_indices: TimeScenarioIndices,
    ) -> Dict[TimeScenarioIndex, float]:
        raise NotImplementedError(
            "Cannot provide variable value at problem build time."
        )

    def get_parameter_value(
        self,
        name: str,
        time_scenarios_indices: TimeScenarioIndices,
    ) -> Dict[TimeScenarioIndex, float]:
        result = {}
        param_indexing = IndexingStructure(True, True)
        for block_timestep in time_scenarios_indices.time_indices:
            for scenario in time_scenarios_indices.scenario_indices:
                result[TimeScenarioIndex(block_timestep, scenario)] = p_values[
                    TimeScenarioIndex(
                        _get_data_time_key(block_timestep, param_indexing),
                        _get_data_scenario_key(scenario, param_indexing),
                    )
                ]
        return result

    def parameter_is_constant_over_time(self, name: str) -> bool:
        return True

    @staticmethod
    def block_length() -> int:
        return 4

    @staticmethod
    def scenarios() -> int:
        return 2


@pytest.fixture
def provider() -> CustomValueProvider:
    return CustomValueProvider()


@pytest.mark.parametrize(
    "port_node",
    [
        (PortFieldNode("port", "field")),
        (
            PortFieldAggregatorNode(
                PortFieldNode("port", "field"), PortFieldAggregatorName.PORT_SUM
            )
        ),
    ],
)
def test_resolve_coefficient_raises_value_error_on_port_field_node(
    port_node: ExpressionNodeEfficient, provider: CustomValueProvider
) -> None:
    with pytest.raises(
        ValueError, match="Port fields must be resolved before evaluating parameters"
    ):
        resolve_coefficient(port_node, provider, RowIndex(0, 0))


def test_resolve_coefficient_raises_value_error_on_comparison_node(
    provider: CustomValueProvider,
) -> None:
    expr = ComparisonNode(LiteralNode(0), param("p"), Comparator.EQUAL)
    with pytest.raises(ValueError, match="Cannot evaluate comparison operator."):
        resolve_coefficient(expr, provider, RowIndex(0, 0))


@pytest.mark.parametrize(
    "expr",
    [
        (
            TimeOperatorNode(
                param("p"),
                TimeOperatorName.SHIFT,
                InstancesTimeIndex([LiteralNode(1), LiteralNode(2)]),
            )
        ),
        (
            TimeOperatorNode(
                param("p"),
                TimeOperatorName.EVALUATION,
                InstancesTimeIndex([LiteralNode(1), LiteralNode(2)]),
            )
        ),
    ],
)
def test_resolve_coefficient_raises_value_error_on_expressions_that_are_not_aggregated_on_a_single_time_and_scenario(
    expr: ExpressionNodeEfficient, provider: CustomValueProvider
) -> None:
    with pytest.raises(
        ValueError, match="Evaluation of expression cannot be reduced to a float value"
    ):
        resolve_coefficient(expr, provider, RowIndex(0, 0))


@pytest.mark.parametrize(
    "expr",
    [
        (param("p").shift(2)),
        (param("p").eval(2)),
        param("p").shift(comp_param("c", "q")),
    ],
)
def test_resolve_coefficient_on_expression_with_shift_but_without_sum_raises_value_error(
    expr: ExpressionNodeEfficient,
    provider: CustomValueProvider,
) -> None:
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Expression has a time operator but not time aggregator, maybe you are missing a sum(), necessary even on one element"
        ),
    ):
        resolve_coefficient(expr, provider, RowIndex(0, 0))


@pytest.mark.parametrize(
    "expr",
    [
        (
            TimeOperatorNode(
                param("p"),
                TimeOperatorName.EVALUATION,
                InstancesTimeIndex([comp_param("c", "q")]),
            )
        ),
        (
            TimeOperatorNode(
                param("p"),
                TimeOperatorName.SHIFT,
                InstancesTimeIndex([param("q")]),
            )
        ),
    ],
)
def test_resolve_coefficient_with_no_time_varying_parameter_in_time_operator_argument_raises_value_error(
    expr: ExpressionNodeEfficient,
) -> None:
    class TimeVaryingParameterValueProvider(CustomValueProvider):
        def parameter_is_constant_over_time(self, name: str) -> bool:
            return False

    provider = TimeVaryingParameterValueProvider()

    with pytest.raises(
        ValueError,
        match="Parameter given in an instance index expression must be constant over time",
    ):
        resolve_coefficient(expr, provider, RowIndex(0, 0))


@pytest.mark.parametrize(
    "expr, row_id, expected",
    [
        (param("p"), RowIndex(0, 0), 1.0),
        (comp_param("c", "q"), RowIndex(0, 0), 2.0),
        (-comp_param("c", "q"), RowIndex(0, 0), -2.0),
        (param("p") + comp_param("c", "q"), RowIndex(0, 0), 3.0),
        (param("p") - comp_param("c", "q"), RowIndex(0, 0), -1.0),
        (param("p") * LiteralNode(2), RowIndex(0, 0), 2.0),
        (param("p") / LiteralNode(2), RowIndex(0, 0), 0.5),
    ],
)
def test_resolve_coefficient_on_elementary_operations(
    expr: ExpressionNodeEfficient,
    row_id: RowIndex,
    expected: float,
    provider: CustomValueProvider,
) -> None:
    assert math.isclose(resolve_coefficient(expr, provider, row_id), expected)


@pytest.mark.parametrize(
    "expr, row_id, expected",
    [
        (param("p").shift(2).sum(), RowIndex(0, 0), 3.0),
        (param("p").shift(-1).sum(), RowIndex(2, 1), 5.0),
        (literal(0).shift(-1).sum(), RowIndex(0, 0), 0.0),
        (param("p").eval(2).sum(), RowIndex(0, 0), 3.0),
        (param("p").eval(2).sum(), RowIndex(2, 0), 3.0),
        (param("p").shift(ExpressionRange(0, 3)).sum(), RowIndex(0, 0), 13.0),
        (param("p").eval(ExpressionRange(1, 2)).sum(), RowIndex(0, 0), 5.0),
        (param("p").eval(ExpressionRange(0, 3, 2)).sum(), RowIndex(0, 0), 4.0),
        (param("p").shift(comp_param("c", "q")).sum(), RowIndex(1, 0), 7.0),
        (param("p").shift(comp_param("c", "q")).sum(), RowIndex(1, 1), 6.0),
        (param("p").sum(), RowIndex(0, 0), 13.0),
        (param("p").sum(), RowIndex(2, 1), 23.0),
        (comp_param("c", "q").sum(), RowIndex(0, 0), 2 * 4.0),
    ],
)
def test_resolve_coefficient_on_time_shift_and_sum(
    expr: ExpressionNodeEfficient,
    row_id: RowIndex,
    expected: float,
    provider: CustomValueProvider,
) -> None:
    assert math.isclose(resolve_coefficient(expr, provider, row_id), expected)


@pytest.mark.parametrize(
    "expr, row_id, expected",
    [
        (param("p").expec(), RowIndex(0, 0), 2.5),
        (param("p").expec(), RowIndex(1, 1), 3.5),
        (comp_param("c", "q").expec(), RowIndex(1, 1), 1.5),
    ],
)
def test_resolve_coefficient_on_expectation(
    expr: ExpressionNodeEfficient,
    row_id: RowIndex,
    expected: float,
    provider: CustomValueProvider,
) -> None:
    assert math.isclose(resolve_coefficient(expr, provider, row_id), expected)


@pytest.mark.parametrize(
    "expr, row_id, expected",
    [
        (param("p").expec().sum(), RowIndex(0, 0), 18.0),
        (param("p").sum().expec(), RowIndex(0, 0), 18.0),
        (param("p").shift(comp_param("c", "q")).sum().expec(), RowIndex(1, 0), 6.5),
        (param("p").expec().shift(comp_param("c", "q")).sum(), RowIndex(1, 0), 7.5),
        (param("p").shift(comp_param("c", "q")).expec().sum(), RowIndex(1, 0), 6.5),
    ],
)
def test_resolve_coefficient_on_sum_and_expectation(
    expr: ExpressionNodeEfficient,
    row_id: RowIndex,
    expected: float,
    provider: CustomValueProvider,
) -> None:
    assert math.isclose(resolve_coefficient(expr, provider, row_id), expected)
