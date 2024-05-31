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

import pytest

from andromede.simulation import TimeBlock
from andromede.simulation.decision_tree import (
    DecisionTreeNode,
    InterDecisionTimeScenarioConfig,
)
from andromede.study.network import Network


def test_generate_model_on_node() -> None:
    scenarios = 1
    blocks = [TimeBlock(1, [0])]
    config = InterDecisionTimeScenarioConfig(blocks, scenarios)

    network = Network("network_id")
    root = DecisionTreeNode("root", config, network)

    assert root.id == "root"
    assert root.parent is None
    assert root.prob == 1.0
    assert not root.children  # No children

    child = DecisionTreeNode("child", config, parent=root, prob=0.8)

    assert child.parent == root
    assert child.prob == 0.8
    assert child in root.children

    grandchild = DecisionTreeNode("grandchild", config, parent=child)

    assert grandchild.parent == child
    assert (grandchild not in root.children) and (grandchild in child.children)

    with pytest.raises(ValueError, match="Probability must be a value in the range"):
        great_grandchild = DecisionTreeNode(
            "greatgrandchild", config, parent=grandchild, prob=2.0
        )

    with pytest.raises(ValueError, match="Probability must be a value in the range"):
        great_grandchild = DecisionTreeNode(
            "greatgrandchild", config, parent=grandchild, prob=-0.3
        )
