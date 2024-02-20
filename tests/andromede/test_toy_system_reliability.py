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
from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    CONSTANT,
    DEMAND_MODEL,
    TIME_AND_SCENARIO_FREE,
)
from andromede.model import model
from andromede.model.common import ProblemContext
from andromede.model.constraint import Constraint
from andromede.model.model import ModelPort, PortFieldDefinition, PortFieldId
from andromede.model.parameter import float_parameter
from andromede.model.variable import float_variable
from andromede.simulation.optimization import build_problem
from andromede.simulation.output_values import OutputValues
from andromede.simulation.time_block import TimeBlock
from andromede.simulation.xpansion import build_xpansion_problem
from andromede.study.data import (
    ConstantData,
    DataBase,
    ScenarioIndex,
    ScenarioSeriesData,
)
from andromede.study.network import Network, Node, PortRef, create_component
from andromede.utils import serialize


def test_model_export_xpansion_toy_reliability_system() -> None:
    """
    We describe a system with 4 nodes, on 1 timestep, 2 scenarios :


    |------- N1
    |
    N0 ----- N2
    |
    |------- N3

    On node 0, there is a generator with :
        - Initial P_max = 1
        - Prod cost = 1
        - Investment cost = 20

    On nodes N1, N2, N3, there is a demand that differ between scenarios :
        - On N1 : Demand1 = [1, 3]
        - On N2 : Demand2 = [3, 3]
        - On N3 : Demand3 = [0, 3]

    Over the whole system we have :
        - Spillage cost = 1
        - ENS cost = 10

    There are also transmission costs on lines :
        - On L01 : transmission cost = 2
        - On L02 : transmission cost = 1
        - On L03 : transmission cost = 3

    As the investment cost is higher than the ENS cost, adding 1MW of capacity would cost 20 to reduce ENS cost only by 10, hence an increased overall cost. Therefore the optimal investment is not to add any capacity beyond the existing one. Given the transmission cost, all flow will get to node 2.

    This use case is simple enough so that we can count the number of hours with ENS with respect to the investment. Then we could use this test to check the behavior of any heuristic that aims at reaching a given target of LOLE (not done here).

    We add 1 hour of ENS if there is at least 0.1 MWh of unsupplied energy, the "optimal" situation leads to 5h of ENS hours overall, hence 2.5h in expectation.

    Each invested capacity will first go to node 2, then to node 1 and finally to node 3 given the transmission costs.

    Hence we can deduce the number expected hours of ENS given the total capacity as follows  (invested capacity is total capacity - 1 as P_max = 1 initially):
        - 0 <= P_max <= 2.9 : 2.5h
        - 2.9 <= P_max <= 3.9 : 1.5h
        - 3.9 <= P_max <= 5.9 : 1h
        - 5.9 <= P_max <= 8.9 : 0.5h
        - 8.9 <= P_max : 0h

    """

    NODE_WITH_SPILL_AND_ENS = model(
        id="NODE_WITH_SPILL_AND_ENS",
        parameters=[float_parameter("spillage_cost"), float_parameter("ens_cost")],
        variables=[
            float_variable("NegativeUnsuppliedEnergy", lower_bound=literal(0)),
            float_variable("PositiveUnsuppliedEnergy", lower_bound=literal(0)),
        ],
        ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
        binding_constraints=[
            Constraint(
                name="Balance",
                expression=port_field("balance_port", "flow").sum_connections()
                == var("NegativeUnsuppliedEnergy") - var("PositiveUnsuppliedEnergy"),
            )
        ],
        objective_operational_contribution=(
            param("spillage_cost") * var("NegativeUnsuppliedEnergy")
            + param("ens_cost") * var("PositiveUnsuppliedEnergy")
        )
        .sum()
        .expec(),
    )

    LINK_WITH_TRANSMISSION_COST = model(
        id="LINK",
        parameters=[
            float_parameter("f_max", TIME_AND_SCENARIO_FREE),
            float_parameter("transmission_cost", CONSTANT),
        ],
        variables=[
            float_variable("flow", lower_bound=literal(0), upper_bound=param("f_max"))
        ],
        ports=[
            ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port_from"),
            ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port_to"),
        ],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId("balance_port_from", "flow"),
                definition=-var("flow"),
            ),
            PortFieldDefinition(
                port_field=PortFieldId("balance_port_to", "flow"),
                definition=var("flow"),
            ),
        ],
        objective_operational_contribution=(param("transmission_cost") * var("flow"))
        .sum()
        .expec(),
    )

    INVESTMENT = ProblemContext.investment

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
                name="Max generation",
                expression=var("generation") <= literal(1) + var("p_max"),
            )
        ],
        objective_operational_contribution=(param("op_cost") * var("generation"))
        .sum()
        .expec(),
        objective_investment_contribution=param("invest_cost") * var("p_max"),
    )

    database = DataBase()
    database.add_data(
        "D1", "demand", ScenarioSeriesData({ScenarioIndex(0): 1, ScenarioIndex(1): 3})
    )
    database.add_data(
        "D2", "demand", ScenarioSeriesData({ScenarioIndex(0): 3, ScenarioIndex(1): 3})
    )
    database.add_data(
        "D3", "demand", ScenarioSeriesData({ScenarioIndex(0): 0, ScenarioIndex(1): 3})
    )
    database.add_data("G", "op_cost", ConstantData(1))
    database.add_data("G", "invest_cost", ConstantData(20))

    database.add_data("L01", "f_max", ConstantData(100))
    database.add_data("L02", "f_max", ConstantData(100))
    database.add_data("L03", "f_max", ConstantData(100))

    database.add_data("L01", "transmission_cost", ConstantData(2))
    database.add_data("L02", "transmission_cost", ConstantData(1))
    database.add_data("L03", "transmission_cost", ConstantData(3))

    database.add_data("N0", "spillage_cost", ConstantData(1))
    database.add_data("N0", "ens_cost", ConstantData(10))
    database.add_data("N1", "spillage_cost", ConstantData(1))
    database.add_data("N1", "ens_cost", ConstantData(10))
    database.add_data("N2", "spillage_cost", ConstantData(1))
    database.add_data("N2", "ens_cost", ConstantData(10))
    database.add_data("N3", "spillage_cost", ConstantData(1))
    database.add_data("N3", "ens_cost", ConstantData(10))

    demand1 = create_component(model=DEMAND_MODEL, id="D1")
    demand2 = create_component(model=DEMAND_MODEL, id="D2")
    demand3 = create_component(model=DEMAND_MODEL, id="D3")

    link01 = create_component(model=LINK_WITH_TRANSMISSION_COST, id="L01")
    link02 = create_component(model=LINK_WITH_TRANSMISSION_COST, id="L02")
    link03 = create_component(model=LINK_WITH_TRANSMISSION_COST, id="L03")

    generator = create_component(model=THERMAL_CANDIDATE, id="G")

    node0 = Node(model=NODE_WITH_SPILL_AND_ENS, id="N0")
    node1 = Node(model=NODE_WITH_SPILL_AND_ENS, id="N1")
    node2 = Node(model=NODE_WITH_SPILL_AND_ENS, id="N2")
    node3 = Node(model=NODE_WITH_SPILL_AND_ENS, id="N3")

    network = Network("test")
    network.add_node(node0)
    network.add_node(node1)
    network.add_node(node2)
    network.add_node(node3)
    network.add_component(link01)
    network.add_component(link02)
    network.add_component(link03)
    network.add_component(demand1)
    network.add_component(demand2)
    network.add_component(demand3)
    network.add_component(generator)

    network.connect(
        PortRef(link01, "balance_port_from"), PortRef(node0, "balance_port")
    )
    network.connect(PortRef(link01, "balance_port_to"), PortRef(node1, "balance_port"))
    network.connect(
        PortRef(link02, "balance_port_from"), PortRef(node0, "balance_port")
    )
    network.connect(PortRef(link02, "balance_port_to"), PortRef(node2, "balance_port"))
    network.connect(
        PortRef(link03, "balance_port_from"), PortRef(node0, "balance_port")
    )
    network.connect(PortRef(link03, "balance_port_to"), PortRef(node3, "balance_port"))
    network.connect(PortRef(demand1, "balance_port"), PortRef(node1, "balance_port"))
    network.connect(PortRef(demand2, "balance_port"), PortRef(node2, "balance_port"))
    network.connect(PortRef(demand3, "balance_port"), PortRef(node3, "balance_port"))
    network.connect(PortRef(generator, "balance_port"), PortRef(node0, "balance_port"))

    scenarios = 2

    xpansion_problem = build_xpansion_problem(
        network, database, TimeBlock(1, [0]), scenarios
    )
    xpansion_problem.set_environment(is_debug=True)

    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)

    serialize("merged.mps", problem.export_as_mps(), "outputs/lp")
    serialize("merged.lp", problem.export_as_lp(), "outputs/lp")

    status = problem.solver.Solve()

    output = OutputValues(problem)

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == pytest.approx(
        1 + 0.5 * 1 + 0.5 * 10 * 3 + 0.5 * 1 + 0.5 * 10 * 8, rel=1e-10
    )

    expected_output = OutputValues()
    # TODO : Do we need to overload == operator to compare lists of float
    expected_output.component("N0").var("NegativeUnsuppliedEnergy").value = [
        [0.0],
        [0.0],
    ]
    expected_output.component("N0").var("PositiveUnsuppliedEnergy").value = [
        [0.0],
        [0.0],
    ]
    expected_output.component("N1").var("NegativeUnsuppliedEnergy").value = [
        [0.0],
        [0.0],
    ]
    expected_output.component("N1").var("PositiveUnsuppliedEnergy").value = [
        [1.0],
        [3.0],
    ]
    expected_output.component("N2").var("NegativeUnsuppliedEnergy").value = [
        [0.0],
        [0.0],
    ]
    expected_output.component("N2").var("PositiveUnsuppliedEnergy").value = [
        [2.0],
        [2.0],
    ]
    expected_output.component("N3").var("NegativeUnsuppliedEnergy").value = [
        [0.0],
        [0.0],
    ]
    expected_output.component("N3").var("PositiveUnsuppliedEnergy").value = [
        [0.0],
        [3.0],
    ]

    expected_output.component("L01").var("flow").value = [[0.0], [0.0]]
    expected_output.component("L02").var("flow").value = [[1.0], [1.0]]
    expected_output.component("L03").var("flow").value = [[0.0], [0.0]]

    expected_output.component("G").var("generation").value = [[1.0], [1.0]]
    expected_output.component("G").var("p_max").value = 0

    assert output == expected_output, f"Output differs from expected: {output}"
