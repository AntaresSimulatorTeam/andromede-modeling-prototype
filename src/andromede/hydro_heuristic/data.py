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
from typing import List, Optional

import numpy as np


def get_number_of_days_in_month(month: int) -> int:
    number_day_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    return number_day_month


class RawHydroData:

    def __init__(self, name: str, folder_name: str, scenario: int) -> None:

        name_file = {
            "demand": "load",
            "inflow": "mod",
            "lower_rule_curve": "reservoir",
            "upper_rule_curve": "reservoir",
            "max_generating": "maxpower",
        }[name]

        column = {
            "demand": scenario,
            "inflow": scenario,
            "lower_rule_curve": 0,
            "upper_rule_curve": 2,
            "max_generating": 0,
        }[name]

        hours_input = 1 if name == "demand" else 24

        data = np.loadtxt(
            Path(__file__).parent
            / (
                "../../../tests/functional/data/"
                + folder_name
                + "/"
                + name_file
                + ".txt"
            )
        )
        data = data[:, column]
        data = np.repeat(data, hours_input)
        if name_file == "mod":
            data = data / hours_input

        self.time_series = data


class HydroHeuristicData:
    def __init__(
        self,
        scenario: int,
        hours_aggregated_time_steps: List[int],
        folder_name: str,
        timesteps: List[int],
        capacity: float,
        initial_level: float,
    ):
        self.folder_name = folder_name

        self.capacity = capacity
        self.initial_level = initial_level

        data_aggregator = DataAggregator(hours_aggregated_time_steps, timesteps)

        self.demand = data_aggregator.aggregate_data(
            operator="sum",
            raw_data=RawHydroData("demand", folder_name, scenario),
        )
        self.inflow = data_aggregator.aggregate_data(
            operator="sum",
            raw_data=RawHydroData("inflow", folder_name, scenario),
        )
        self.lower_rule_curve = data_aggregator.aggregate_data(
            operator="lag_first_element",
            raw_data=RawHydroData("lower_rule_curve", folder_name, scenario),
        )
        self.upper_rule_curve = data_aggregator.aggregate_data(
            operator="lag_first_element",
            raw_data=RawHydroData("upper_rule_curve", folder_name, scenario),
        )
        self.max_generating = data_aggregator.aggregate_data(
            operator="sum",
            raw_data=RawHydroData("max_generating", folder_name, scenario),
        )

    def compute_target(  # TODO : rajouter un test avec vraiment très peu de données
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


class DataAggregator:

    def __init__(
        self,
        hours_aggregated_time_steps: List[int],
        timesteps: List[int],
    ) -> None:
        self.hours_aggregated_time_steps = hours_aggregated_time_steps
        self.timesteps = timesteps

    def aggregate_data(self, operator: str, raw_data: RawHydroData) -> List[float]:
        data = raw_data.time_series
        aggregated_data: List[float] = []
        hour = 0
        for time_step, hours_time_step in enumerate(self.hours_aggregated_time_steps):
            if time_step in self.timesteps:
                if operator == "sum":
                    aggregated_data.append(np.sum(data[hour : hour + hours_time_step]))
                elif operator == "lag_first_element":
                    aggregated_data.append(data[(hour + hours_time_step) % len(data)])
            hour += hours_time_step
        return aggregated_data


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
