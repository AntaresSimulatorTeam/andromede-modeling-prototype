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

from andromede.libs.standard import (
    DEMAND_MODEL,
    GENERATOR_MODEL,
    NODE_WITH_SPILL_AND_ENS,
    THERMAL_CANDIDATE_WITH_ALREADY_INSTALLED_CAPA,
)
from andromede.simulation.optimization import build_problem
from andromede.simulation.optimization_orchestrator import OptimizationOrchestrator
from andromede.simulation.output_values import OutputValues
from andromede.simulation.time_block import ResolutionNode, TimeBlock
from andromede.study.data import ConstantData, DataBase, TreeData
from andromede.study.network import Component, Network, Node, PortRef, create_component


@pytest.fixture
def generator() -> Component:
    generator = create_component(
        model=GENERATOR_MODEL,
        id="BASE",
    )
    return generator


@pytest.fixture
def candidate() -> Component:
    candidate = create_component(
        model=THERMAL_CANDIDATE_WITH_ALREADY_INSTALLED_CAPA, id="CAND"
    )
    return candidate


@pytest.fixture
def demand() -> Component:
    demand = create_component(model=DEMAND_MODEL, id="D")
    return demand


@pytest.fixture
def node() -> Node:
    node = Node(model=NODE_WITH_SPILL_AND_ENS, id="N")
    return node


def test_investment_pathway_on_a_tree_with_one_root_two_children(
    generator: Component,
    candidate: Component,
    demand: Component,
    node: Node,
) -> None:
    """
    This use case aims at representing the situation where investment decisions are to be made at different, say "planning times". An actualisation rate can be taken into account.

    The novelty compared the actual usage of planning tools, is that the planning decisions at a given time are taken without knowing exactly which "macro-scenario" / hypothesis on the system that will eventually happen (only knowing the probability distribution of these hypothesis).

    This example models a case where investment decisions have to be made in 2030 and 2040.
        - In 2030, we have full knowledge of the existing assets
        - In 2040, two equiprobable hypothesis are possible :
            - A case where there is no change in the generation assets since 2030 (except te potential investment in 2030)
            - A case where a base generation unit is present

    When taking the decision in 2030, we do not know which case will occur in 2040 and we seek the best decision given a risk criterion (the expectation here).

    The value of these models lies in the output for the first decision rather than the decisions at the later stages as the first decisions are related to "what we have to do today" ?  

    More specifically, to define the use case, we define the following tree representing the system at the different decision times and hypothesis

    2030 (root node) :
        Demand = 300
        Generator :
            P_max = 200,
            Production cost = 10,
            Max investment = 400,
            Investment cost = 100
        Unsupplied energy :
            Cost = 10000

    2040 with new base (scenario 1) :
        Demand = 600
        Generator :
            P_max = 200,
            Production cost = 10,
            Max investment = 100,
            Investment cost = 50
        Base :
            P_max = 200,
            Production cost = 5
        Unsupplied energy :
            Cost = 10000

    2040 no base (scenario 2) :
        Demand = 600
        Generator :
            P_max = 200,
            Production cost = 10,
            Max investment = 100,
            Investment cost = 50
        Unsupplied energy :
            Cost = 10000

    In the second decision time, demand increases from 300 to 600 in both scenarios. However, investment capacity in the candidate is limited to 100 in the second stage. Investment cost decreases to reflect the effect of a discount rate.

    In case 1, a base unit of capacity 100 has arrived and can produce at the same cost than the candidate. As it is more intersting to invest the latest possible, the optimal solution for scenario 1 is to invest [100, 100].

    In case 2, there is no base unit and the max investment is 100 in the second stage, therefore if we consider scenario 2 only, as unsupplied energy is very expensive, the best investment is [300, 100]

    But here as we solve on the tree, we need to find the best solution in expectation on the set of paths in the tree.

    With initial investment = 100 :
        Total cost = [100 x 100 (investment root) + 10 x 300 (prod root)]
            + 0.5 (proba child 1) x [100 x 50 (investment child 1) + 10 x 400 (prod generator) + 5 x 200 (prod base)]
            + 0.5 (proba child 2) x [100 x 50 (investment child 2) + 10 x 400 (prod generator) + 1000 x 200 (unsupplied energy)]
            = 122 500

    With initial investment = 300 :
        Total cost = [100 x 300 (investment root) + 10 x 300 (prod root)]
            + 0.5 (proba child 1) x [10 x 400 (prod generator) + 5 x 200 (prod base)]
            + 0.5 (proba child 2) x [100 x 50 (investment child 2) + 10 x 600 (prod generator)]
            = 41 000

    As investing less than 300 in the first stage would increase the unsupplied energy and lead to an increase in overall cost (-1 MW invested in 1st stage => + 1 MW unsp energy => +900/MW cost increase more or less), the optimal solution is to invest :
        - 300 at first stage
        - 0 in child 1
        - 100 in child 2

    """

    # Either we duplicate all network for each node : Lots of duplications
    # or we index all data, parameters, variables by the resolution node : Make the data struture dependent of the resolution tree...

    database = DataBase()
    database.add_data("N", "spillage", ConstantData(10))
    database.add_data("N", "unsupplied_energy", ConstantData(10000))

    database.add_data(
        "D",
        "demand",
        TreeData({0: ConstantData(300), 1: ConstantData(600), 2: ConstantData(600)}),
    )

    database.add_data("CAND", "op_cost", ConstantData(10))
    database.add_data("CAND", "already_installed_capa", ConstantData(200))
    database.add_data(
        "CAND",
        "invest_cost",
        TreeData({0: ConstantData(100), 1: ConstantData(50), 2: ConstantData(50)}),
    )
    database.add_data(
        "CAND",
        "max_invest",
        TreeData({0: ConstantData(400), 1: ConstantData(100), 2: ConstantData(100)}),
    )

    database.add_data(
        "BASE",
        "p_max",
        TreeData({0: ConstantData(0), 1: ConstantData(200), 2: ConstantData(0)}),
    )
    database.add_data("BASE", "cost", ConstantData(5))

    # Fonction qui crée les composants / noeud en fonction de l'arbre et du Database initial / modèles + générer les contraintes couplantes temporelles trajectoire + actualisation + 
    # contraintes industrielles liées à l'arbre ?
    # Test mode peigne
    # Générer le modèle "couplant"

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(generator)
    network.add_component(candidate)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(generator, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(candidate, "balance_port"), PortRef(node, "balance_port"))

    root = ResolutionNode("2030", [TimeBlock(0, [0])])
    child_1 = ResolutionNode("2040_new_base", [TimeBlock(0, [0])])
    child_2 = ResolutionNode("2040_no_base", [TimeBlock(0, [0])])
    resolution_tree = ResolutionNode(root, [child_1, child_2])

    scenarios = 1

    orchestrator = OptimizationOrchestrator(network, database, resolution_tree)
    solution_tree = orchestrator.run()

    # Réfléchir à la représentation des variables dans l'arbre
