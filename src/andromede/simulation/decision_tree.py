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

import math
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
    prob: float

    def __init__(
        self,
        id: str,
        config: InterDecisionTimeScenarioConfig,
        network: Network = Network(""),
        parent: Optional["DecisionTreeNode"] = None,
        children: Optional[Iterable["DecisionTreeNode"]] = None,
        prob: float = 1.0,
    ) -> None:
        self.id = id
        self.config = config
        self.network = network
        self.parent = parent

        if prob < 0 or 1 < prob:
            raise ValueError("Probability must be a value in the range [0, 1]")

        self.prob = prob * (parent.prob if parent is not None else 1)
        if children:
            self.children = children

    def traverse(
        self, depth: Optional[int] = None
    ) -> Generator["DecisionTreeNode", None, None]:
        yield from LevelOrderIter(self, maxlevel=depth)

    def is_leaves_prob_sum_one(self) -> bool:
        if not self.children:
            return True

        # Since we multiply the child's prob by the parent's prob
        # in the constructor, the sum of the children prob should
        # equal 1 * parent.prob if the values were set correctly
        if not math.isclose(self.prob, sum(child.prob for child in self.children)):
            return False

        # Recursively check if child nodes have their children's
        # probability sum equal to one
        return all(child.is_leaves_prob_sum_one() for child in self.children)
