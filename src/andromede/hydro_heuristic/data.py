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
from typing import List, Optional

import numpy as np
import pandas as pd

from andromede.study import (
    ConstantData,
    DataBase,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
)


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


@dataclass(frozen=True)
class RawDataProperties:
    name_file: str
    column: int
    hours_input: int


def get_number_of_days_in_month(month: int) -> int:
    number_day_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    return number_day_month


class RawHydroData:
    def __init__(self, folder_name: str, scenario: int) -> None:
        self.folder_name = folder_name
        self.scenario = scenario

        self.properties = {
            "demand": RawDataProperties("load", self.scenario, 1),
            "inflow": RawDataProperties("mod", self.scenario, 24),
            "lower_rule_curve": RawDataProperties("reservoir", 0, 24),
            "upper_rule_curve": RawDataProperties("reservoir", 2, 24),
            "max_generating": RawDataProperties("maxpower", 0, 24),
        }

    def read_data(self, name: str) -> List[float]:
        properties = self.properties[name]
        data = np.loadtxt(f"{self.folder_name}/{properties.name_file}.txt")
        if len(data.shape) >= 2:
            data = data[:, properties.column]
        hourly_data = self.convert_to_hourly_data(properties, list(data))

        return hourly_data

    def convert_to_hourly_data(
        self, properties: RawDataProperties, data: List[float]
    ) -> List[float]:
        hourly_data = np.repeat(np.array(data), properties.hours_input)
        if properties.name_file == "mod":
            hourly_data = hourly_data / properties.hours_input
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


def save_generation_target(
    all_daily_generation: List[float], daily_generation: List[float]
) -> List[float]:
    all_daily_generation = all_daily_generation + daily_generation
    return all_daily_generation


def compute_weekly_target(all_daily_generation: List[float]) -> List[float]:
    weekly_target = [
        sum([all_daily_generation[day] for day in range(7 * week, 7 * (week + 1))])
        for week in range(len(all_daily_generation) // 7)
    ]

    return weekly_target


def get_database(hydro_data: HydroHeuristicData, id: str = "H") -> DataBase:
    database = DataBase()

    database.add_data(id, "capacity", ConstantData(hydro_data.reservoir_data.capacity))
    database.add_data(
        id,
        "initial_level",
        ConstantData(hydro_data.reservoir_data.initial_level),
    )

    inflow_data = pd.DataFrame(
        hydro_data.inflow,
        index=[i for i in range(len(hydro_data.inflow))],
        columns=[0],
    )
    database.add_data(id, "inflow", TimeScenarioSeriesData(inflow_data))

    target_data = pd.DataFrame(
        hydro_data.target,
        index=[i for i in range(len(hydro_data.target))],
        columns=[0],
    )
    database.add_data(id, "generating_target", TimeScenarioSeriesData(target_data))
    database.add_data(id, "overall_target", ConstantData(sum(hydro_data.target)))

    database.add_data(
        id,
        "lower_rule_curve",
        TimeSeriesData(
            {
                TimeIndex(i): hydro_data.lower_rule_curve[i]
                * hydro_data.reservoir_data.capacity
                for i in range(len(hydro_data.lower_rule_curve))
            }
        ),
    )
    database.add_data(
        id,
        "upper_rule_curve",
        TimeSeriesData(
            {
                TimeIndex(i): hydro_data.upper_rule_curve[i]
                * hydro_data.reservoir_data.capacity
                for i in range(len(hydro_data.lower_rule_curve))
            }
        ),
    )
    database.add_data(id, "min_generating", ConstantData(0))

    database.add_data(
        id,
        "max_generating",
        TimeSeriesData(
            {
                TimeIndex(i): hydro_data.max_generating[i]
                for i in range(len(hydro_data.max_generating))
            }
        ),
    )

    database.add_data(
        id,
        "max_epsilon",
        TimeSeriesData(
            {
                TimeIndex(i): (hydro_data.reservoir_data.capacity if i == 0 else 0)
                for i in range(len(hydro_data.max_generating))
            }
        ),
    )

    return database
