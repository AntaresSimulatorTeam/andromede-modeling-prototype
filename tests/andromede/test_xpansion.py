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

from andromede.expression.expression import literal, param, port_field, var
from andromede.expression.indexing_structure import IndexingStructure
from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    CONSTANT,
    DEMAND_MODEL,
    GENERATOR_MODEL,
    NODE_BALANCE_MODEL,
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
    OptimizationProblem,
    OutputValues,
    TimeBlock,
    XpansionProblem,
    build_problem,
    build_xpansion_problem,
)
from andromede.study import (
    Component,
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    TimeScenarioIndex,
    TimeScenarioSeriesData,
    create_component,
)

CONSTANT = IndexingStructure(False, False)
FREE = IndexingStructure(True, True)

INVESTMENT = ProblemContext.investment
OPERATIONAL = ProblemContext.operational

XPANSION_MASTER = OptimizationProblem.Type.xpansion_master
XPANSION_SUBPBL = OptimizationProblem.Type.xpansion_subproblem
XPANSION_MERGED = OptimizationProblem.Type.xpansion_merged


@pytest.fixture
def thermal_candidate() -> Model:
    THERMAL_CANDIDATE = model(
        id="GEN",
        parameters=[
            float_parameter("op_cost", CONSTANT),
            float_parameter("invest_cost", CONSTANT, INVESTMENT),
        ],
        variables=[
            float_variable("generation", lower_bound=literal(0)),
            float_variable(
                "p_max",
                lower_bound=literal(0),
                upper_bound=literal(1000),
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
            )
        ],
        objective_operational_contribution=(param("op_cost") * var("generation"))
        .sum()
        .expec(),
        objective_investment_contribution=param("invest_cost") * var("p_max"),
    )
    return THERMAL_CANDIDATE


@pytest.fixture
def wind_cluster_candidate() -> Model:
    WIND_CLUSTER_CANDIDATE = model(
        id="WIND_CLUSTER",
        parameters=[
            float_parameter("op_cost", CONSTANT),
            float_parameter("invest_cost", CONSTANT, INVESTMENT),
            float_parameter("p_max_per_unit", CONSTANT, INVESTMENT),
        ],
        variables=[
            float_variable("generation", lower_bound=literal(0)),
            float_variable(
                "p_max",
                lower_bound=literal(0),
                structure=CONSTANT,
                context=INVESTMENT,
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
    return WIND_CLUSTER_CANDIDATE


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
def cluster_candidate(wind_cluster_candidate: Model) -> Component:
    cluster = create_component(model=wind_cluster_candidate, id="CLUSTER")
    return cluster


def test_generation_xpansion_single_time_step_single_scenario(
    generator: Component,
    candidate: Component,
) -> None:
    """
    Simple generation expansion problem on one node. One timestep, one scenario, one thermal cluster candidate.

    Demand = 300
    Generator : P_max : 200, Cost : 40
    Unsupplied energy : Cost : 1000

    -> 100 of unsupplied energy
    -> Total cost without investment = 200 * 40 + 100 * 1000 = 108000

    Candidate : Invest cost : 490 / MW, Prod cost : 10

    Optimal investment : 100 MW

    -> Optimal cost = 490 * 100 (investment) + 100 * 10 + 200 * 40 (production) = 58000

    """

    database = DataBase()
    database.add_data("D", "demand", ConstantData(300))

    database.add_data("G1", "p_max", ConstantData(200))
    database.add_data("G1", "cost", ConstantData(40))

    database.add_data("CAND", "op_cost", ConstantData(10))
    database.add_data("CAND", "invest_cost", ConstantData(490))

    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    node = Node(model=NODE_BALANCE_MODEL, id="N")
    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(generator)
    network.add_component(candidate)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(generator, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(candidate, "balance_port"), PortRef(node, "balance_port"))

    scenarios = 1
    problem = build_problem(
        network, database, TimeBlock(1, [0]), scenarios, problem_type=XPANSION_MERGED
    )
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 490 * 100 + 100 * 10 + 200 * 40

    output = OutputValues(problem)
    expected_output = OutputValues()
    expected_output.component("G1").var("generation").value = 200.0
    expected_output.component("CAND").var("generation").value = 100.0
    expected_output.component("CAND").var("p_max").value = 100.0

    assert output == expected_output, f"Output differs from expected: {output}"


def test_model_export_xpansion_single_time_step_single_scenario(
    generator: Component,
    candidate: Component,
    cluster_candidate: Component,
) -> None:
    """
    Same as the previous test, but only checking the MPS file generation for Bender's branching
    in Xpansion
    """

    database = DataBase()
    database.add_data("D", "demand", ConstantData(300))

    database.add_data("G1", "p_max", ConstantData(200))
    database.add_data("G1", "cost", ConstantData(40))

    database.add_data("CAND", "op_cost", ConstantData(10))
    database.add_data("CAND", "invest_cost", ConstantData(490))

    database.add_data("CLUSTER", "op_cost", ConstantData(5))
    database.add_data("CLUSTER", "invest_cost", ConstantData(495))
    database.add_data("CLUSTER", "p_max_per_unit", ConstantData(100))

    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    node = Node(model=NODE_BALANCE_MODEL, id="N")
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

    xpansion = build_xpansion_problem(network, database, TimeBlock(1, [0]), scenarios)

    assert any(
        "CAND_p_max_0_0" == solver_var.name and 0 == solver_var.column
        for solver_var in xpansion.master.context._solver_variables.values()
    )
    assert any(
        "CLUSTER_p_max_0_0" == solver_var.name and 1 == solver_var.column
        for solver_var in xpansion.master.context._solver_variables.values()
    )
    assert any(
        "CLUSTER_nb_units_0_0" == solver_var.name and not solver_var.is_in_objective
        for solver_var in xpansion.master.context._solver_variables.values()
    )

    assert any(
        "CAND_p_max_0_0" == solver_var.name and 2 == solver_var.column
        for solver_var in xpansion.subproblems[0].context._solver_variables.values()
    )
    assert any(
        "CLUSTER_p_max_0_0" == solver_var.name and 4 == solver_var.column
        for solver_var in xpansion.subproblems[0].context._solver_variables.values()
    )
    assert any(
        "CAND_generation_0_0" == solver_var.name
        for solver_var in xpansion.subproblems[0].context._solver_variables.values()
    )
    assert any(
        "CLUSTER_generation_0_0" == solver_var.name
        for solver_var in xpansion.subproblems[0].context._solver_variables.values()
    )

    xpansion.set_environment(is_debug=True)


def test_generation_xpansion_two_time_steps_two_scenarios(
    generator: Component,
    candidate: Component,
) -> None:
    """
    Same as previous example but with two timesteps and two scenarios, in order to test the correct instantiation of the objective function

    Demand = [300, 500] for scenario 1, [200, 400] for scenario 2
    Generator : P_max : 200, Cost : 40
    Unsupplied energy : Cost : 1000

    Equiprobable scenarios => Weights 0.5

    -> 300 MW of unsupplied energy at step 2 for scenario 1

    Candidate : Invest cost : 490 / MW, Prod cost : 10

    Optimal investment : 300 MW

    -> Optimal cost =       490 * 300                       (investment)
    (weights 0.5/scenario)  + 0.5 * 10 * 300                (scenario 1, step 1)
                            + 0.5 * (10 * 300 + 40 * 200)   (scenario 1, step 2)
                            + 0.5 * 10 * 200                (scenario 2, step 1)
                            + 0.5 * (10 * 300 + 40 * 100)   (scenario 2, step 2)

    """

    scenarios = 2
    horizon = 2
    time_block = TimeBlock(1, list(range(horizon)))

    data = {}
    data[TimeScenarioIndex(0, 0)] = 300
    data[TimeScenarioIndex(1, 0)] = 500
    data[TimeScenarioIndex(0, 1)] = 200
    data[TimeScenarioIndex(1, 1)] = 400

    demand_data = TimeScenarioSeriesData(time_scenario_series=data)

    database = DataBase()
    database.add_data("D", "demand", demand_data)

    database.add_data("G1", "p_max", ConstantData(200))
    database.add_data("G1", "cost", ConstantData(40))

    database.add_data("CAND", "op_cost", ConstantData(10))
    database.add_data("CAND", "invest_cost", ConstantData(490))

    demand = create_component(model=DEMAND_MODEL, id="D")

    node = Node(model=NODE_BALANCE_MODEL, id="N")
    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(generator)
    network.add_component(candidate)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(generator, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(candidate, "balance_port"), PortRef(node, "balance_port"))

    problem = build_problem(network, database, time_block, scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    # assert problem.solver.NumVariables() == 2 * scenarios * horizon + 1
    # assert (
    #     problem.solver.NumConstraints() == 3 * scenarios * horizon
    # )  # Flow balance, Max generation for each cluster
    assert problem.solver.Objective().Value() == 490 * 300 + 0.5 * (
        10 * 300 + 10 * 300 + 40 * 200
    ) + 0.5 * (10 * 200 + 10 * 300 + 40 * 100)

    output = OutputValues(problem)
    expected_output = OutputValues()
    expected_output.component("G1").var("generation").value = [[0, 200], [0, 100]]
    expected_output.component("CAND").var("generation").value = [[300, 300], [200, 300]]
    expected_output.component("CAND").var("p_max").value = 300.0

    assert output == expected_output, f"Output differs from expected: {output}"
