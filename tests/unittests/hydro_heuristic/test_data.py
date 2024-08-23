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


from pathlib import Path

import pytest

from andromede.hydro_heuristic.data import (
    DataAggregator,
    DataAggregatorParameters,
    HydroHeuristicData,
    HydroHeuristicParameters,
    ReservoirParameters,
    compute_weekly_target,
    get_number_of_days_in_month,
)


def test_calculate_weekly_target() -> None:
    output = compute_weekly_target([0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6, 0])

    assert len(output) == 2
    assert output[0] == 21
    assert output[1] == 21


def test_hydro_heuristic_data_building() -> None:
    capacity = 1e07
    folder_name = (
        str(Path(__file__).parent) + "../../tests/functional/data/hydro_with_rulecurves"
    )
    initial_level = 0.445 * capacity

    data = HydroHeuristicData(
        data_aggregator_parameters=DataAggregatorParameters(
            hours_aggregated_time_steps=[
                24 * get_number_of_days_in_month(m) for m in range(12)
            ],
            timesteps=list(range(12)),
        ),
        reservoir_data=ReservoirParameters(capacity, initial_level, folder_name, 0),
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
    folder_name = (
        str(Path(__file__).parent) + "../../tests/functional/data/hydro_with_rulecurves"
    )
    initial_level = 0.445 * capacity

    data = HydroHeuristicData(
        data_aggregator_parameters=DataAggregatorParameters(
            hours_aggregated_time_steps=[
                24 * get_number_of_days_in_month(m) for m in range(12)
            ],
            timesteps=list(range(12)),
        ),
        reservoir_data=ReservoirParameters(capacity, initial_level, folder_name, 0),
    )

    data.compute_target(HydroHeuristicParameters())

    assert data.target[0] == pytest.approx(0.0495627 * capacity)


def test_data_aggregator() -> None:
    raw_data = [float(i) for i in range(10)]

    data_aggregator = DataAggregator(
        DataAggregatorParameters([2, 3, 4, 0, 1], [1, 3, 4])
    )
    aggregated_data = data_aggregator.aggregate_data("sum", raw_data)

    assert aggregated_data == [9, 0, 9]

    data_aggregator = DataAggregator(
        DataAggregatorParameters([2, 3, 4, 0, 1], list(range(5)))
    )
    aggregated_data = data_aggregator.aggregate_data("lag_first_element", raw_data)

    assert aggregated_data == [2, 5, 9, 9, 0]
