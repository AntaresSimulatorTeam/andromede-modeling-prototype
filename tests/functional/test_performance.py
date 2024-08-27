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

from andromede.expression.expression import param
from andromede.expression.indexing_structure import RowIndex
from andromede.expression.linear_expression import literal, var, wrap_in_linear_expr
from andromede.libs.standard import (
    DEMAND_MODEL,
    GENERATOR_MODEL,
    GENERATOR_MODEL_WITH_STORAGE,
    NODE_BALANCE_MODEL,
)
from andromede.simulation.optimization import build_problem
from andromede.simulation.time_block import TimeBlock
from andromede.study.data import ConstantData, DataBase
from andromede.study.network import Network, Node, PortRef, create_component
from tests.unittests.test_utils import generate_scalar_matrix_data
from tests.utils import EvaluationContext


def test_large_number_of_parameters_sum() -> None:
    """
    Test performance when the problem involves an expression with a high number of terms.

    This test pass with 476 terms but fails with 477 locally due to recursion depth, and even less terms are possible with Jenkins...
    """
    nb_terms = 500

    parameters_value = {}
    for i in range(1, nb_terms):
        parameters_value[f"cost_{i}"] = 1 / i

    # Still the recursion depth error with parameters
    with pytest.raises(RecursionError, match="maximum recursion depth exceeded"):
        expr = sum(wrap_in_linear_expr(param(f"cost_{i}")) for i in range(1, nb_terms))
        expr.evaluate(EvaluationContext(parameters=parameters_value), RowIndex(0, 0))


def test_large_number_of_identical_parameters_sum() -> None:
    """
    With identical parameters sum, a simplification is performed online to avoid the recursivity.
    """
    nb_terms = 500

    parameters_value = {"cost": 1.0}

    # Still the recursion depth error with parameters
    # with pytest.raises(RecursionError, match="maximum recursion depth exceeded"):
    expr = sum(wrap_in_linear_expr(param("cost")) for _ in range(nb_terms))
    assert (
        expr.evaluate(EvaluationContext(parameters=parameters_value), RowIndex(0, 0))
        == nb_terms
    )


def test_large_number_of_literal_sum() -> None:
    """
    Literal sums are computed online to avoid recursivity
    """
    nb_terms = 500

    # # Still the recursion depth error with parameters
    # with pytest.raises(RecursionError, match="maximum recursion depth exceeded"):
    expr = sum(wrap_in_linear_expr(literal(1)) for _ in range(nb_terms))
    assert expr.evaluate(EvaluationContext(), RowIndex(0, 0)) == nb_terms


def test_large_number_of_variables_sum() -> None:
    """
    Test performance when the problem involves an expression with a high number of terms. No problem when there is a large number of variables as this is derecusified.
    """
    nb_terms = 500

    variables_value = {}
    for i in range(1, nb_terms):
        variables_value[f"cost_{i}"] = 1 / i

    expr = sum(var(f"cost_{i}") for i in range(1, nb_terms))
    assert expr.evaluate(
        EvaluationContext(variables=variables_value), RowIndex(0, 0)
    ) == sum(1 / i for i in range(1, nb_terms))


def test_large_sum_of_port_connections() -> None:
    """
    Test performance when the problem involves a model where several generators are connected to a node.

    This test pass with 470 terms but fails with 471 locally due to recursion depth,
    and possibly even less terms are possible with Jenkins...
    """
    nb_generators = 500

    time_block = TimeBlock(0, [0])
    scenarios = 1

    database = DataBase()
    database.add_data("D", "demand", ConstantData(nb_generators))

    for gen_id in range(nb_generators):
        database.add_data(f"G_{gen_id}", "p_max", ConstantData(1))
        database.add_data(f"G_{gen_id}", "cost", ConstantData(5))

    node = Node(model=NODE_BALANCE_MODEL, id="N")
    demand = create_component(model=DEMAND_MODEL, id="D")
    generators = [
        create_component(model=GENERATOR_MODEL, id=f"G_{gen_id}")
        for gen_id in range(nb_generators)
    ]

    network = Network("test")
    network.add_node(node)

    network.add_component(demand)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))

    for gen_id in range(nb_generators):
        network.add_component(generators[gen_id])
        network.connect(
            PortRef(generators[gen_id], "balance_port"), PortRef(node, "balance_port")
        )

    # Raised recursion error with previous implementation
    problem = build_problem(network, database, time_block, scenarios)

    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 5 * nb_generators


def test_basic_balance_on_whole_year() -> None:
    """
    Balance on one node with one fixed demand and one generation, on 8760 timestep.
    """

    scenarios = 1
    horizon = 8760
    time_block = TimeBlock(1, list(range(horizon)))

    database = DataBase()
    database.add_data(
        "D", "demand", generate_scalar_matrix_data(100, horizon, scenarios)
    )

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
    assert problem.solver.Objective().Value() == 30 * 100 * horizon


def test_basic_balance_on_whole_year_with_large_sum() -> None:
    """
    Balance on one node with one fixed demand and one generation with storage, on 8760 timestep.
    """

    scenarios = 1
    horizon = 8760
    time_block = TimeBlock(1, list(range(horizon)))

    database = DataBase()
    database.add_data(
        "D", "demand", generate_scalar_matrix_data(100, horizon, scenarios)
    )

    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(30))
    database.add_data("G", "full_storage", ConstantData(100 * horizon))

    node = Node(model=NODE_BALANCE_MODEL, id="N")
    demand = create_component(model=DEMAND_MODEL, id="D")
    gen = create_component(
        model=GENERATOR_MODEL_WITH_STORAGE, id="G"
    )  # Limits the total generation inside a TimeBlock

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))

    problem = build_problem(network, database, time_block, scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 30 * 100 * horizon
