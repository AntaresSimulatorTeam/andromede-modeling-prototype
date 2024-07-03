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
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from andromede.study.network import Network


@dataclass(frozen=True)
class TimeScenarioIndex:
    time: int
    scenario: int


@dataclass(frozen=True)
class TimeIndex:
    time: int


@dataclass(frozen=True)
class ScenarioIndex:
    scenario: int


@dataclass(frozen=True)
class AbstractDataStructure(ABC):
    def get_value(self, timestep: int, scenario: int) -> float:
        return NotImplemented

    @abstractmethod
    def check_requirement(self, time: bool, scenario: bool) -> bool:
        """
        Check if the data structure meets certain requirements.
        Implement this method in subclasses as needed.
        """
        pass


@dataclass(frozen=True)
class ConstantData(AbstractDataStructure):
    value: float

    def get_value(self, timestep: int, scenario: int) -> float:
        return self.value

    # ConstantData can be used for time varying or constant models
    def check_requirement(self, time: bool, scenario: bool) -> bool:
        if not isinstance(self, ConstantData):
            raise ValueError("Invalid data type for ConstantData")
        return True


@dataclass(frozen=True)
class TimeSeriesData(AbstractDataStructure):
    """
    Container for identifiable timeseries data.
    When a model is instantiated as a component, property values
    can be defined by referencing one of those timeseries by its ID.
    """

    time_series: Dict[TimeIndex, float]

    def get_value(self, timestep: int, scenario: int) -> float:
        return self.time_series[TimeIndex(timestep)]

    def check_requirement(self, time: bool, scenario: bool) -> bool:
        if not isinstance(self, TimeSeriesData):
            raise ValueError("Invalid data type for TimeSeriesData")

        return time


@dataclass(frozen=True)
class ScenarioSeriesData(AbstractDataStructure):
    """
    Container for identifiable timeseries data.
    When a model is instantiated as a component, property values
    can be defined by referencing one of those timeseries by its ID.
    """

    scenario_series: Dict[ScenarioIndex, float]

    def get_value(self, timestep: int, scenario: int) -> float:
        return self.scenario_series[ScenarioIndex(scenario)]

    def check_requirement(self, time: bool, scenario: bool) -> bool:
        if not isinstance(self, ScenarioSeriesData):
            raise ValueError("Invalid data type for TimeSeriesData")

        return scenario


def load_ts_from_txt(
    timeseries_name: Optional[str], path_to_file: Optional[Path]
) -> pd.DataFrame:
    if path_to_file is not None and timeseries_name is not None:
        timeseries_with_extension = timeseries_name + ".txt"
        ts_path = path_to_file / timeseries_with_extension
    try:
        return pd.read_csv(ts_path, header=None, sep="\s+")
    except Exception:
        raise Exception(f"An error has arrived when processing '{ts_path}'")


def filter_ts_on_scenarios_and_timesteps(
    raw_ts: pd.DataFrame,
    scenarios: Optional[List[int]],
    timesteps: Optional[List[int]],
) -> pd.DataFrame:
    filtered_ts = raw_ts
    if scenarios is not None:
        filtered_ts = filtered_ts.filter(items=scenarios, axis=1)
    if timesteps is not None:
        filtered_ts = filtered_ts.filter(items=timesteps, axis=0)
    return filtered_ts.reset_index(drop=True)


@dataclass(frozen=True)
class TimeScenarioSeriesData(AbstractDataStructure):
    """
    Container for identifiable timeseries data.
    When a model is instantiated as a component, property values
    can be defined by referencing one of those timeseries by its ID.
    """

    time_scenario_series: pd.DataFrame

    def get_value(self, timestep: int, scenario: int) -> float:
        if self.time_scenario_series.shape[1] == 1:
            value = str(self.time_scenario_series.loc[[timestep]].iloc[0, 0])
            return float(value)
        value = str(self.time_scenario_series.loc[timestep, scenario])
        return float(value)

    def check_requirement(self, time: bool, scenario: bool) -> bool:
        if not isinstance(self, TimeScenarioSeriesData):
            raise ValueError("Invalid data type for TimeScenarioSeriesData")

        return time and scenario


@dataclass(frozen=True)
class ComponentParameterIndex:
    component_id: str
    parameter_name: str


class DataBase:
    """
    Container for identifiable data.
    When a model is instantiated as a component, property values
    can be defined by referencing one of those data by its ID.
    Data can have different structure : constant, varying in time or scenarios.
    """

    _data: Dict[ComponentParameterIndex, AbstractDataStructure]

    def __init__(self) -> None:
        self._data: Dict[ComponentParameterIndex, AbstractDataStructure] = {}

    def get_data(self, component_id: str, parameter_name: str) -> AbstractDataStructure:
        return self._data[ComponentParameterIndex(component_id, parameter_name)]

    def add_data(
        self, component_id: str, parameter_name: str, data: AbstractDataStructure
    ) -> None:
        self._data[ComponentParameterIndex(component_id, parameter_name)] = data

    def get_value(
        self, index: ComponentParameterIndex, timestep: int, scenario: int
    ) -> float:
        if index in self._data:
            return self._data[index].get_value(timestep, scenario)
        else:
            raise KeyError(f"Index {index} not found.")

    def requirements_consistency(self, network: Network) -> None:
        for component in network.components:
            for param in component.model.parameters.values():
                data_structure = self.get_data(component.id, param.name)

                if not data_structure.check_requirement(
                    component.model.parameters[param.name].structure.time,
                    component.model.parameters[param.name].structure.scenario,
                ):
                    raise ValueError(
                        f"Data inconsistency for component: {component.id}, parameter: {param.name}. Requirement not met."
                    )
