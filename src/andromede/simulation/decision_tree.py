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
from andromede.simulation.strategy import InvestmentProblemStrategy
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


def replicate_network_from(root: DecisionTreeNode) -> None:
    if root.size == 1:
        # Nothing to replicate. Just past down the network
        return

    else:
        # Replicates the network and updates their id to take into account the tree node's id
        original_network_id = root.network.id
        for tree_node in root.traverse():
            tree_node.network = root.network.replicate(
                id=f"{tree_node.id}_{original_network_id}"
            )


def create_master_network(
    root: DecisionTreeNode,
    decision_coupling_model: Optional[Model],
) -> Network:
    # TODO Use ports for coupling different models across the decision tree
    """
    Each candidate model should have one of these ports.
    As for balance, they all should  have a common name like "investment" and they could be defined as:

    ports=[ModelPort(port_type=INVESTMENT_PORT_TYPE, port_name="investment_port")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("investment_port", "investment"),
            definition=param("p_max"), ---> p_max if we are investing the p_max for instance
        )
    ],

    Then, here, we would traverse the tree and create a Network that only keeps
    variables allowed in the InvestmentProblemStrategy (we would need to change their names to something like
    p_max_root, p_max_child_id, p_max_child_id2, ...)
    We would connect them by some constraints using these ports to the decision_coupling_model (a parameter here),
    so we could have something like:

    master_network.connect(PortRef(candidate_on_root, "investment_port"), PortRef(coupling_model, "investment_port"))
    master_network.connect(PortRef(candidate_on_child, "investment_port"), PortRef(coupling_model, "investment_port"))

    On the coupling model, we would have something like for the nodes:
    ports=[ModelPort(port_type=INVESTMENT_PORT_TYPE, port_name="investment_port")],
    binding_constraints=[
        Constraint(
            name="Pathway_Investment",
            expression=port_field("investment_port", "flow").some_operator(),
        )
    ],

    Maybe we would have to define a operator to represent consecutive inequalities ?
    Or create one coupling model per pair parent-child so the expression would become
    port_field("investment_port", "flow").sum_connections() <= 0 ? In this case, we would have to define
    a negative and a positive value

    To resume, a network here would need:
     - All candidates on all tree nodes (so we don't make great changes on build_problem)
        - Update investment variable names to show their corresponding tree node;
        - Add a investment port to each model
     - A coupling model with the good ports to connect to
        - The binding constraint that ties everything
    """
    if root.size == 1:
        # Nothing to replicate. Just past down the network
        return root.network

    master_network = Network(f"{root.id}_{root.network.id}")

    # # We assume that the network was copied already
    # # TODO add a guard to verify it

    # for tree_node in root.traverse():
    #     for component_on_node in tree_node.network.components:
    #         component = component_on_node.replicate(id=f"{tree_node.id}_{component_on_node.id}")
    #         master_network.add_component(component)

    return master_network
