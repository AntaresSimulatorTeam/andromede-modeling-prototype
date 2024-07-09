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

from typing import List

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pytest

from andromede.hydro_heuristic.data import (
    calculate_weekly_target,
    get_number_of_days_in_month,
    update_generation_target,
)
from andromede.hydro_heuristic.problem import optimize_target
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

from pathlib import Path

optimal_generation = np.array(
    [
        1146984.0,
        1326912.0,
        1207317.3333333295,
        196577.0,
        13755.000000000031,
        97279.00000000003,
        173275.00000000006,
        44154.00000000003,
        203481.0,
        180828.0,
        97496.45833333323,
        118595.75000000009,
        9385.416666666644,
        148124.83333333334,
        45748.208333333285,
        45425.291666666686,
        118939.95833333323,
        82705.04166666673,
        69633.70833333346,
        74245.00000000009,
        112461.00000000012,
        190215.25000000017,
        144761.83333333352,
        179611.7500000003,
        -78495.00000000006,
        -52954.000000000044,
        -84570.00000000007,
        -368825.0,
        -153642.00000000012,
        -437611.00000000006,
        -363752.0000000001,
        -281616.00000000006,
        -194688.00000000012,
        -155247.00000000012,
        -174545.00000000017,
        -157275.00000000006,
        -165210.00000000012,
        -163579.00000000012,
        17826.99999999997,
        48996.99999999994,
        84821.99999999991,
        111582.99999999997,
        408905.99999999994,
        564588.0,
        337914.99999999994,
        508152.0,
        -256906.83333342522,
        -361090.0,
        -463975.99999999994,
        -133419.99999999997,
        552651.0,
        670764.0,
    ]
)

expected_monthly_generation = [
    143339.17635433562,
    448143.8236456645,
    392228.0,
    0.0,
    0.0,
    0.0,
    0.0,
    283540.0,
    880464.8715492995,
    972585.5404387095,
    987207.2977588804,
    1183898.2902531116,
]

expected_weekly_target = [
    30219.22973453103,
    32189.06192005993,
    32090.851046477324,
    33776.2766893666,
    72029.72533763104,
    112192.22152202608,
    115734.09776498083,
    110161.39372895012,
    103880.17373520866,
    92151.52451197282,
    87515.61080253527,
    87384.7023261077,
    74386.13088015263,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    0.0,
    51468.71296816808,
    63986.14580114127,
    65689.2387701995,
    123439.9024604901,
    207457.9600766448,
    203081.78857398863,
    204202.69822189954,
    244678.42467676676,
    202285.23332789773,
    205663.19866574876,
    209006.91980595692,
    235349.51827916596,
    239300.03230287944,
    210644.55183860307,
    223486.28722687624,
    239229.20488122758,
    250128.32254601712,
    215110.61133805048,
    245745.34147894385,
    310397.5946960565,
    320338.89372197405,
]


def test_complete_year_as_one_block() -> None:
    """ """
    database, network = create_database_and_network(
        HYDRO_MODEL, return_to_initial_level=True
    )

    scenarios = 1
    problem = build_problem(
        network, database, TimeBlock(1, list(range(8736))), scenarios
    )
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == pytest.approx(55507683900)

    output = OutputValues(problem)
    generating = output.component("H").var("generating").value[0]  # type:ignore
    overflow = output.component("H").var("overflow").value[0]  # type:ignore
    assert output.component("H").var("level").value[0][  # type:ignore
        -1
    ] == pytest.approx(0.445 * 1e7)
    for week in range(52):
        assert sum(
            [
                generating[t] + overflow[t]  # type:ignore
                for t in range(168 * week, 168 * (week + 1))
            ]
        ) == pytest.approx(optimal_generation[week])


def test_hydro_heuristic() -> None:
    """ """
    scenarios = 1
    intermonthly_breakdown = 3
    interdaily_breakdown = 3
    folder_name = "hydro_with_large_load"

    capacity = 1e7

    for scenario in range(scenarios):
        initial_level = 0.445 * capacity

        initial_level, status, _, monthly_generation = optimize_target(
            intermonthly_breakdown,
            folder_name,
            capacity,
            scenario,
            initial_level,
            horizon="monthly",
            timesteps=list(range(12)),
            total_target=None,
        )

        assert status == pywraplp.Solver.OPTIMAL
        assert monthly_generation == expected_monthly_generation

        all_daily_generation: List[float] = []
        day_in_year = 0

        for month in range(12):
            number_day_month = get_number_of_days_in_month(month)

            (
                initial_level,
                status,
                obj,
                daily_generation,
            ) = optimize_target(
                interdaily_breakdown,
                folder_name,
                capacity,
                scenario,
                initial_level,
                horizon="daily",
                timesteps=list(range(day_in_year, day_in_year + number_day_month)),
                total_target=monthly_generation[month],
            )

            assert status == pywraplp.Solver.OPTIMAL

            all_daily_generation = update_generation_target(
                all_daily_generation, daily_generation
            )
            day_in_year += number_day_month

        # Calcul des cibles hebdomadaires
        weekly_target = calculate_weekly_target(
            all_daily_generation,
        )

        # Vérification des valeurs trouvées
        assert weekly_target == expected_weekly_target


def test_complete_year_as_weekly_blocks_with_hydro_heuristic() -> None:
    """ """
    database, network = create_database_and_network(
        HYDRO_MODEL_WITH_TARGET, return_to_initial_level=False
    )

    capacity = 1e07
    initial_level = 0.445 * capacity

    total_cost = 0

    scenarios = 1

    for week in range(52):
        database.add_data(
            "H", "overall_target", ConstantData(expected_weekly_target[week])
        )
        database.add_data("H", "initial_level", ConstantData(initial_level))
        problem = build_problem(
            network,
            database,
            TimeBlock(1, list(range(168 * week, 168 * (week + 1)))),
            scenarios,
        )
        status = problem.solver.Solve()
        assert status == problem.solver.OPTIMAL
        total_cost += problem.solver.Objective().Value()

        output = OutputValues(problem)
        initial_level = output.component("H").var("level").value[0][-1]  # type:ignore

    assert total_cost == pytest.approx(58832554067)


def create_database_and_network(
    hydro_model: Model,
    return_to_initial_level: bool,
) -> tuple[DataBase, Network]:
    capacity = 1e07
    initial_level = 0.445 * capacity
    demand_data = np.loadtxt(
        Path(__file__).parent
        / "../../tests/functional/data/hydro_with_large_load/load.txt",
        usecols=0,
    )
    inflow_data = (
        np.loadtxt(
            Path(__file__).parent
            / "../../tests/functional/data/hydro_with_large_load/mod.txt",
            usecols=0,
        ).repeat(24)
        / 24
    )
    rule_curve_data = np.loadtxt(
        Path(__file__).parent
        / "../../tests/functional/data/hydro_with_large_load/reservoir.txt"
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

    database.add_data("G1", "p_max", ConstantData(30000))
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
