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

import numpy as np
import pytest

from andromede.libs.standard import (
    DEMAND_MODEL,
    GENERATOR_MODEL,
    NODE_WITH_SPILL_AND_ENS_MODEL,
)
from andromede.model.model import Model
from andromede.simulation import OutputValues, TimeBlock, build_problem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    TimeIndex,
    TimeSeriesData,
    create_component,
)
from tests.functional.libs.lib_hydro_heuristic import (
    HYDRO_MODEL,
    HYDRO_MODEL_WITH_TARGET,
)

weekly_generation = np.array(
    [
        1146984.0,
        1326912.0,
        1322812.0,
        1456577.0,
        1273755.0,
        1357279.0,
        1433275.0,
        1253238.99999999,
        881095.0,
        907328.0,
        842615.0,
        1125173.0,
        1177329.0,
        1413747.0,
        1454544.0,
        1657992.0,
        1925616.0,
        2210712.0,
        2513112.0,
        2944032.0,
        3540096.0,
        4211928.0,
        4882584.0,
        5425392.0,
        5689992.0,
        5731364.0,
        5715685.0,
        5783535.0,
        5556520.0,
        5230256.0,
        4856544.0,
        4485600.0,
        4125744.0,
        3782016.0,
        3447696.0,
        3113880.0,
        2801736.0,
        2549568.0,
        2350656.0,
        2162160.0,
        1981224.0,
        1839096.0,
        906893.99999983,
        564588.0,
        337915.0,
        508152.0,
        678530.0,
        898910.0,
        796024.0,
        1126580.0,
        1102748.0,
        1106144.0,
    ]
)

weekly_cost = [
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    724183000.0,
    830477200.0,
    820700000.0,
    798688600.0,
    746353200.0,
    712827000.0,
    675922900.0,
    648795900.0,
    621487200.0,
    602586700.0,
    552946500.0,
    521539800.0,
    466889400.0,
    398966900.0,
    325126200.0,
    262730100.0,
    201368500.0,
    137151300.0,
    135568200.0,
    133974500.0,
    98764000.0,
    142983800.0,
    147213300.0,
    191970400.0,
    237278400.0,
    281956800.0,
    320273700.0,
    351775900.0,
    386884500.0,
    417305400.0,
    442685300.0,
    480717100.0,
    502683700.0,
    524359800.0,
    541248700.0,
    664201200.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
    714000000.0,
]


def test_complete_year_as_one_block() -> None:
    """ """
    database, network = create_database_and_network(
        HYDRO_MODEL, return_to_initial_level=True
    )

    scenarios = 1
    problem = build_problem(
        network, database, TimeBlock(1, list(range(8760))), scenarios
    )
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == pytest.approx(27576585100)

    output = OutputValues(problem)
    generating = output.component("H").var("generating").value[0]  # type:ignore
    overflow = output.component("H").var("overflow").value[0]  # type:ignore
    production_1 = output.component("G1").var("generation").value[0]  # type:ignore
    production_2 = output.component("G2").var("generation").value[0]  # type:ignore
    production_3 = output.component("G3").var("generation").value[0]  # type:ignore
    unsupplied = output.component("1").var("unsupplied_energy").value[0]  # type:ignore
    for week in range(52):
        assert sum(
            [
                generating[t] + overflow[t]  # type:ignore
                for t in range(168 * week, 168 * (week + 1))
            ]
        ) == pytest.approx(weekly_generation[week])

        assert sum(
            [
                100 * production_1[t]  # type:ignore
                + 200 * production_2[t]  # type:ignore
                + 300 * production_3[t]  # type:ignore
                + 3000 * unsupplied[t]  # type:ignore
                for t in range(168 * week, 168 * (week + 1))
            ]
        ) == pytest.approx(weekly_cost[week])


def test_complete_year_as_weekly_blocks() -> None:
    """ """
    database, network = create_database_and_network(
        HYDRO_MODEL_WITH_TARGET, return_to_initial_level=False
    )

    capacity = 1e07
    initial_level = 0.445 * capacity

    scenarios = 1

    for week in range(52):
        database.add_data("H", "overall_target", ConstantData(weekly_generation[week]))
        database.add_data("H", "initial_level", ConstantData(initial_level))
        problem = build_problem(
            network,
            database,
            TimeBlock(1, list(range(168 * week, 168 * (week + 1)))),
            scenarios,
        )
        status = problem.solver.Solve()
        assert status == problem.solver.OPTIMAL
        assert problem.solver.Objective().Value() == pytest.approx(weekly_cost[week])

        output = OutputValues(problem)
        initial_level = output.component("H").var("level").value[0][-1]  # type:ignore


def create_database_and_network(
    hydro_model: Model,
    return_to_initial_level: bool,
) -> tuple[DataBase, Network]:
    capacity = 1e07
    initial_level = 0.445 * capacity
    demand_data = np.loadtxt(
        "tests/functional/data/hydro_with_rulecurves/load.txt", usecols=0
    )
    inflow_data = np.loadtxt(
        "tests/functional/data/hydro_with_rulecurves/mod.txt", usecols=0
    ).repeat(24)
    rule_curve_data = np.loadtxt(
        "tests/functional/data/hydro_with_rulecurves/reservoir.txt"
    ).repeat(24, axis=0)

    node = Node(model=NODE_WITH_SPILL_AND_ENS_MODEL, id="1")

    thermal_1 = create_component(
        model=GENERATOR_MODEL,
        id="G1",
    )

    thermal_2 = create_component(
        model=GENERATOR_MODEL,
        id="G2",
    )

    thermal_3 = create_component(
        model=GENERATOR_MODEL,
        id="G3",
    )

    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    hydro = create_component(model=hydro_model, id="H")

    database = DataBase()

    database.add_data("1", "spillage_cost", ConstantData(0))
    database.add_data("1", "ens_cost", ConstantData(3000))
    database.add_data(
        "D",
        "demand",
        TimeSeriesData({TimeIndex(t): demand_data[t] for t in range(8760)}),
    )

    database.add_data("G1", "p_max", ConstantData(42500))
    database.add_data("G1", "cost", ConstantData(100))
    database.add_data("G2", "p_max", ConstantData(12500))
    database.add_data("G2", "cost", ConstantData(200))
    database.add_data("G3", "p_max", ConstantData(7500))
    database.add_data("G3", "cost", ConstantData(300))

    database.add_data("H", "max_generating", ConstantData(50000))
    database.add_data("H", "min_generating", ConstantData(-50000))
    database.add_data("H", "capacity", ConstantData(capacity))
    database.add_data("H", "initial_level", ConstantData(initial_level))

    database.add_data(
        "H",
        "inflow",
        TimeSeriesData({TimeIndex(t): inflow_data[t] for t in range(8760)}),
    )

    database.add_data(
        "H",
        "lower_rule_curve",
        TimeSeriesData(
            {
                TimeIndex(i): rule_curve_data[(i - 1) % 8760][0] * capacity
                for i in range(8760)
            }
        ),
    )
    database.add_data(
        "H",
        "upper_rule_curve",
        TimeSeriesData(
            {
                TimeIndex(i): rule_curve_data[(i - 1) % 8760][2] * capacity
                for i in range(8760)
            }
        ),
    )

    if return_to_initial_level:
        database.add_data(
            "H",
            "max_epsilon",
            ConstantData(0),
        )
    else:
        database.add_data(
            "H",
            "max_epsilon",
            TimeSeriesData(
                {TimeIndex(i): capacity if i % 168 == 0 else 0 for i in range(8760)}
            ),
        )

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(thermal_1)
    network.add_component(thermal_2)
    network.add_component(thermal_3)
    network.add_component(hydro)
    network.connect(PortRef(node, "balance_port"), PortRef(demand, "balance_port"))
    network.connect(PortRef(node, "balance_port"), PortRef(thermal_1, "balance_port"))
    network.connect(PortRef(node, "balance_port"), PortRef(thermal_2, "balance_port"))
    network.connect(PortRef(node, "balance_port"), PortRef(thermal_3, "balance_port"))
    network.connect(PortRef(node, "balance_port"), PortRef(hydro, "balance_port"))
    return database, network