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

from pathlib import Path

import pytest

from andromede.libs.standard import (
    DEMAND_MODEL,
    GENERATOR_MODEL,
    LINK_MODEL,
    NODE_WITH_SPILL_AND_ENS,
    RES_MODEL,
    THERMAL_CANDIDATE,
)
from andromede.simulation import TimeBlock, build_benders_decomposed_problem
from andromede.simulation.decision_tree import (
    DecisionTreeNode,
    InterDecisionTimeScenarioConfig,
)
from andromede.study.data import ConstantData, DataBase
from andromede.study.network import Network, Node, PortRef, create_component
from tests.unittests.test_utils import generate_random_data

BLOCK_LENGTH = 24 * 7  # One week
NB_BLOCKS = 2
NB_SCENARIOS = 2


@pytest.fixture
def network() -> Network:
    network = Network("test_case")

    # Area 1
    area1 = Node(model=NODE_WITH_SPILL_AND_ENS, id="Area1")
    load1 = create_component(model=DEMAND_MODEL, id="D1")
    wind1 = create_component(model=RES_MODEL, id="Wind1")
    base1 = create_component(model=GENERATOR_MODEL, id="Base1")
    semi1 = create_component(model=GENERATOR_MODEL, id="SemiBase1")
    peak1 = create_component(model=GENERATOR_MODEL, id="Peak1")

    network.add_node(area1)
    network.add_component(load1)
    network.add_component(wind1)
    network.add_component(base1)
    network.add_component(semi1)
    network.add_component(peak1)
    network.connect(PortRef(load1, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(wind1, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(base1, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(semi1, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(peak1, "balance_port"), PortRef(area1, "balance_port"))

    # Area 2
    area2 = Node(model=NODE_WITH_SPILL_AND_ENS, id="Area2")
    load2 = create_component(model=DEMAND_MODEL, id="D2")
    wind2 = create_component(model=RES_MODEL, id="Wind2")
    base2 = create_component(model=GENERATOR_MODEL, id="Base2")
    semi2 = create_component(model=GENERATOR_MODEL, id="SemiBase2")
    peak2 = create_component(model=GENERATOR_MODEL, id="Peak2")

    network.add_node(area2)
    network.add_component(load2)
    network.add_component(wind2)
    network.add_component(base2)
    network.add_component(semi2)
    network.add_component(peak2)
    network.connect(PortRef(load2, "balance_port"), PortRef(area2, "balance_port"))
    network.connect(PortRef(wind2, "balance_port"), PortRef(area2, "balance_port"))
    network.connect(PortRef(base2, "balance_port"), PortRef(area2, "balance_port"))
    network.connect(PortRef(semi2, "balance_port"), PortRef(area2, "balance_port"))
    network.connect(PortRef(peak2, "balance_port"), PortRef(area2, "balance_port"))

    # Link
    link12 = create_component(model=LINK_MODEL, id="Area1/Area2")
    network.add_component(link12)
    network.connect(
        PortRef(link12, "balance_port_from"), PortRef(area1, "balance_port")
    )
    network.connect(PortRef(link12, "balance_port_to"), PortRef(area2, "balance_port"))

    # Candidates
    cand_semi = create_component(model=THERMAL_CANDIDATE, id="Cand_Semi")
    cand_peak = create_component(model=THERMAL_CANDIDATE, id="Cand_Peak")

    network.add_component(cand_semi)
    network.add_component(cand_peak)
    network.connect(PortRef(cand_semi, "balance_port"), PortRef(area1, "balance_port"))
    network.connect(PortRef(cand_peak, "balance_port"), PortRef(area1, "balance_port"))

    return network


@pytest.fixture
def database() -> DataBase:
    path = Path("tests/functional/data/pathway_test_case/")

    # Magic numbers based on real data
    # The main expected behaviors are:
    # - Loads are much bigger than RES;
    # - RES vary from 0 to a limit, loads never go to 0
    # - RES varies a lot, i.e., big std deviations proportionally to their mean
    wind1 = generate_random_data(
        400, 380, NB_BLOCKS * BLOCK_LENGTH, NB_SCENARIOS, upper=800, lower=0
    )
    wind2 = generate_random_data(
        500, 420, NB_BLOCKS * BLOCK_LENGTH, NB_SCENARIOS, upper=900, lower=0
    )
    load1 = generate_random_data(
        3200, 750, NB_BLOCKS * BLOCK_LENGTH, NB_SCENARIOS, upper=5300, lower=1700
    )
    load2 = generate_random_data(
        3000, 800, NB_BLOCKS * BLOCK_LENGTH, NB_SCENARIOS, upper=5600, lower=1600
    )

    database = DataBase()

    # Area 1
    database.add_data("Area1", "spillage_cost", ConstantData(0))
    database.add_data("Area1", "ens_cost", ConstantData(20_000))

    database.add_data("D1", "demand", load1)
    database.add_data("Wind1", "production", wind1)

    database.add_data("Base1", "cost", ConstantData(20))
    database.add_data("Base1", "p_max", ConstantData(3 * 900))

    database.add_data("SemiBase1", "cost", ConstantData(45))
    database.add_data("SemiBase1", "p_max", ConstantData(2 * 450))

    database.add_data("Peak1", "cost", ConstantData(100))
    database.add_data("Peak1", "p_max", ConstantData(10 * 100))

    # Area 2
    database.add_data("Area2", "spillage_cost", ConstantData(0))
    database.add_data("Area2", "ens_cost", ConstantData(20_000))

    database.add_data("D2", "demand", load2)
    database.add_data("Wind2", "production", wind2)

    database.add_data("Base2", "cost", ConstantData(20))
    database.add_data("Base2", "p_max", ConstantData(3 * 900))

    database.add_data("SemiBase2", "cost", ConstantData(45))
    database.add_data("SemiBase2", "p_max", ConstantData(2 * 450))

    database.add_data("Peak2", "cost", ConstantData(100))
    database.add_data("Peak2", "p_max", ConstantData(2 * 100))

    # Link
    database.add_data("Area1/Area2", "f_max", ConstantData(1_000))

    # Candidates
    database.add_data("Cand_Semi", "op_cost", ConstantData(40))
    database.add_data("Cand_Semi", "max_invest", ConstantData(2 * 200))
    database.add_data("Cand_Semi", "invest_cost", ConstantData(21_000))

    database.add_data("Cand_Peak", "op_cost", ConstantData(95))
    database.add_data("Cand_Peak", "max_invest", ConstantData(3 * 100))
    database.add_data("Cand_Peak", "invest_cost", ConstantData(15_000))

    return database


def test_large_scale_investment(network: Network, database: DataBase) -> None:
    """
    Single node investment tree with 2 weeks and 2 time-series
    """
    time_blocks = [
        TimeBlock(i, list(range(i * (BLOCK_LENGTH), i * (BLOCK_LENGTH) + BLOCK_LENGTH)))
        for i in range(NB_BLOCKS)
    ]
    config = InterDecisionTimeScenarioConfig(time_blocks, NB_SCENARIOS)
    decision_tree_root = DecisionTreeNode("", config, network)

    xpansion = build_benders_decomposed_problem(decision_tree_root, database)
    assert xpansion.run()
    if (decomposed_solution := xpansion.solution) is not None:  # For mypy only
        assert decomposed_solution.overall_cost < 50.49e6
        assert decomposed_solution.investment_cost > 8.64e6
        assert decomposed_solution.candidates["Cand_Semi_p_max"] >= 197
        assert decomposed_solution.candidates["Cand_Peak_p_max"] >= 300
