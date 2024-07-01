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

from typing import List, Optional

import numpy as np


def get_number_of_days_in_month(month: int) -> int:
    number_day_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    return number_day_month


class HydroHeuristicData:
    def __init__(
        self,
        scenario: int,
        horizon: str,
        folder_name: str,
        timesteps: List[int],
        capacity: float,
        initial_level: float,
    ):
        self.folder_name = folder_name
        if horizon == "monthly":
            hours_aggregated_time_steps = [
                24 * get_number_of_days_in_month(m) for m in range(12)
            ]
        elif horizon == "daily":
            hours_aggregated_time_steps = [24 for d in range(365)]
        self.hours_aggregated_time_steps = hours_aggregated_time_steps
        self.timesteps = timesteps
        self.capacity = capacity
        self.initial_level = initial_level

        self.demand = self.get_input_data(
            name_file="load",
            column=scenario,
            hours_input=1,
            operator="sum",
        )
        self.inflow = self.get_input_data(
            name_file="mod",
            column=scenario,
            hours_input=24,
            operator="sum",
        )
        self.lower_rule_curve = self.get_input_data(
            name_file="reservoir",
            column=0,
            hours_input=24,
            operator="lag_first_element",
        )
        self.upper_rule_curve = self.get_input_data(
            name_file="reservoir",
            column=2,
            hours_input=24,
            operator="lag_first_element",
        )
        max_generating = self.get_input_data(
            name_file="maxpower",
            column=0,
            hours_input=24,
            operator="sum",
        )
        self.max_generating = [x * 24 for x in max_generating]

    def get_input_data(
        self,
        name_file: str,
        column: int,
        hours_input: int,
        operator: str,
    ) -> List[float]:
        data = np.loadtxt(
            "tests/functional/data/" + self.folder_name + "/" + name_file + ".txt"
        )
        data = data[:, column]
        aggregated_data: List[float] = []
        hour = 0
        for time_step, hours_time_step in enumerate(self.hours_aggregated_time_steps):
            assert hours_time_step % hours_input == 0
            if time_step in self.timesteps:
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

    def compute_target(
        self, total_target: Optional[float], inter_breakdown: int = 1
    ) -> None:
        if total_target is None:
            total_target = sum(self.inflow)
        target = (
            total_target
            * np.power(self.demand, inter_breakdown)
            / sum(np.power(self.demand, inter_breakdown))
        )

        self.target = list(target)


def update_generation_target(
    all_daily_generation: list[float], daily_generation: list[float]
) -> list[float]:
    all_daily_generation = all_daily_generation + daily_generation
    return all_daily_generation


def calculate_weekly_target(all_daily_generation: list[float]) -> list[float]:
    weekly_target = [
        sum([all_daily_generation[day] for day in range(7 * week, 7 * (week + 1))])
        for week in range(len(all_daily_generation) // 7)
    ]

    return weekly_target
