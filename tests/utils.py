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

from dataclasses import dataclass, field
from typing import Dict

from andromede.expression.value_provider import (
    TimeScenarioIndex,
    TimeScenarioIndices,
    ValueProvider,
)


# Used only for tests
@dataclass(frozen=True)
class EvaluationContext(ValueProvider):
    """
    Simple value provider relying on dictionaries.
    Does not support component variables/parameters.
    """

    variables: Dict[str, float] = field(default_factory=dict)
    parameters: Dict[str, float] = field(default_factory=dict)

    def get_variable_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        return {TimeScenarioIndex(0, 0): self.variables[name]}

    def get_parameter_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        return {TimeScenarioIndex(0, 0): self.parameters[name]}

    def get_component_variable_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        raise NotImplementedError()

    def get_component_parameter_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        raise NotImplementedError()

    def parameter_is_constant_over_time(self, name: str) -> bool:
        raise NotImplementedError()

    @staticmethod
    def block_length() -> int:
        raise NotImplementedError()

    @staticmethod
    def scenarios() -> int:
        raise NotImplementedError()
