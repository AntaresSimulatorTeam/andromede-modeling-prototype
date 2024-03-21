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


from anytree import Node as TreeNode

from andromede.libs.standard import THERMAL_CLUSTER_MODEL_HD
from andromede.simulation.decision_tree import _generate_tree_model
from andromede.study.network import create_component


def test_generate_model_on_node() -> None:
    thermal = create_component(model=THERMAL_CLUSTER_MODEL_HD, id="thermal")

    tree_node_id = "2030"
    tree_node_model = _generate_tree_model(TreeNode(tree_node_id), thermal)

    # How to compare model efficiently with only change in name ?
    assert tree_node_model.id == f"{tree_node_id}_{thermal.id}"

    for variable in thermal.model.variables.values():
        assert f"{tree_node_id}_{variable.name}" in tree_node_model.variables

        # Create dedicated function
        tree_variable = tree_node_model.variables[f"{tree_node_id}_{variable.name}"]
        # assert
