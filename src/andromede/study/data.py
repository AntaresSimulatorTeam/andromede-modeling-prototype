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
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Type, TypeVar

import pandas as pd

from andromede.study.network import Network

T = TypeVar("T", bound="AbstractDataStructure")


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
    @abstractmethod
    def get_value(self, timestep: int, scenario: int, node_id: str = "") -> float:
        """
        Get the data value for a given timestep and scenario at a given node
        Implement this method in subclasses as needed.
        """
        pass

    @abstractmethod
    def check_requirement(self, time: bool, scenario: bool) -> bool:
        """
        Check if the data structure meets certain requirements.
        Implement this method in subclasses as needed.
        """
        pass

    @classmethod
    @abstractmethod
    def from_dataframe(cls: Type[T], df: pd.DataFrame) -> T:
        """
        Constructor of DataStructure from a pandas DataFrame.
        Implement this method in subclasses as needed.
        """
        pass


@dataclass(frozen=True)
class ConstantData(AbstractDataStructure):
    value: float

    def get_value(self, timestep: int, scenario: int, node_id: str = "") -> float:
        return self.value

    # ConstantData can be used for time varying or constant models
    def check_requirement(self, time: bool, scenario: bool) -> bool:
        if not isinstance(self, ConstantData):
            raise ValueError("Invalid data type for ConstantData")
        return True

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "ConstantData":
        return cls(df.iat[0, 0])


@dataclass(frozen=True)
class TimeSeriesData(AbstractDataStructure):
    """
    Container for identifiable timeseries data.
    When a model is instantiated as a component, property values
    can be defined by referencing one of those timeseries by its ID.
    """

    time_series: Mapping[TimeIndex, float]

    def get_value(self, timestep: int, scenario: int, node_id: str = "") -> float:
        return self.time_series[TimeIndex(timestep)]

    def check_requirement(self, time: bool, scenario: bool) -> bool:
        if not isinstance(self, TimeSeriesData):
            raise ValueError("Invalid data type for TimeSeriesData")

        return time

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "TimeSeriesData":
        return cls(
            {TimeIndex(time): v[1] for time, v in enumerate(df.iloc[:, 0].items())}
        )


@dataclass(frozen=True)
class ScenarioSeriesData(AbstractDataStructure):
    """
    Container for identifiable timeseries data.
    When a model is instantiated as a component, property values
    can be defined by referencing one of those timeseries by its ID.
    """

    scenario_series: Mapping[ScenarioIndex, float]

    def get_value(self, timestep: int, scenario: int, node_id: str = "") -> float:
        return self.scenario_series[ScenarioIndex(scenario)]

    def check_requirement(self, time: bool, scenario: bool) -> bool:
        if not isinstance(self, ScenarioSeriesData):
            raise ValueError("Invalid data type for TimeSeriesData")

        return scenario

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "ScenarioSeriesData":
        return cls(
            {
                ScenarioIndex(scenario): v[1]
                for scenario, v in enumerate(df.iloc[0, :].items())
            }
        )


@dataclass(frozen=True)
class TimeScenarioSeriesData(AbstractDataStructure):
    """
    Container for identifiable timeseries data.
    When a model is instantiated as a component, property values
    can be defined by referencing one of those timeseries by its ID.
    """

    time_scenario_series: pd.DataFrame

    def get_value(self, timestep: int, scenario: int, node_id: str = "") -> float:
        value = str(self.time_scenario_series.iloc[timestep, scenario])
        return float(value)

    def check_requirement(self, time: bool, scenario: bool) -> bool:
        if not isinstance(self, TimeScenarioSeriesData):
            raise ValueError("Invalid data type for TimeScenarioSeriesData")

        return time and scenario

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "TimeScenarioSeriesData":
        return cls(df)


@dataclass(frozen=True)
class TreeData(AbstractDataStructure):
    data: Mapping[str, AbstractDataStructure]

    def get_value(self, timestep: int, scenario: int, node_id: str = "") -> float:
        return self.data[node_id].get_value(timestep, scenario)

    def check_requirement(self, time: bool, scenario: bool) -> bool:
        return all(
            node_data.check_requirement(time, scenario)
            for node_data in self.data.values()
        )

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "TreeData":
        # TODO if needed
        return cls({})


@dataclass(frozen=True)
class DatabaseIndex:
    component_id: str
    parameter_name: str


class DataBase:
    """
    Container for identifiable data.
    When a model is instantiated as a component, property values
    can be defined by referencing one of those data by its ID.
    Data can have different structure : constant, varying in time or scenarios.
    """

    _data: Dict[DatabaseIndex, AbstractDataStructure]

    def __init__(self) -> None:
        self._data: Dict[DatabaseIndex, AbstractDataStructure] = {}

    def get_data(self, component_id: str, parameter_name: str) -> AbstractDataStructure:
        return self._data[DatabaseIndex(component_id, parameter_name)]

    def add_data(
        self, component_id: str, parameter_name: str, data: AbstractDataStructure
    ) -> None:
        self._data[DatabaseIndex(component_id, parameter_name)] = data

    def get_value(self, index: DatabaseIndex, timestep: int, scenario: int) -> float:
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
