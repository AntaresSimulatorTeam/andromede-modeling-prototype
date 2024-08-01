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

import pytest
from unittest.mock import Mock

from andromede.hydro_heuristic.data import (
    HydroHeuristicData,
    calculate_weekly_target,
    get_number_of_days_in_month,
    DataAggregator,
    RawHydroData,
)


def test_calculate_weekly_target() -> None:
    output = calculate_weekly_target([0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0])

    assert len(output) == 2
    assert output[0] == 21
    assert output[1] == 21


def test_hydro_heuristic_data_building() -> None:
    capacity = 1e07
    folder_name = "hydro_with_rulecurves"
    initial_level = 0.445 * capacity

    data = HydroHeuristicData(
        scenario=0,
        hours_aggregated_time_steps=[
            24 * get_number_of_days_in_month(m) for m in range(12)
        ],
        folder_name=folder_name,
        timesteps=list(range(12)),
        capacity=capacity,
        initial_level=initial_level,
    )

    assert len(data.demand) == 12
    assert len(data.inflow) == 12
    assert len(data.lower_rule_curve) == 12
    assert len(data.upper_rule_curve) == 12
    assert len(data.max_generating) == 12
    assert data.demand[0] == 37559973
    assert data.inflow[0] == 140447
    assert data.lower_rule_curve[0] == 0.23
    assert data.upper_rule_curve[0] == 0.582
    assert data.max_generating[0] == 37200000


def test_compute_target() -> None:
    capacity = 1e07
    folder_name = "hydro_with_rulecurves"
    initial_level = 0.445 * capacity

    data = HydroHeuristicData(
        scenario=0,
        hours_aggregated_time_steps=[
            24 * get_number_of_days_in_month(m) for m in range(12)
        ],
        folder_name=folder_name,
        timesteps=list(range(12)),
        capacity=capacity,
        initial_level=initial_level,
    )

    data.compute_target(None, 1)

    assert data.target[0] == pytest.approx(0.0495627 * capacity)


def test_data_aggregator() -> None:

    mock_raw_data = Mock(spec=RawHydroData)
    mock_raw_data.time_series = list(range(10))

    data_aggregator = DataAggregator([2, 3, 4, 0, 1], [1, 3, 4])
    aggregated_data = data_aggregator.aggregate_data("sum", mock_raw_data)

    assert aggregated_data == [9, 0, 9]

    data_aggregator = DataAggregator([2, 3, 4, 0, 1], list(range(5)))
    aggregated_data = data_aggregator.aggregate_data("lag_first_element", mock_raw_data)

    assert aggregated_data == [2, 5, 9, 9, 0]
