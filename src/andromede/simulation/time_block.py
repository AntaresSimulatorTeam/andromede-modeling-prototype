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

import ortools.linear_solver.pywraplp as lp


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
class ResolutionNode:
    id: str
    blocks: List[TimeBlock] # Séparer horizon de simu annuel
    children: List["ResolutionNode"] = field(default_factory=list)
    # solution: Dict[TimestepComponentVariableKey, lp.Variable]
    
class InBetweenMasterDecisionTimeHorizon:
    blocks : List[TimeBlock]