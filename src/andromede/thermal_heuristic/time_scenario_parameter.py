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


@dataclass
class TimeScenarioHourParameter:
    week: int
    scenario: int
    hour: int


@dataclass
class WeekScenarioIndex:
    week: int
    scenario: int


def timesteps(
    index: WeekScenarioIndex,
    parameter: TimeScenarioHourParameter,
) -> list[int]:
    return list(
        range(
            index.week * parameter.hour,
            (index.week + 1) * parameter.hour,
        )
    )
