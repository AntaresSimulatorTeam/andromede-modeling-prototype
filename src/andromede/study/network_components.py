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

from andromede.study import Component, PortRef, PortsConnection


@dataclass(frozen=True)
class NetworkComponents:
    components: Dict[str, Component]
    nodes: Dict[str, Component]
    connections: List[PortsConnection]


def network_components(
    components_list: Iterable[Component],
    nodes: Iterable[Component],
    connections: Iterable[PortsConnection],
) -> NetworkComponents:
    return NetworkComponents(
        components=dict((m.id, m) for m in components_list),
        nodes=dict((n.id, n) for n in nodes),
        connections=list(connections),
    )
