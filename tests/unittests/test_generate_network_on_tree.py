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


from andromede.simulation import TimeBlock
from andromede.simulation.decision_tree import (
    DecisionTreeNode,
    InterDecisionTimeScenarioConfig,
    replicate_network_from_root,
)
from andromede.study.network import Network


def test_generate_model_on_node() -> None:
    scenarios = 1
    blocks = [TimeBlock(1, [0])]
    config = InterDecisionTimeScenarioConfig(blocks, scenarios)

    network = Network("network_id")
    tree_root = DecisionTreeNode("root", config, network)

    assert tree_root.id == "root"
    assert tree_root.parent is None
    assert not tree_root.children  # No children

    child = DecisionTreeNode("child", config, parent=tree_root)

    print(child.parent)

    assert child.parent == tree_root
    assert child in tree_root.children

    replicate_network_from_root(tree_root)

    assert child.network.id == "child_network_id"
