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
from typing import List

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pytest

from andromede.hydro_heuristic.data import (
    calculate_weekly_target,
    get_number_of_days_in_month,
    update_generation_target,
)
from andromede.hydro_heuristic.heuristic_model import HeuristicHydroModelBuilder
from andromede.hydro_heuristic.problem import (
    DataAggregatorParameters,
    HydroHeuristicParameters,
    ReservoirParameters,
    optimize_target,
)
from andromede.libs.standard import (
    DEMAND_MODEL,
    GENERATOR_MODEL_WITH_AVAILIBILITY,
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
    HYDRO_MODEL_RULE_CURVES,
    HYDRO_MODEL_WITH_TARGET,
)

optimal_generation = np.array(
    [
        970769.5416666669,
        861569.4583333309,
        62812.00000000003,
        200749.91666666663,
        141134.41666666695,
        126312.49999999991,
        363693.41666666657,
        108869.99999999977,
        282407.74999999977,
        195624.33333333328,
        224115.4583333334,
        178595.7500000001,
        169385.4166666667,
        218124.83333333346,
        -23170.375000000186,
        -95656.12499999999,
        -14351.708333333398,
        -126658.00000000022,
        -505373.2500000001,
        -500585.33333333326,
        -506195.7499999998,
        -502971.3333333329,
        -233037.00000000047,
        -241259.74999999997,
        -188374.74999999983,
        -179214.99999999994,
        -196510.49999999994,
        -368825.0,
        -153642.00000000012,
        -437611.00000000006,
        -363752.0000000001,
        -281616.00000000006,
        -194688.00000000012,
        -155247.00000000012,
        -174545.00000000017,
        322724.99999999994,
        1514789.9999999998,
        864940.5833333291,
        437826.99999999994,
        468997.0,
        504821.9999999999,
        387070.875,
        337153.6250000011,
        242700.99999999825,
        125085.3333333341,
        305316.9166666665,
        187429.08333333337,
        171796.66666666674,
        396580.75,
        625215.791666667,
        -112760.54166666513,
        -153855.99999999988,
    ]
)

expected_monthly_generation = [
    136760.44202273246,
    454722.55797726725,
    392228.0,
    0.0,
    0.0,
    0.0,
    0.0,
    283540.0,
    898040.8616171081,
    991513.8584313857,
    1006350.2625943671,
    1128251.0173571385,
]

expected_weekly_target = [
    28832.27964045688,
    30711.703865259067,
    30618.000504990046,
    32226.07138819498,
    72174.61325238849,
    113839.19907816286,
    117433.0699300096,
    111778.55881012032,
    104659.53500964906,
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
    211599.27129032084,
    207135.74190508344,
    208279.0273427336,
    249982.82107897024,
    206222.07904732513,
    209665.7858541006,
    213074.58200765122,
    239929.85629180167,
    243948.82501163633,
    214729.16634437843,
    227819.9161894151,
    243868.1052085034,
    259440.27843087824,
    236637.23039282142,
    270337.6492112127,
    265096.8896480867,
    264759.8266297981,
]


def test_complete_year_as_one_block() -> None:
    """Solve yearly problem as one block to see the difference between this optimal solution and the solution found by the heuristic. As the heuristic dosen't see thermal unavaibility and as the heuristic doesn't take into account pumping capacity, the heuristic solution is suboptimal."""
    database, network = create_database_and_network(
        HYDRO_MODEL_RULE_CURVES, return_to_initial_level=True
    )

    scenarios = 1
    problem = build_problem(
        network, database, TimeBlock(1, list(range(8736))), scenarios
    )
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == pytest.approx(57079450112.5)

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
    """Check that weekly targets are the same in the POC and in Antares."""
    capacity = 1e7

    reservoir_data = ReservoirParameters(
        capacity,
        initial_level=0.445 * capacity,
        folder_name=str(Path(__file__).parent)
        + "../../tests/functional/data/hydro_with_rulecurves",
        scenario=0,
    )

    solving_output, monthly_output = optimize_target(
        heuristic_parameters=HydroHeuristicParameters(3),
        data_aggregator_parameters=DataAggregatorParameters(
            [24 * get_number_of_days_in_month(m) for m in range(12)],
            list(range(12)),
        ),
        reservoir_data=reservoir_data,
        heuristic_model=HeuristicHydroModelBuilder(HYDRO_MODEL, "monthly").get_model(),
    )

    assert solving_output.status == pywraplp.Solver.OPTIMAL
    assert monthly_output.generating == expected_monthly_generation

    all_daily_generation: List[float] = []
    day_in_year = 0

    for month in range(12):
        number_day_month = get_number_of_days_in_month(month)

        solving_output, daily_output = optimize_target(
            heuristic_parameters=HydroHeuristicParameters(
                3, monthly_output.generating[month]
            ),
            data_aggregator_parameters=DataAggregatorParameters(
                [24 for d in range(365)],
                list(range(day_in_year, day_in_year + number_day_month)),
            ),
            reservoir_data=reservoir_data,
            heuristic_model=HeuristicHydroModelBuilder(
                HYDRO_MODEL, "daily"
            ).get_model(),
        )
        reservoir_data.initial_level = daily_output.level

        assert solving_output.status == pywraplp.Solver.OPTIMAL

        all_daily_generation = update_generation_target(
            all_daily_generation, daily_output.generating
        )
        day_in_year += number_day_month

    # Calcul des cibles hebdomadaires
    weekly_target = calculate_weekly_target(
        all_daily_generation,
    )

    # Vérification des valeurs trouvées
    assert weekly_target == pytest.approx(expected_weekly_target)


def test_complete_year_as_weekly_blocks_with_hydro_heuristic() -> None:
    """Solve weekly problems with heuristic weekly targets for the stock."""
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

    assert total_cost == pytest.approx(60879820711)


def create_database_and_network(
    hydro_model: Model,
    return_to_initial_level: bool,
) -> tuple[DataBase, Network]:
    capacity = 1e07
    initial_level = 0.445 * capacity
    demand_data = np.loadtxt(
        Path(__file__).parent
        / "../../tests/functional/data/hydro_with_rulecurves/load.txt",
        usecols=0,
    )
    inflow_data = (
        np.loadtxt(
            Path(__file__).parent
            / "../../tests/functional/data/hydro_with_rulecurves/mod.txt",
            usecols=0,
        ).repeat(24)
        / 24
    )
    rule_curve_data = np.loadtxt(
        Path(__file__).parent
        / "../../tests/functional/data/hydro_with_rulecurves/reservoir.txt"
    ).repeat(24, axis=0)

    node = Node(model=NODE_WITH_SPILL_AND_ENS_MODEL, id="1")

    thermal_1 = create_component(
        model=GENERATOR_MODEL_WITH_AVAILIBILITY,
        id="G1",
    )

    thermal_2 = create_component(
        model=GENERATOR_MODEL_WITH_AVAILIBILITY,
        id="G2",
    )

    thermal_3 = create_component(
        model=GENERATOR_MODEL_WITH_AVAILIBILITY,
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

    database.add_data(
        "G1",
        "p_max",
        TimeSeriesData(
            {TimeIndex(t): 20000 if 6000 <= t <= 7000 else 30000 for t in range(8760)}
        ),
    )
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
