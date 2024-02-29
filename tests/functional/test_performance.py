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

from andromede.expression.expression import literal, param
from andromede.expression.indexing_structure import IndexingStructure
from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    DEMAND_MODEL,
    GENERATOR_MODEL,
    NODE_BALANCE_MODEL,
)
from andromede.model import ModelPort, float_parameter, model
from andromede.simulation import TimeBlock, build_problem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    create_component,
)
from tests.unittests.test_utils import generate_data


def test_large_sum_with_loop() -> None:
    """
    Test performance when the problem involves an expression with a high number of terms. Here the objective function is the sum over nb_terms terms.
    """

    # This test pass with 476 terms but fails with 477 locally due to recursion depth, and even less terms are possible with Jenkins...
    nb_terms = 100

    time_blocks = [TimeBlock(0, [0])]
    scenarios = 1
    database = DataBase()

    for i in range(1, nb_terms):
        database.add_data("simple_cost", f"cost_{i}", ConstantData(1 / i))

    SIMPLE_COST_MODEL = model(
        id="SIMPLE_COST",
        parameters=[
            float_parameter(f"cost_{i}", IndexingStructure(False, False))
            for i in range(1, nb_terms)
        ],
        objective_operational_contribution=sum(
            [param(f"cost_{i}") for i in range(1, nb_terms)]
        ),
    )

    network = Network("test")

    # for i in range(1, nb_terms + 1):
    cost_model = create_component(model=SIMPLE_COST_MODEL, id="simple_cost")
    network.add_component(cost_model)

    problem = build_problem(network, database, time_blocks[0], scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == sum(
        [1 / i for i in range(1, nb_terms)]
    )


def test_large_sum_outside_model() -> None:
    """
    Test performance when the problem involves an expression with a high number of terms. Here the objective function is the sum over nb_terms terms.
    """

    nb_terms = 10000

    time_blocks = [TimeBlock(0, [0])]
    scenarios = 1
    database = DataBase()

    obj_coeff = sum([1 / i for i in range(1, nb_terms)])

    SIMPLE_COST_MODEL = model(
        id="SIMPLE_COST",
        parameters=[],
        objective_operational_contribution=literal(obj_coeff),
    )

    network = Network("test")

    # for i in range(1, nb_terms + 1):
    simple_model = create_component(
        model=SIMPLE_COST_MODEL,
        id="simple_cost",
    )
    network.add_component(simple_model)

    problem = build_problem(network, database, time_blocks[0], scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == sum(
        [1 / i for i in range(1, nb_terms)]
    )


def test_basic_balance_on_whole_year() -> None:
    """
    Balance on one node with one fixed demand and one generation, on 8760 timestep.
    """

    scenarios = 1
    horizon = 8760
    time_block = TimeBlock(1, list(range(horizon)))

    database = DataBase()
    database.add_data("D", "demand", generate_data(100, horizon, scenarios))

    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(30))

    node = Node(model=NODE_BALANCE_MODEL, id="N")
    demand = create_component(model=DEMAND_MODEL, id="D")

    gen = create_component(model=GENERATOR_MODEL, id="G")

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))

    problem = build_problem(network, database, time_block, scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000 * horizon
