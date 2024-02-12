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

from andromede.expression import literal, param, var
from andromede.expression.indexing_structure import IndexingStructure
from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    DEMAND_MODEL,
    GENERATOR_MODEL,
    GENERATOR_MODEL_WITH_PMIN,
    LINK_MODEL,
    NODE_BALANCE_MODEL,
    SHORT_TERM_STORAGE_SIMPLE,
    SPILLAGE_MODEL,
    THERMAL_CLUSTER_MODEL_HD,
    UNSUPPLIED_ENERGY_MODEL,
)
from andromede.model import Model, ModelPort, float_parameter, float_variable, model
from andromede.model.model import PortFieldDefinition, PortFieldId
from andromede.simulation import (
    BlockBorderManagement,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    TimeScenarioIndex,
    TimeScenarioSeriesData,
    create_component,
)


def test_network() -> None:
    network = Network("test")
    assert network.id == "test"
    assert list(network.nodes) == []
    assert list(network.components) == []
    assert list(network.all_components) == []
    assert list(network.connections) == []

    with pytest.raises(KeyError):
        network.get_node("N")

    N1 = Node(model=NODE_BALANCE_MODEL, id="N1")
    N2 = Node(model=NODE_BALANCE_MODEL, id="N2")
    network.add_node(N1)
    network.add_node(N2)
    assert list(network.nodes) == [N1, N2]
    assert network.get_node(N1.id) == N1
    assert network.get_component("N1") == Node(model=NODE_BALANCE_MODEL, id="N1")
    with pytest.raises(KeyError):
        network.get_component("unknown")


def test_basic_balance() -> None:
    """
    Balance on one node with one fixed demand and one generation, on 1 timestep.
    """

    database = DataBase()
    database.add_data("D", "demand", ConstantData(100))

    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(30))

    node = Node(model=NODE_BALANCE_MODEL, id="N")
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    gen = create_component(
        model=GENERATOR_MODEL,
        id="G",
    )

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000


def test_link() -> None:
    """
    Balance on one node with one fixed demand and one generation, on 1 timestep.
    """

    database = DataBase()
    database.add_data("D", "demand", ConstantData(100))

    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(35))

    database.add_data("L", "f_max", ConstantData(150))

    node1 = Node(model=NODE_BALANCE_MODEL, id="1")
    node2 = Node(model=NODE_BALANCE_MODEL, id="2")
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )
    gen = create_component(
        model=GENERATOR_MODEL,
        id="G",
    )
    link = create_component(
        model=LINK_MODEL,
        id="L",
    )

    network = Network("test")
    network.add_node(node1)
    network.add_node(node2)
    network.add_component(demand)
    network.add_component(gen)
    network.add_component(link)
    network.connect(PortRef(demand, "balance_port"), PortRef(node1, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node2, "balance_port"))
    network.connect(PortRef(link, "balance_port_from"), PortRef(node1, "balance_port"))
    network.connect(PortRef(link, "balance_port_to"), PortRef(node2, "balance_port"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3500

    for variable in problem.solver.variables():
        if "balance_port_from" in variable.name():
            assert variable.solution_value() == 100
        if "balance_port_to" in variable.name():
            assert variable.solution_value() == -100


def test_stacking_generation() -> None:
    """
    Balance on one node with one fixed demand and 2 generations with different costs, on 1 timestep.
    """

    database = DataBase()
    database.add_data("D", "demand", ConstantData(150))

    database.add_data("G1", "p_max", ConstantData(100))
    database.add_data("G1", "cost", ConstantData(30))

    database.add_data("G2", "p_max", ConstantData(100))
    database.add_data("G2", "cost", ConstantData(50))

    node1 = Node(model=NODE_BALANCE_MODEL, id="1")

    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    gen1 = create_component(
        model=GENERATOR_MODEL,
        id="G1",
    )

    gen2 = create_component(
        model=GENERATOR_MODEL,
        id="G2",
    )

    network = Network("test")
    network.add_node(node1)
    network.add_component(demand)
    network.add_component(gen1)
    network.add_component(gen2)
    network.connect(PortRef(demand, "balance_port"), PortRef(node1, "balance_port"))
    network.connect(PortRef(gen1, "balance_port"), PortRef(node1, "balance_port"))
    network.connect(PortRef(gen2, "balance_port"), PortRef(node1, "balance_port"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 30 * 100 + 50 * 50


def test_timeseries() -> None:
    """
    Basic case with 2 timesteps, where the demand is 100 on first timestep and 50 on second timestep.
    """

    database = DataBase()

    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(30))

    demand_data = TimeScenarioSeriesData(
        {TimeScenarioIndex(0, 0): 100, TimeScenarioIndex(1, 0): 50}
    )
    database.add_data("D", "demand", demand_data)

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    gen = create_component(
        model=GENERATOR_MODEL,
        id="G",
    )

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))

    time_block = TimeBlock(1, [0, 1])
    scenarios = 1

    problem = build_problem(network, database, time_block, scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 100 * 30 + 50 * 30


def create_one_node_network(generator_model: Model) -> Network:
    node = Node(model=NODE_BALANCE_MODEL, id="1")
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    gen = create_component(
        model=generator_model,
        id="G",
    )

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))
    return network


def create_simple_database(max_generation: float = 100) -> DataBase:
    database = DataBase()
    database.add_data("D", "demand", ConstantData(100))

    database.add_data("G", "p_max", ConstantData(max_generation))
    database.add_data("G", "cost", ConstantData(30))
    return database


def test_variable_bound() -> None:
    """
    Create a network with one node, one demand and one generator on this node.
    Demand is constant 100, cost of generation is constant 30.
    Max generation can be chosen to make it infeasible or not.
    Variation of generator model using variable bound instead of constraint.
    """

    generator_model = model(
        id="GEN",
        parameters=[
            float_parameter("p_max", IndexingStructure(False, False)),
            float_parameter("cost", IndexingStructure(False, False)),
        ],
        variables=[
            float_variable(
                "generation",
                lower_bound=literal(0),
                upper_bound=param("p_max"),
            )
        ],
        ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId("balance_port", "flow"),
                definition=var("generation"),
            )
        ],
        objective_contribution=(param("cost") * var("generation")).sum().expec(),
    )

    network = create_one_node_network(generator_model)
    database = create_simple_database(max_generation=200)
    problem = build_problem(network, database, TimeBlock(1, [0]), 1)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000

    network = create_one_node_network(generator_model)
    database = create_simple_database(max_generation=80)
    problem = build_problem(network, database, TimeBlock(1, [0]), 1)
    status = problem.solver.Solve()
    assert status == problem.solver.INFEASIBLE  # Infeasible


def test_spillage() -> None:
    """
    Balance on one node with one fixed demand and 1 generation higher than demand and 1 timestep .
    """

    database = DataBase()
    database.add_data("D", "demand", ConstantData(150))
    database.add_data("S", "cost", ConstantData(10))

    database.add_data("G1", "p_max", ConstantData(300))
    database.add_data("G1", "p_min", ConstantData(200))
    database.add_data("G1", "cost", ConstantData(30))

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    spillage = create_component(model=SPILLAGE_MODEL, id="S")
    demand = create_component(model=DEMAND_MODEL, id="D")

    gen1 = create_component(
        model=GENERATOR_MODEL_WITH_PMIN,
        id="G1",
    )

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen1)
    network.add_component(spillage)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen1, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(spillage, "balance_port"), PortRef(node, "balance_port"))

    problem = build_problem(network, database, TimeBlock(0, [1]), 1)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 30 * 200 + 50 * 10


def test_min_up_down_times() -> None:
    """
    Model on 3 time steps with one thermal generation and one demand on a single node.
        - Demand is the following time series : [500 MW, 0, 0]
        - Thermal generation is characterized with:
            - P_min = 100 MW
            - P_max = 500 MW
            - Min up/down time = 3
            - Generation cost = 100€ / MWh
        - Unsupplied energy = 3000 €/MWh
        - Spillage = 10 €/MWh

    The optimal solution consists is turning on the thermal plant, which must then stay on for the 3 timesteps and producing [500, 100, 100] to satisfy P_min constraints.

    The optimal cost is then :
          500 x 100 (prod step 1)
        + 100 x 100 (prod step 2)
        + 100 x 100 (prod step 3)
        + 100 x 10 (spillage step 2)
        + 100 x 10 (spillage step 3)
        = 72 000
    """

    database = DataBase()

    database.add_data("G", "p_max", ConstantData(500))
    database.add_data("G", "p_min", ConstantData(100))
    database.add_data("G", "cost", ConstantData(100))
    database.add_data("G", "d_min_up", ConstantData(3))
    database.add_data("G", "d_min_down", ConstantData(3))
    database.add_data("G", "nb_units_max", ConstantData(1))
    database.add_data("G", "nb_failures", ConstantData(0))

    database.add_data("U", "cost", ConstantData(3000))
    database.add_data("S", "cost", ConstantData(10))

    demand_data = TimeScenarioSeriesData(
        {
            TimeScenarioIndex(0, 0): 500,
            TimeScenarioIndex(1, 0): 0,
            TimeScenarioIndex(2, 0): 0,
        }
    )
    database.add_data("D", "demand", demand_data)

    time_block = TimeBlock(1, [0, 1, 2])
    scenarios = 1

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    demand = create_component(model=DEMAND_MODEL, id="D")

    gen = create_component(model=THERMAL_CLUSTER_MODEL_HD, id="G")

    spillage = create_component(model=SPILLAGE_MODEL, id="S")

    unsupplied_energy = create_component(model=UNSUPPLIED_ENERGY_MODEL, id="U")

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.add_component(spillage)
    network.add_component(unsupplied_energy)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(spillage, "balance_port"), PortRef(node, "balance_port"))
    network.connect(
        PortRef(unsupplied_energy, "balance_port"), PortRef(node, "balance_port")
    )

    border_management = BlockBorderManagement.CYCLE

    problem = build_problem(network, database, time_block, scenarios, border_management)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 72000

    output = OutputValues(problem)
    expected_output = OutputValues()
    expected_output.component("G").var("generation").value = [[500.0, 100.0, 100.0]]
    expected_output.component("G").var("nb_on").value = [[1.0, 1.0, 1.0]]
    expected_output.component("G").var("nb_start").value = [[-0.0, 0.0, 0.0]]
    expected_output.component("G").var("nb_stop").value = [[0.0, 0.0, 0.0]]

    expected_output.component("S").var("spillage").value = [[0.0, 100.0, 100.0]]
    expected_output.component("U").var("unsupplied_energy").value = [[0.0, 0.0, 0.0]]

    # TODO this test should pass with the next port implementation
    # assert output == expected_output, f"Output differs from expected: {output}"

    print(f"Variables values: {output}")


def generate_data(
    efficiency: float, horizon: int, scenarios: int
) -> TimeScenarioSeriesData:
    data = {}
    for scenario in range(scenarios):
        for absolute_timestep in range(horizon):
            if absolute_timestep == 0:
                data[TimeScenarioIndex(absolute_timestep, scenario)] = -18
            else:
                data[TimeScenarioIndex(absolute_timestep, scenario)] = 2 * efficiency
    return TimeScenarioSeriesData(time_scenario_series=data)


def short_term_storage_base(efficiency: float, horizon: int) -> None:
    # 18 produced in the 1st time-step, then consumed 2 * efficiency in the rest
    time_blocks = [TimeBlock(0, list(range(horizon)))]
    scenarios = 1
    database = DataBase()

    database.add_data("D", "demand", generate_data(efficiency, horizon, scenarios))

    database.add_data("U", "cost", ConstantData(10))
    database.add_data("S", "cost", ConstantData(1))

    database.add_data("STS1", "p_max_injection", ConstantData(100))
    database.add_data("STS1", "p_max_withdrawal", ConstantData(50))
    database.add_data("STS1", "level_min", ConstantData(0))
    database.add_data("STS1", "level_max", ConstantData(1000))
    database.add_data("STS1", "inflows", ConstantData(0))
    database.add_data("STS1", "efficiency", ConstantData(efficiency))

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    spillage = create_component(model=SPILLAGE_MODEL, id="S")

    unsupplied = create_component(model=UNSUPPLIED_ENERGY_MODEL, id="U")

    demand = create_component(model=DEMAND_MODEL, id="D")

    short_term_storage = create_component(
        model=SHORT_TERM_STORAGE_SIMPLE,
        id="STS1",
    )

    network = Network("test")
    network.add_node(node)
    for component in [demand, short_term_storage, spillage, unsupplied]:
        network.add_component(component)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(
        PortRef(short_term_storage, "balance_port"), PortRef(node, "balance_port")
    )
    network.connect(PortRef(spillage, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(unsupplied, "balance_port"), PortRef(node, "balance_port"))

    border_management = BlockBorderManagement.CYCLE
    problem = build_problem(
        network, database, time_blocks[0], scenarios, border_management
    )
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL

    # The short-term storage should satisfy the load
    # No spillage / unsupplied energy is expected
    assert problem.solver.Objective().Value() == 0

    count_variables = 0
    for variable in problem.solver.variables():
        if "injection" in variable.name():
            count_variables += 1
            assert 0 <= variable.solution_value() <= 100
        elif "withdrawal" in variable.name():
            count_variables += 1
            assert 0 <= variable.solution_value() <= 50
        elif "level" in variable.name():
            count_variables += 1
            assert 0 <= variable.solution_value() <= 1000
    assert count_variables == 3 * horizon


def test_short_test_horizon_10() -> None:
    short_term_storage_base(efficiency=0.8, horizon=10)


def test_short_test_horizon_5() -> None:
    short_term_storage_base(efficiency=0.2, horizon=5)
