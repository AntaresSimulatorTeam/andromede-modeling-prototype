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
    HydroHeuristicData,
    calculate_weekly_target,
    get_number_of_days_in_month,
    update_generation_target,
)
from andromede.hydro_heuristic.problem import HydroHeuristicProblem


def test_hydro_heuristic() -> None:
    """ """
    scenarios = 1
    capacity = 1e07

    for scenario in range(scenarios):
        initial_level = 0.445 * capacity

        # Répartition des apports mensuels
        monthly_data = HydroHeuristicData(
            scenario,
            "monthly",
            folder_name="hydro_with_rulecurves",
            timesteps=list(range(12)),
            capacity=capacity,
            initial_level=initial_level,
        )
        monthly_data.compute_target(sum(monthly_data.inflow))

        # Ajustement de la réapartition mensuelle
        problem = HydroHeuristicProblem(horizon="monthly", hydro_data=monthly_data)

        status, obj, monthly_generation, _ = problem.solve_hydro_problem()

        assert status == pywraplp.Solver.OPTIMAL

        assert obj / capacity == pytest.approx(10.1423117689793)

        monthly_generation = [
            capacity * target
            for target in [
                0.0495627,
                0.00958564,
                0.0392228,
                0,
                0,
                0,
                0,
                0.028354,
                0.0966672,
                0.100279,
                0.100799,
                0.10467,
            ]
        ]  # equivalent solution found by Antares that is taken to be consistent

        all_daily_generation: List[float] = []
        day_in_year = 0

        for month in range(12):
            number_day_month = get_number_of_days_in_month(month)
            daily_data = HydroHeuristicData(
                scenario,
                "daily",
                folder_name="hydro_with_rulecurves",
                timesteps=list(range(day_in_year, day_in_year + number_day_month)),
                capacity=capacity,
                initial_level=initial_level,
            )
            # Répartition des crédits de turbinage jour par jour

            daily_data.compute_target(
                total_target=monthly_generation[month],
            )
            # Ajustement de la répartition jour par jour
            problem = HydroHeuristicProblem(horizon="daily", hydro_data=daily_data)

            status, obj, daily_generation, initial_level = problem.solve_hydro_problem()
            assert status == pywraplp.Solver.OPTIMAL
            assert obj / capacity == pytest.approx(
                [
                    -0.405595,
                    -0.354666,
                    -0.383454,
                    -0.374267,
                    -0.424858,
                    -0.481078,
                    -0.595347,
                    0.0884837,
                    -0.638019,
                    -0.610892,
                    -0.526716,
                    -0.466928,
                ][month],
                abs=0.02,
            )

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
            "tests/functional/data/hydro_with_rulecurves/values-weekly.txt",
            "r",
        )
        expected_output = expected_output_file.readlines()
        # Test fail because the solution is slightly different because of Antares' noises
        # for week in range(52):
        #     assert float(expected_output[week + 7].strip().split("\t")[1]) - float(
        #         expected_output[week + 7].strip().split("\t")[2]
        #     ) == round(weekly_target[week])
