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

from andromede.model.model import Model
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

    def traverse(self) -> Generator["DecisionTreeNode", None, None]:
        yield from LevelOrderIter(self)


def replicate_network_from_root(root: DecisionTreeNode) -> None:
    if root.size == 1:
        # Nothing to replicate. Just past down the network
        return

    else:
        # Replicates the network and updates their id to take into account the tree node's id
        original_network_id = root.network.id
        for tree_node in LevelOrderIter(root):
            tree_node.network = root.network.replicate(
                id=f"{tree_node.id}_{original_network_id}"
            )


def create_master_network(
    root: DecisionTreeNode,
    decision_coupling_model: Optional[Model],
) -> Network:
    # TODO
    return root.network
