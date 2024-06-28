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

import numpy as np


def get_number_of_days_in_month(month: int) -> int:
    number_day_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    return number_day_month


def get_all_data(
    scenario: int, horizon: str, folder_name: str
) -> tuple[List[float], List[float], List[float], List[float], List[float]]:
    if horizon == "monthly":
        hours_aggregated_time_steps = [
            24 * get_number_of_days_in_month(m) for m in range(12)
        ]
    elif horizon == "daily":
        hours_aggregated_time_steps = [24 for d in range(365)]

    demand = get_input_data(
        name_file="load",
        column=scenario,
        hours_aggregated_time_steps=hours_aggregated_time_steps,
        hours_input=1,
        operator="sum",
        folder_name=folder_name,
    )
    inflow = get_input_data(
        name_file="mod",
        column=scenario,
        hours_aggregated_time_steps=hours_aggregated_time_steps,
        hours_input=24,
        operator="sum",
        folder_name=folder_name,
    )
    lowerrulecruve = get_input_data(
        name_file="reservoir",
        column=0,
        hours_aggregated_time_steps=hours_aggregated_time_steps,
        hours_input=24,
        operator="lag_first_element",
        folder_name=folder_name,
    )
    upperrulecruve = get_input_data(
        name_file="reservoir",
        column=2,
        hours_aggregated_time_steps=hours_aggregated_time_steps,
        hours_input=24,
        operator="lag_first_element",
        folder_name=folder_name,
    )
    max_generating = get_input_data(
        name_file="maxpower",
        column=0,
        hours_aggregated_time_steps=hours_aggregated_time_steps,
        hours_input=24,
        operator="sum",
        folder_name=folder_name,
    )
    max_generating = [x * 24 for x in max_generating]

    return (
        demand,
        inflow,
        max_generating,
        lowerrulecruve,
        upperrulecruve,
    )


def get_input_data(
    name_file: str,
    column: int,
    hours_aggregated_time_steps: List[int],
    hours_input: int,
    operator: str,
    folder_name: str,
) -> List[float]:
    data = np.loadtxt("tests/functional/data/" + folder_name + "/" + name_file + ".txt")
    data = data[:, column]
    aggregated_data: List[float] = []
    hour = 0
    for hours_time_step in hours_aggregated_time_steps:
        assert hours_time_step % hours_input == 0
        if operator == "sum":
            aggregated_data.append(
                np.sum(data[hour : hour + hours_time_step // hours_input])
            )
        elif operator == "lag_first_element":
            aggregated_data.append(
                data[(hour + hours_time_step // hours_input) % len(data)]
            )
        hour += hours_time_step // hours_input
    return aggregated_data


def calculate_weekly_target(all_daily_generation: list[float]) -> list[float]:
    weekly_target = np.zeros(52)
    week = 0
    day_in_week = 0
    day_in_year = 0

    while week < 52:
        weekly_target[week] += all_daily_generation[day_in_year]
        day_in_year += 1
        day_in_week += 1
        if day_in_week >= 7:
            week += 1
            day_in_week = 0

    return list(weekly_target)


def get_target(
    demand: List[float], total_target: float, inter_breakdown: int = 1
) -> List[float]:
    target = (
        total_target
        * np.power(demand, inter_breakdown)
        / sum(np.power(demand, inter_breakdown))
    )

    return list(target)
