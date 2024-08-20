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

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np


@dataclass(frozen=False)
class ReservoirParameters:
    capacity: float
    initial_level: float
    folder_name: str
    scenario: int


@dataclass(frozen=True)
class HydroHeuristicParameters:
    inter_breakdown: int = 1
    total_target: Optional[float] = None


@dataclass(frozen=True)
class DataAggregatorParameters:
    hours_aggregated_time_steps: List[int]
    timesteps: List[int]


def get_number_of_days_in_month(month: int) -> int:
    number_day_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    return number_day_month


class RawHydroData:
    def __init__(self, folder_name: str, scenario: int) -> None:
        self.folder_name = folder_name
        self.scenario = scenario

        self.name_file = {
            "demand": "load",
            "inflow": "mod",
            "lower_rule_curve": "reservoir",
            "upper_rule_curve": "reservoir",
            "max_generating": "maxpower",
        }

        self.column = {
            "demand": self.scenario,
            "inflow": self.scenario,
            "lower_rule_curve": 0,
            "upper_rule_curve": 2,
            "max_generating": 0,
        }

    def read_data(self, name: str) -> List[float]:

        data = np.loadtxt(f"{self.folder_name}/{self.name_file[name]}.txt")
        if len(data.shape) >= 2:
            data = data[:, self.column[name]]
        hourly_data = self.convert_to_hourly_data(name, list(data))

        return hourly_data

    def convert_to_hourly_data(self, name: str, data: List[float]) -> List[float]:
        hours_input = 1 if name == "demand" else 24
        hourly_data = np.repeat(np.array(data), hours_input)
        if self.name_file[name] == "mod":
            hourly_data = hourly_data / hours_input
        return list(hourly_data)


class HydroHeuristicData:
    def __init__(
        self,
        data_aggregator_parameters: DataAggregatorParameters,
        reservoir_data: ReservoirParameters,
    ):
        self.reservoir_data = reservoir_data

        data_aggregator = DataAggregator(
            data_aggregator_parameters,
        )

        raw_data_reader = RawHydroData(
            reservoir_data.folder_name, reservoir_data.scenario
        )

        self.demand = data_aggregator.aggregate_data(
            operator="sum",
            data=raw_data_reader.read_data("demand"),
        )
        self.inflow = data_aggregator.aggregate_data(
            operator="sum",
            data=raw_data_reader.read_data("inflow"),
        )
        self.lower_rule_curve = data_aggregator.aggregate_data(
            operator="lag_first_element",
            data=raw_data_reader.read_data("lower_rule_curve"),
        )
        self.upper_rule_curve = data_aggregator.aggregate_data(
            operator="lag_first_element",
            data=raw_data_reader.read_data("upper_rule_curve"),
        )
        self.max_generating = data_aggregator.aggregate_data(
            operator="sum",
            data=raw_data_reader.read_data("max_generating"),
        )

    def compute_target(self, heuristic_parameters: HydroHeuristicParameters) -> None:
        if heuristic_parameters.total_target is None:
            total_target = sum(self.inflow)
        else:
            total_target = heuristic_parameters.total_target
        target = (
            total_target
            * np.power(self.demand, heuristic_parameters.inter_breakdown)
            / sum(np.power(self.demand, heuristic_parameters.inter_breakdown))
        )

        self.target = list(target)


@dataclass(frozen=True)
class DataAggregator:
    data_aggregator_parameters: DataAggregatorParameters

    def aggregate_data(self, operator: str, data: List[float]) -> List[float]:
        aggregated_data: List[float] = []
        hour = 0
        for time_step, hours_time_step in enumerate(
            self.data_aggregator_parameters.hours_aggregated_time_steps
        ):
            if time_step in self.data_aggregator_parameters.timesteps:
                if operator == "sum":
                    aggregated_data.append(np.sum(data[hour : hour + hours_time_step]))
                elif operator == "lag_first_element":
                    aggregated_data.append(data[(hour + hours_time_step) % len(data)])
            hour += hours_time_step
        return aggregated_data


def update_generation_target(
    all_daily_generation: List[float], daily_generation: List[float]
) -> List[float]:
    all_daily_generation = all_daily_generation + daily_generation
    return all_daily_generation


def calculate_weekly_target(all_daily_generation: List[float]) -> List[float]:
    weekly_target = [
        sum([all_daily_generation[day] for day in range(7 * week, 7 * (week + 1))])
        for week in range(len(all_daily_generation) // 7)
    ]

    return weekly_target
