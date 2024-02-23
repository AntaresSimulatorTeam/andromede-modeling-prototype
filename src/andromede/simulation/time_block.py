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
from typing import Dict, List, Optional

from anytree import Node as TreeNode

from andromede.simulation.optimization import OrchestrationMethod


# TODO: Move keys elsewhere as variables have no sense in this file
@dataclass(eq=True, frozen=True)
class TimestepComponentVariableKey:
    """
    Identifies the solver variable for one timestep and one component variable.
    """

    component_id: str
    variable_name: str
    block_timestep: Optional[int] = None
    scenario: Optional[int] = None


@dataclass(frozen=True)
class TimeBlock:
    id: int
    timesteps: List[int]

    def __len__(self) -> int:
        return len(self.timesteps)


@dataclass(frozen=True)
class InterDecisionTimeScenarioConfig:
    blocks: List[TimeBlock]
    scenarios: int
    orchestration_method: OrchestrationMethod = field(
        default=OrchestrationMethod.SEQUENTIAL
    )  # Link to resolution and not to problem description, should be placed elsewhere maybe ?


@dataclass(frozen=True)
class ConfiguredTree:
    node_to_config: Dict[TreeNode, InterDecisionTimeScenarioConfig]
