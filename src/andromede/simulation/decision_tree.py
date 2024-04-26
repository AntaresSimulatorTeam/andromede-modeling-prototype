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
from typing import Generator, Iterable, List, Optional

from anytree import LevelOrderIter, NodeMixin

from andromede.simulation.time_block import TimeBlock
from andromede.study.network import Network


@dataclass(frozen=True)
class InterDecisionTimeScenarioConfig:
    blocks: List[TimeBlock]
    scenarios: int


class DecisionTreeNode(NodeMixin):
    id: str
    config: InterDecisionTimeScenarioConfig
    network: Network

    def __init__(
        self,
        id: str,
        config: InterDecisionTimeScenarioConfig,
        network: Network = Network(""),
        parent: Optional["DecisionTreeNode"] = None,
        children: Optional[Iterable["DecisionTreeNode"]] = None,
    ) -> None:
        self.id = id
        self.config = config
        self.network = network
        self.parent = parent
        if children:
            self.children = children

    def traverse(
        self, depth: Optional[int] = None
    ) -> Generator["DecisionTreeNode", None, None]:
        yield from LevelOrderIter(self, maxlevel=depth)
