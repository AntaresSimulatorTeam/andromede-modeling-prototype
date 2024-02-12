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


@dataclass(frozen=True)
class IndexingStructure:
    """
    Specifies if parameters and variables should be indexed by time and/or scenarios.
    """

    time: bool
    scenario: bool

    def __or__(self, other: "IndexingStructure") -> "IndexingStructure":
        time = self.time or other.time
        scenario = self.scenario or other.scenario
        return IndexingStructure(time, scenario)
