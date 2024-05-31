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
from anytree import Node as TreeNode

from andromede.expression import literal, var
from andromede.expression.indexing_structure import IndexingStructure
from andromede.libs.standard import (
    DEMAND_MODEL,
    GENERATOR_MODEL,
    NODE_WITH_SPILL_AND_ENS,
    THERMAL_CANDIDATE_WITH_ALREADY_INSTALLED_CAPA,
)
from andromede.model.common import ProblemContext
from andromede.model.constraint import Constraint
from andromede.model.model import model
from andromede.model.variable import float_variable
from andromede.simulation import (
    BendersSolution,
    TimeBlock,
    build_benders_decomposed_problem,
)
from andromede.simulation.decision_tree import (
    DecisionTreeNode,
    InterDecisionTimeScenarioConfig,
)
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


def test_investment_pathway_on_sequential_nodes(
    node: Node,
    demand: Component,
    candidate: Component,
) -> None:
    database = DataBase()
    database.add_data("N", "spillage_cost", ConstantData(10))
    database.add_data("N", "ens_cost", ConstantData(10000))

    database.add_data(
        "D",
        "demand",
        TreeData(
            {
                "parent": ConstantData(100),
                "child": ConstantData(200),
            }
        ),
    )

    database.add_data("CAND", "op_cost", ConstantData(10))
    database.add_data("CAND", "already_installed_capa", ConstantData(100))

    database.add_data(
        "CAND",
        "invest_cost",
        TreeData(
            {
                "parent": ConstantData(100),
                "child": ConstantData(300),
            }
        ),
    )

    database.add_data(
        "CAND",
        "max_invest",
        TreeData(
            {
                "parent": ConstantData(80),
                "child": ConstantData(100),
            }
        ),
    )

    COUPLING_MODEL = model(
        id="COUPLING",
        variables=[
            float_variable(
                "parent_CAND_delta_invest",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
            float_variable(
                "parent_CAND_invested_capa",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
            float_variable(
                "child_CAND_delta_invest",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
            float_variable(
                "child_CAND_invested_capa",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
        ],
        constraints=[
            Constraint(
                name="Max investment on parent",
                expression=var("parent_CAND_invested_capa")
                == var("parent_CAND_delta_invest"),
                context=ProblemContext.INVESTMENT,
            ),
            Constraint(
                name="Max investment on child",
                expression=var("child_CAND_invested_capa")
                == var("child_CAND_delta_invest") + var("parent_CAND_invested_capa"),
                context=ProblemContext.INVESTMENT,
            ),
        ],
    )

    network_coupling = Network("coupling_test")
    network_coupling.add_component(create_component(model=COUPLING_MODEL, id=""))

    demand_par = demand.replicate()
    candidate_par = candidate.replicate()

    network_par = Network("parent_test")
    network_par.add_node(node)
    network_par.add_component(demand_par)
    network_par.add_component(candidate_par)
    network_par.connect(
        PortRef(demand_par, "balance_port"), PortRef(node, "balance_port")
    )
    network_par.connect(
        PortRef(candidate_par, "balance_port"), PortRef(node, "balance_port")
    )

    demand_chd = demand.replicate()
    candidate_chd = candidate.replicate()

    network_chd = Network("child_test")
    network_chd.add_node(node)
    network_chd.add_component(demand_chd)
    network_chd.add_component(candidate_chd)
    network_chd.connect(
        PortRef(demand_chd, "balance_port"), PortRef(node, "balance_port")
    )
    network_chd.connect(
        PortRef(candidate_chd, "balance_port"), PortRef(node, "balance_port")
    )

    config = InterDecisionTimeScenarioConfig([TimeBlock(0, [0])], 1)

    decision_tree_par = DecisionTreeNode("parent", config, network_par)
    decision_tree_chd = DecisionTreeNode(
        "child", config, network_chd, parent=decision_tree_par
    )

    xpansion = build_benders_decomposed_problem(
        decision_tree_par, database, coupling_network=network_coupling
    )

    data = {
        "solution": {
            "overall_cost": 17_000,
            "values": {
                "parent_CAND_delta_invest": 80,
                "child_CAND_delta_invest": 20,
                "parent_CAND_invested_capa": 80,
                "child_CAND_invested_capa": 100,
            },
        }
    }
    solution = BendersSolution(data)

    assert xpansion.run()
    decomposed_solution = xpansion.solution
    if decomposed_solution is not None:  # For mypy only
        assert decomposed_solution.is_close(
            solution
        ), f"Solution differs from expected: {decomposed_solution}"


def test_investment_pathway_on_a_tree_with_one_root_two_children(
    generator: Component,
    candidate: Component,
    demand: Component,
    node: Node,
) -> None:
    """
    This use case aims at representing the situation where investment decisions are to be made at different, say "planning times".
    An actualization rate can be taken into account.

    The novelty compared the actual usage of planning tools, is that the planning decisions at a given time
    are taken without knowing exactly which "macro-scenario" / hypothesis on the system that will eventually happen
    (only knowing the probability distribution of these hypothesis).

    This example models a case where investment decisions have to be made in 2030 and 2040.
        - In 2030, we have full knowledge of the existing assets
        - In 2040, two possible hypothesis are possible :
            - P=0.2 => A case where there is no change in the generation assets since 2030 (except te potential investment in 2030)
            - P=0.8 => A case where a base generation unit is present

    When taking the decision in 2030, we do not know which case will occur in 2040
    and we seek the best decision given a risk criterion (the expectation here).
    The value of these models lies in the output for the first decision rather than
    the decisions at the later stages as the first decisions are related to "what we have to do today" ?
    More specifically, to define the use case, we define the following tree representing the system at the different decision times and hypothesis

    2030 (root node) :
        Demand = 300
        Generator :
            P_max = 200,
            Production cost = 10,
            Max investment = 400,
            Investment cost = 100
        Unsupplied energy :
            Cost = 10 000

    2040 with new base (child A) :
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
            Cost = 10 000

    2040 no base (child B) :
        Demand = 600
        Generator :
            P_max = 200,
            Production cost = 10,
            Max investment = 100,
            Investment cost = 50
        Unsupplied energy :
            Cost = 10 000

    In the second decision time, demand increases from 300 to 600 in both scenarios.
    However, investment capacity in the candidate is limited to 100 in the second stage.
    Investment cost decreases to reflect the effect of a discount rate.

    In case 1, a base unit of capacity 100 has arrived and can produce at smaller cost than the candidate.
    As it is more interesting to invest the latest possible, the optimal solution for this scenario is to invest [100, 100].

    In case 2, there is no base unit and the max investment is 100 in the second stage,
    therefore if we consider scenario 2 only, as unsupplied energy is very expensive, the best investment is [300, 100]

    But here as we solve on the tree, we need to find the best solution in expectation on the set of paths in the tree.

    Case 1 :    prob    |    investment   |  operational
    root:             1 x [     100 x 100 +     10 x 300 ]
    child A:      + 0.8 x [      50 x 100 +     10 x 400 (generator) + 5 x 200 (base)]
    child B:      + 0.2 x [      50 x 100 +     10 x 400 (generator) + 10 000 x 200 (unsupplied energy)]
                  = 422 800

    Case 2 :    prob    |    investment   |  operational
    root:             1 x [     100 x 300 +     10 x 300 ]
    child A:      + 0.8 x [      50 x   0 +     10 x 400 (generator) + 5 x 200 (base)]
    child B:      + 0.2 x [      50 x 100 +     10 x 600 (generator)]
                  = 39 200

    As investing less than 300 in the first stage would increase the unsupplied energy and lead to an increase in overall cost
    (-1 MW invested in 1st stage => + 1 MW unsupplied energy => +900/MW cost increase more or less), the optimal solution is to invest :
        - 300 at first stage
        - 0 in child A
        - 100 in child B
    """

    # Either we duplicate all network for each node : Lots of duplications
    # or we index all data, parameters, variables by the resolution node : Make the data structure dependent of the resolution tree...

    database = DataBase()
    database.add_data("N", "spillage_cost", ConstantData(10))
    database.add_data("N", "ens_cost", ConstantData(10_000))

    database.add_data(
        "D",
        "demand",
        TreeData(
            {
                "root": ConstantData(300),
                "childA": ConstantData(600),
                "childB": ConstantData(600),
            }
        ),
    )

    database.add_data("CAND", "op_cost", ConstantData(10))
    database.add_data("CAND", "already_installed_capa", ConstantData(200))
    database.add_data(
        "CAND",
        "invest_cost",
        TreeData(
            {
                "root": ConstantData(100),
                "childA": ConstantData(50),
                "childB": ConstantData(50),
            }
        ),
    )
    database.add_data(
        "CAND",
        "max_invest",
        TreeData(
            {
                "root": ConstantData(400),
                "childA": ConstantData(100),
                "childB": ConstantData(100),
            }
        ),
    )

    database.add_data("BASE", "p_max", ConstantData(200))
    database.add_data("BASE", "cost", ConstantData(5))

    COUPLING_MODEL = model(
        id="COUPLING",
        variables=[
            float_variable(
                "root_CAND_delta_invest",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
            float_variable(
                "root_CAND_invested_capa",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
            float_variable(
                "childA_CAND_delta_invest",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
            float_variable(
                "childA_CAND_invested_capa",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
            float_variable(
                "childB_CAND_delta_invest",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
            float_variable(
                "childB_CAND_invested_capa",
                lower_bound=literal(0),
                structure=IndexingStructure(False, False),
                context=ProblemContext.INVESTMENT,
            ),
        ],
        constraints=[
            Constraint(
                name="Max investment on root",
                expression=var("root_CAND_invested_capa")
                == var("root_CAND_delta_invest"),
                context=ProblemContext.INVESTMENT,
            ),
            Constraint(
                name="Max investment on child A",
                expression=var("childA_CAND_invested_capa")
                == var("childA_CAND_delta_invest") + var("root_CAND_invested_capa"),
                context=ProblemContext.INVESTMENT,
            ),
            Constraint(
                name="Max investment on child B",
                expression=var("childB_CAND_invested_capa")
                == var("childB_CAND_delta_invest") + var("root_CAND_invested_capa"),
                context=ProblemContext.INVESTMENT,
            ),
        ],
    )

    network_coupler = Network("coupling_test")
    network_coupler.add_component(create_component(model=COUPLING_MODEL, id=""))

    network_root = Network("root_network")
    network_root.add_node(node)
    network_root.add_component(demand)
    network_root.add_component(candidate)
    network_root.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network_root.connect(
        PortRef(candidate, "balance_port"), PortRef(node, "balance_port")
    )

    network_childA = network_root.replicate(id="childA_network")
    network_childA.add_component(generator)
    network_childA.connect(
        PortRef(generator, "balance_port"), PortRef(node, "balance_port")
    )

    network_childB = network_root.replicate(id="childB_network")

    scenarios = 1
    time_scenario_config = InterDecisionTimeScenarioConfig(
        [TimeBlock(0, [0])], scenarios
    )

    # TODO Implement the prob behavior for the Expected Value
    dt_root = DecisionTreeNode("root", time_scenario_config, network_root)
    dt_child_A = DecisionTreeNode(
        "childA", time_scenario_config, network_childA, parent=dt_root, prob=0.8
    )
    dt_child_B = DecisionTreeNode(
        "childB", time_scenario_config, network_childB, parent=dt_root, prob=0.2
    )

    xpansion = build_benders_decomposed_problem(
        dt_root, database, coupling_network=network_coupler
    )
    xpansion.initialise(is_debug=True)

    data = {
        "solution": {
            "overall_cost": 49_000,
            "values": {
                "root_CAND_delta_invest": 300,
                "childA_CAND_delta_invest": 0,
                "childB_CAND_delta_invest": 100,
                "root_CAND_invested_capa": 300,
                "childA_CAND_invested_capa": 300,
                "childB_CAND_invested_capa": 400,
            },
        }
    }
    solution = BendersSolution(data)

    assert xpansion.run()
    decomposed_solution = xpansion.solution
    if decomposed_solution is not None:  # For mypy only
        assert decomposed_solution.is_close(
            solution
        ), f"Solution differs from expected: {decomposed_solution}"
