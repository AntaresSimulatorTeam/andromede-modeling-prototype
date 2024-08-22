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

from andromede.expression import literal, var
from andromede.expression.indexing_structure import IndexingStructure
from andromede.model.common import ProblemContext
from andromede.model.constraint import Constraint
from andromede.model.model import model
from andromede.model.variable import Variable, float_variable
from andromede.simulation.time_block import TimeBlock
from andromede.study.network import (
    Component,
    Network,
    PortRef,
    build_ports_connection,
    create_component,
)


@dataclass(frozen=True)
class InterDecisionTimeScenarioConfig:
    blocks: List[TimeBlock]
    scenarios: int


class DecisionTreeNode(NodeMixin):
    id: str
    config: InterDecisionTimeScenarioConfig
    network: Network
    coupling_network: Network
    prob: float

    def __init__(
        self,
        id: str,
        config: InterDecisionTimeScenarioConfig,
        network: Network,
        parent: Optional["DecisionTreeNode"] = None,
        children: Optional[Iterable["DecisionTreeNode"]] = None,
        prob: float = 1.0,
        coupling_network: Network = Network("_Coupler"),
    ) -> None:
        self.id = id
        self.config = config
        self.network = network
        self.coupling_network = coupling_network
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

    def connect_from_parent(self, port: PortRef, parent_port: PortRef) -> None:
        if self.parent is None:
            raise RuntimeError("Cannot connect upwards because no parent is defined")

        ports_connection = build_ports_connection(
            port, parent_port, self.id, self.parent.id
        )
        self.network._connections.append(ports_connection)

    def connect_to_children(self, port: PortRef, children_port: PortRef) -> None:
        if not self.children:
            raise RuntimeError("Cannot connect downwards because no child is defined")

        for child in self.children:
            ports_connection = build_ports_connection(
                port, children_port, self.id, child.id
            )
            child.network._connections.append(ports_connection)

    def add_coupling_component(
        self,
        component: Component,
        cumulative_var_id: str,
        delta_var_id: str,
    ) -> None:
        if not component.is_variable_in_model(cumulative_var_id):
            raise ValueError(
                f"Cumulative variable {cumulative_var_id} not present in {component.id}"
            )

        if not component.is_variable_in_model(delta_var_id):
            raise ValueError(
                f"Incremental variable {delta_var_id} not present in {component.id}"
            )

        variables: List[Variable] = []
        constraints: List[Constraint] = []

        for tree_node in self.traverse():
            parent_cumulative_var_id = (
                f"{tree_node.parent.id}_{component.id}_{cumulative_var_id}"
                if tree_node.parent is not None
                else ""
            )
            node_cumulative_var_id = (
                f"{tree_node.id}_{component.id}_{cumulative_var_id}"
            )
            node_delta_var_id = f"{tree_node.id}_{component.id}_{delta_var_id}"

            variables.extend(
                (
                    # TODO For now, unbounded positive float variable for both
                    # Eventually should allow more flexibility
                    float_variable(
                        node_cumulative_var_id,
                        lower_bound=literal(0),
                        structure=IndexingStructure(False, False),
                        context=ProblemContext.INVESTMENT,
                    ),
                    float_variable(
                        node_delta_var_id,
                        lower_bound=literal(0),
                        structure=IndexingStructure(False, False),
                        context=ProblemContext.INVESTMENT,
                    ),
                )
            )

            # TODO For now, only kind of relationship allowed between nodes
            # Eventually should give the user the possibility to define the expression
            constraints.append(
                Constraint(
                    name=f"Cumulative max investment on {tree_node.id}",
                    expression=var(node_cumulative_var_id) - var(node_delta_var_id)
                    == (
                        var(parent_cumulative_var_id)
                        if parent_cumulative_var_id
                        else literal(0)
                    ),
                    context=ProblemContext.INVESTMENT,
                ),
            )

        self.coupling_network.add_component(
            create_component(
                model(
                    id="coupling_decision_tree_model",
                    variables=variables,
                    constraints=constraints,
                ),
                id="",
            )
        )

        return
