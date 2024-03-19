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

from andromede.expression.expression import literal, param, var
from andromede.expression.indexing_structure import IndexingStructure
from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    CONSTANT,
    DEMAND_MODEL,
    GENERATOR_MODEL,
    NODE_WITH_SPILL_AND_ENS,
)
from andromede.model import (
    Constraint,
    Model,
    ModelPort,
    ProblemContext,
    float_parameter,
    float_variable,
    int_variable,
    model,
)
from andromede.model.model import PortFieldDefinition, PortFieldId
from andromede.simulation import (
    BendersSolution,
    TimeBlock,
    build_benders_decomposed_problem,
)
from andromede.simulation.decision_tree import (
    create_network_on_tree,
    create_single_node_decision_tree,
)
from andromede.study import (
    Component,
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    TimeIndex,
    TimeSeriesData,
    create_component,
)

CONSTANT = IndexingStructure(False, False)
FREE = IndexingStructure(True, True)

INVESTMENT = ProblemContext.INVESTMENT
OPERATIONAL = ProblemContext.OPERATIONAL
COUPLING = ProblemContext.COUPLING


@pytest.fixture
def thermal_candidate() -> Model:
    THERMAL_CANDIDATE = model(
        id="GEN",
        parameters=[
            float_parameter("op_cost", CONSTANT),
            float_parameter("invest_cost", CONSTANT),
        ],
        variables=[
            float_variable("generation", lower_bound=literal(0)),
            float_variable(
                "p_max",
                lower_bound=literal(0),
                upper_bound=literal(1000),
                structure=CONSTANT,
                context=COUPLING,
            ),
        ],
        ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId("balance_port", "flow"),
                definition=var("generation"),
            )
        ],
        constraints=[
            Constraint(
                name="Max generation", expression=var("generation") <= var("p_max")
            )
        ],
        objective_operational_contribution=(param("op_cost") * var("generation"))
        .sum()
        .expec(),
        objective_investment_contribution=param("invest_cost") * var("p_max"),
    )
    return THERMAL_CANDIDATE


@pytest.fixture
def discrete_candidate() -> Model:
    DISCRETE_CANDIDATE = model(
        id="DISCRETE",
        parameters=[
            float_parameter("op_cost", CONSTANT),
            float_parameter("invest_cost", CONSTANT),
            float_parameter("p_max_per_unit", CONSTANT),
        ],
        variables=[
            float_variable("generation", lower_bound=literal(0)),
            float_variable(
                "p_max",
                lower_bound=literal(0),
                structure=CONSTANT,
                context=COUPLING,
            ),
            int_variable(
                "nb_units",
                lower_bound=literal(0),
                upper_bound=literal(10),
                structure=CONSTANT,
                context=INVESTMENT,
            ),
        ],
        ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId("balance_port", "flow"),
                definition=var("generation"),
            )
        ],
        constraints=[
            Constraint(
                name="Max generation", expression=var("generation") <= var("p_max")
            ),
            Constraint(
                name="Max investment",
                expression=var("p_max") == param("p_max_per_unit") * var("nb_units"),
                context=INVESTMENT,
            ),
        ],
        objective_operational_contribution=(param("op_cost") * var("generation"))
        .sum()
        .expec(),
        objective_investment_contribution=param("invest_cost") * var("p_max"),
    )
    return DISCRETE_CANDIDATE


@pytest.fixture
def generator() -> Component:
    generator = create_component(
        model=GENERATOR_MODEL,
        id="G1",
    )
    return generator


@pytest.fixture
def candidate(thermal_candidate: Model) -> Component:
    candidate = create_component(model=thermal_candidate, id="CAND")
    return candidate


@pytest.fixture
def cluster_candidate(discrete_candidate: Model) -> Component:
    cluster = create_component(model=discrete_candidate, id="DISCRETE")
    return cluster


def test_benders_decomposed_integration(
    generator: Component,
    candidate: Component,
    cluster_candidate: Component,
) -> None:
    """
    Simple generation expansion problem on one node, one timestep and one scenario
    but this time with two candidates: one thermal cluster and one wind cluster.
    We separate master/subproblem and export the problems in MPS format to be solved by the Benders solver in Xpansion

    Demand = 400
    Generator : P_max : 200, Cost : 45
    Unsupplied energy : Cost : 501

    -> 200 of unsupplied energy
    -> Total cost without investment = 45 * 200 + 501 * 200 = 109_200

    Single candidate  : Invest cost : 490 / MW; Prod cost : 10
    Cluster candidate : Invest cost : 200 / MW; Prod cost : 10; Nb of discrete thresholds: 10; Prod per threshold: 10

    Optimal investment : 100 MW (Cluster) + 100 MW (Single)

    -> Optimal cost = 490 * 100 + 10 * 100 (Single)
                    + 200 * 100 + 10 * 100 (Cluster)
                                + 45 * 200 (Generator)
                    =    69_000 +   11_000
                    = 80_000
    """

    database = DataBase()
    database.add_data("D", "demand", ConstantData(400))

    database.add_data("N", "spillage_cost", ConstantData(1))
    database.add_data("N", "ens_cost", ConstantData(501))

    database.add_data("G1", "p_max", ConstantData(200))
    database.add_data("G1", "cost", ConstantData(45))

    database.add_data("CAND", "op_cost", ConstantData(10))
    database.add_data("CAND", "invest_cost", ConstantData(490))

    database.add_data("DISCRETE", "op_cost", ConstantData(10))
    database.add_data("DISCRETE", "invest_cost", ConstantData(200))
    database.add_data("DISCRETE", "p_max_per_unit", ConstantData(10))

    demand = create_component(model=DEMAND_MODEL, id="D")

    node = Node(model=NODE_WITH_SPILL_AND_ENS, id="N")
    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(generator)
    network.add_component(candidate)
    network.add_component(cluster_candidate)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(generator, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(candidate, "balance_port"), PortRef(node, "balance_port"))
    network.connect(
        PortRef(cluster_candidate, "balance_port"), PortRef(node, "balance_port")
    )
    scenarios = 1
    blocks = [TimeBlock(1, [0])]

    configured_tree = create_single_node_decision_tree(blocks, scenarios)
    tree_node_to_network = create_network_on_tree(network, configured_tree.root)

    xpansion = build_benders_decomposed_problem(
        tree_node_to_network, database, configured_tree
    )

    data = {
        "solution": {
            "overall_cost": 80_000,
            "values": {"CAND_p_max_t0_s0": 100, "DISCRETE_p_max_t0_s0": 100},
        }
    }
    solution = BendersSolution(data)

    assert xpansion.run()
    decomposed_solution = xpansion.solution
    if decomposed_solution is not None:  # For mypy only
        assert decomposed_solution.is_close(
            solution
        ), f"Solution differs from expected: {decomposed_solution}"

    assert xpansion.run(should_merge=True)
    merged_solution = xpansion.solution
    if merged_solution is not None:  # For mypy only
        assert merged_solution.is_close(
            solution
        ), f"Solution differs from expected: {merged_solution}"


def test_benders_decomposed_multi_time_block_single_scenario(
    generator: Component,
    candidate: Component,
) -> None:
    """
    Simple generation xpansion problem on one node. Two time blocks with one timestep each,
    one scenario, one thermal cluster candidate.

    Demand = [200, 300]
    Generator : P_max : 200, Cost : 40
    Unsupplied energy : Cost : 501

    -> [0, 100] of unsupplied energy
    -> Total cost without investment = (200 * 40) + (200 * 40 + 100 * 501) = 66_100

    Candidate : Invest cost : 480 / MW, Prod cost : 10

    Optimal investment : 100 MW

    -> Optimal cost = 480 * 100            (investment)
                    +  10 * 100 + 40 * 100 (operational - time block 1)
                    +  10 * 100 + 40 * 200 (operational - time block 2)
                    = 62_000

    """

    data = {}
    data[TimeIndex(0)] = 200
    data[TimeIndex(1)] = 300

    demand_data = TimeSeriesData(time_series=data)

    database = DataBase()
    database.add_data("D", "demand", demand_data)

    database.add_data("N", "spillage_cost", ConstantData(1))
    database.add_data("N", "ens_cost", ConstantData(501))

    database.add_data("G1", "p_max", ConstantData(200))
    database.add_data("G1", "cost", ConstantData(40))

    database.add_data("CAND", "op_cost", ConstantData(10))
    database.add_data("CAND", "invest_cost", ConstantData(480))

    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    node = Node(model=NODE_WITH_SPILL_AND_ENS, id="N")
    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(generator)
    network.add_component(candidate)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(generator, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(candidate, "balance_port"), PortRef(node, "balance_port"))

    scenarios = 1
    blocks = [TimeBlock(1, [0]), TimeBlock(2, [1])]

    configured_tree = create_single_node_decision_tree(blocks, scenarios)
    tree_node_to_network = create_network_on_tree(network, configured_tree.root)

    xpansion = build_benders_decomposed_problem(
        tree_node_to_network, database, configured_tree
    )

    data = {
        "solution": {
            "overall_cost": 62_000,
            "values": {
                "CAND_p_max_t0_s0": 100,
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
