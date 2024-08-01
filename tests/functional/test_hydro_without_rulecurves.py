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

from andromede.hydro_heuristic.data import (
    calculate_weekly_target,
    get_number_of_days_in_month,
    update_generation_target,
)
from andromede.hydro_heuristic.problem import optimize_target
from andromede.hydro_heuristic.heuristic_model import HeuristicHydroModelBuilder
from tests.functional.libs.lib_hydro_heuristic import HYDRO_MODEL


def test_hydro_heuristic() -> None:
    """ """
    scenarios = 1
    intermonthly_breakdown = 1
    interdaily_breakdown = 3
    folder_name = "hydro_without_rulecurves"

    capacity = 1711510

    for scenario in range(scenarios):
        initial_level = 0.5 * capacity

        initial_level, status, _, monthly_generation = optimize_target(
            intermonthly_breakdown,
            folder_name,
            capacity,
            scenario,
            initial_level,
            hours_aggregated_time_steps=[
                24 * get_number_of_days_in_month(m) for m in range(12)
            ],
            timesteps=list(range(12)),
            total_target=None,
            heuristic_model=HeuristicHydroModelBuilder(
                HYDRO_MODEL, "monthly"
            ).get_model(),
        )

        assert status == pywraplp.Solver.OPTIMAL

        all_daily_generation: List[float] = []
        day_in_year = 0

        for month in range(12):
            number_day_month = get_number_of_days_in_month(month)

            (
                initial_level,
                status,
                obj,
                daily_generation,
            ) = optimize_target(
                interdaily_breakdown,
                folder_name,
                capacity,
                scenario,
                initial_level,
                hours_aggregated_time_steps=[24 for d in range(365)],
                timesteps=list(range(day_in_year, day_in_year + number_day_month)),
                total_target=monthly_generation[month],
                heuristic_model=HeuristicHydroModelBuilder(
                    HYDRO_MODEL, "daily"
                ).get_model(),
            )

            assert status == pywraplp.Solver.OPTIMAL

            all_daily_generation = update_generation_target(
                all_daily_generation, daily_generation
            )
            day_in_year += number_day_month

        # Calcul des cibles hebdomadaires
        weekly_target = calculate_weekly_target(
            all_daily_generation,
        )

        # Vérification des valeurs trouvées
        expected_output_file = open(
            "tests/functional/data/hydro_without_rulecurves/values-weekly.txt",
            "r",
        )
        expected_output = expected_output_file.readlines()
        for week in range(52):
            assert float(expected_output[week + 7].strip().split("\t")[9]) == round(
                weekly_target[week]
            )
