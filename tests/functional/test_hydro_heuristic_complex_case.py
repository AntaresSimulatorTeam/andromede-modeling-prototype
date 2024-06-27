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
    get_all_data,
    get_number_of_days_in_month,
    get_target,
    calculate_weekly_target,
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
        (
            monthly_demand,
            monthly_inflow,
            monthly_max_generating,
            monthly_lowerrulecurve,
            monthly_upperrulecurve,
        ) = get_all_data(scenario, "monthly", folder_name="data_complex_case")
        monthly_target = get_target(monthly_demand, sum(monthly_inflow))

        # Ajustement de la réapartition mensuelle
        problem = create_hydro_problem(
            horizon="monthly",
            target=monthly_target,
            inflow=monthly_inflow,
            max_generating=monthly_max_generating,
            lower_rule_curve=monthly_lowerrulecurve,
            upper_rule_curve=monthly_upperrulecurve,
            initial_level=initial_level,
            capacity=capacity,
        )

        status, monthly_generation, _ = solve_hydro_problem(problem)

        assert status == problem.solver.OPTIMAL

        all_daily_generation: List[float] = []
        day_in_year = 0
        (
            daily_demand,
            daily_inflow,
            daily_max_generating,
            daily_lowerrulecurve,
            daily_upperrulecurve,
        ) = get_all_data(scenario, "daily", folder_name="data_complex_case")

        for month in range(12):
            number_day_month = get_number_of_days_in_month(month)
            # Répartition des crédits de turbinage jour par jour

            daily_target = get_target(
                demand=daily_demand[day_in_year : day_in_year + number_day_month],
                total_target=monthly_generation[month],
                inter_breakdown=interdaily_breakdown,
            )
            # Ajustement de la répartition jour par jour
            problem = create_hydro_problem(
                horizon="daily",
                target=daily_target,
                inflow=daily_inflow[day_in_year : day_in_year + number_day_month],
                max_generating=daily_max_generating[
                    day_in_year : day_in_year + number_day_month
                ],
                lower_rule_curve=daily_lowerrulecurve,
                upper_rule_curve=daily_upperrulecurve,
                initial_level=initial_level,
                capacity=capacity,
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
            "tests/functional/data_complex_case/hydro/values-weekly.txt",
            "r",
        )
        expected_output = expected_output_file.readlines()
        for week in range(52):
            assert float(expected_output[week + 7].strip().split("\t")[9]) == round(
                weekly_target[week]
            )
