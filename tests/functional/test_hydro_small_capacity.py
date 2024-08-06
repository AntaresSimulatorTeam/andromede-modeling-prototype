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

from typing import List

import ortools.linear_solver.pywraplp as pywraplp
import pytest

from andromede.hydro_heuristic.data import (
    calculate_weekly_target,
    get_number_of_days_in_month,
    update_generation_target,
)
from andromede.hydro_heuristic.heuristic_model import HeuristicHydroModelBuilder
from andromede.hydro_heuristic.problem import (
    DataAggregatorParameters,
    HydroHeuristicParameters,
    ReservoirParameters,
    optimize_target,
)
from tests.functional.libs.lib_hydro_heuristic import HYDRO_MODEL


def test_hydro_heuristic() -> None:
    """ """
    capacity = 2945
    reservoir_data = ReservoirParameters(
        capacity,
        initial_level=0.5 * capacity,
        folder_name="hydro_small_capacity",
        scenario=0,
    )

    solving_output, monthly_output = optimize_target(
        heuristic_parameters=HydroHeuristicParameters(1),
        data_aggregator_parameters=DataAggregatorParameters(
            [24 * get_number_of_days_in_month(m) for m in range(12)],
            list(range(12)),
        ),
        reservoir_data=reservoir_data,
        heuristic_model=HeuristicHydroModelBuilder(HYDRO_MODEL, "monthly").get_model(),
    )

    assert solving_output.status == pywraplp.Solver.OPTIMAL

    all_daily_generation: List[float] = []
    day_in_year = 0

    for month in range(12):
        number_day_month = get_number_of_days_in_month(month)

        solving_output, daily_output = optimize_target(
            heuristic_parameters=HydroHeuristicParameters(
                3, monthly_output.generating[month]
            ),
            data_aggregator_parameters=DataAggregatorParameters(
                [24 for d in range(365)],
                list(range(day_in_year, day_in_year + number_day_month)),
            ),
            reservoir_data=reservoir_data,
            heuristic_model=HeuristicHydroModelBuilder(
                HYDRO_MODEL, "daily"
            ).get_model(),
        )
        reservoir_data.initial_level = daily_output.level

        assert solving_output.status == pywraplp.Solver.OPTIMAL

        all_daily_generation = update_generation_target(
            all_daily_generation, daily_output.generating
        )
        day_in_year += number_day_month

    # Calcul des cibles hebdomadaires
    weekly_target = calculate_weekly_target(
        all_daily_generation,
    )

    # Vérification des valeurs trouvées
    expected_output_file = open(
        "tests/functional/data/hydro_small_capacity/values-weekly.txt",
        "r",
    )
    expected_output = expected_output_file.readlines()
    for week in range(52):
        assert float(expected_output[week + 7].strip().split("\t")[42]) - 0.75 * float(
            expected_output[week + 7].strip().split("\t")[43]
        ) == pytest.approx(weekly_target[week], abs=1)
