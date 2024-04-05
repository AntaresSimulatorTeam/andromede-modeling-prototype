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
from typing import Dict, Iterable, List

from andromede.study import Component, PortRef


@dataclass(frozen=True)
class Components:
    components: Dict[str, Component]
    connections: Dict[int, List[PortRef]]


def components(
    components_list: Iterable[Component], connections: Dict[int, List[PortRef]]
) -> Components:
    return Components(
        components=dict((m.id, m) for m in components_list), connections=connections
    )
