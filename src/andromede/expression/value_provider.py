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
from typing import Dict, List


@dataclass
class TimeScenarioIndices:
    time_indices: List[int]
    scenario_indices: List[int]


# TODO: Already define in study module, factorize this
@dataclass(frozen=True)
class TimeScenarioIndex:
    time: int
    scenario: int


# Given a list of time_indices and of scenario_indices, the value provider will get the parameter value for all couple (time, scenario) for time in time_indices and scenario in scenario_indices
class ValueProvider(ABC):
    """
    Implementations are in charge of mapping parameters and variables to their values.
    Depending on the implementation, evaluation may require a component id or not.
    """

    # TODO: To be removed, or should we keep it to evaluate solutions ?
    @abstractmethod
    def get_variable_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        ...

    # Need to have time_scenarios_indices as function argument as we do not want to create a Provider each time we have to get the value of a parameter at a different (time, scenario) index
    @abstractmethod
    def get_parameter_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        ...

    # TODO: To be removed ?
    @abstractmethod
    def get_component_variable_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        ...

    @abstractmethod
    def get_component_parameter_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        ...

    # TODO: Should this really be an abstract method ? Or maybe, only the Provider in _make_value_provider should implement it. And the context attribute in the InstancesIndexVisitor is a ValueProvider that implements the parameter_is_constant_over_time method. Maybe create a child class of ValueProvider like TimeValueProvider ?
    @abstractmethod
    def parameter_is_constant_over_time(self, name: str) -> bool:
        ...

    # There is probably a better place to put this..
    # Which is useful when evaluating the TimeSum operator over the whole block, to know which time steps to look for to get the parameter values
    @staticmethod
    @abstractmethod
    def block_length() -> int:
        ...

    @staticmethod
    @abstractmethod
    def scenarios() -> int:
        ...
