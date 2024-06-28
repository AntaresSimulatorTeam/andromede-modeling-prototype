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

from andromede.hydro_heuristic.data import (
    calculate_weekly_target,
    get_number_of_days_in_month,
    HydroHeuristicData,
)
from andromede.hydro_heuristic.problem import create_hydro_problem, solve_hydro_problem


def test_hydro_heuristic() -> None:
    """ """
    scenarios = 1
    interdaily_breakdown = 3

    capacity = 1711510

    for scenario in range(scenarios):
        initial_level = 0.5 * capacity

        # Répartition des apports mensuels
        monthly_data = HydroHeuristicData(
            scenario,
            "monthly",
            folder_name="hydro_without_rulecurves",
            timesteps=list(range(12)),
            capacity=capacity,
            initial_level=initial_level,
        )
        monthly_data.compute_target(sum(monthly_data.inflow))

        # Ajustement de la réapartition mensuelle
        problem = create_hydro_problem(
            horizon="monthly",
            hydro_data=monthly_data,
        )

        status, monthly_generation, _ = solve_hydro_problem(problem)

        assert status == problem.solver.OPTIMAL

        all_daily_generation: List[float] = []
        day_in_year = 0

        for month in range(12):

            number_day_month = get_number_of_days_in_month(month)
            daily_data = HydroHeuristicData(
                scenario,
                "daily",
                folder_name="hydro_without_rulecurves",
                timesteps=list(range(day_in_year, day_in_year + number_day_month)),
                capacity=capacity,
                initial_level=initial_level,
            )
            # Répartition des crédits de turbinage jour par jour

            daily_data.compute_target(
                total_target=monthly_generation[month],
                inter_breakdown=interdaily_breakdown,
            )
            # Ajustement de la répartition jour par jour
            problem = create_hydro_problem(
                horizon="daily",
                hydro_data=daily_data,
            )

            status, daily_generation, initial_level = solve_hydro_problem(problem)

            assert status == problem.solver.OPTIMAL

            all_daily_generation = all_daily_generation + daily_generation
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
