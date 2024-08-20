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
from typing import List, Tuple

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
    HYDRO_MODEL_RULE_CURVES,
    HYDRO_MODEL_WITH_TARGET,
)

optimal_generation = np.array(
    [
        970769.54166667,
        861569.45833333,
        62812.0,
        200749.91666667,
        141134.41666667,
        126312.5,
        363693.41666667,
        108870.0,
        282407.75,
        195624.33333333,
        224115.45833333,
        178595.75,
        169385.41666667,
        218124.83333333,
        -23170.375,
        -95656.125,
        -14351.70833333,
        -126658.0,
        -505373.25,
        -500585.33333333,
        -506195.75,
        -502971.33333333,
        -233037.0,
        -241259.75,
        -188374.75,
        -179215.0,
        39146.16666667,
        -57964.41666667,
        34419.625,
        -296548.91666667,
        -363752.0,
        -281616.0,
        -194688.0,
        -155247.0,
        -174545.0,
        -157275.0,
        -165210.0,
        -163579.0,
        17827.0,
        48997.0,
        84822.0,
        111583.0,
        408906.0,
        564588.0,
        337915.0,
        508152.0,
        678530.0,
        898910.0,
        796024.0,
        556589.12499998,
        552651.0,
        670764.0,
    ]
)

expected_monthly_generation = [
    152697.73105305,
    438785.26894695,
    392228.0,
    0.0,
    0.0,
    0.0,
    0.0,
    283540.0,
    811245.60160001,
    939332.74547519,
    961679.01031377,
    1311898.64261102,
]

expected_weekly_target = [
    30808.59868795,
    34138.59595819,
    33878.95450005,
    37138.74177906,
    68243.30211844,
    109585.49868441,
    116206.55310524,
    106413.64170753,
    106235.09659609,
    94120.89889535,
    87772.00295574,
    86306.95398197,
    72862.16102998,
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
    50475.29566149,
    63276.90557923,
    66979.26924831,
    123852.52951097,
    195032.417803,
    183190.90389278,
    186094.70977249,
    225883.57013174,
    183224.09230019,
    188761.4662071,
    195376.51984883,
    237680.27684789,
    242770.15796234,
    194253.57880885,
    211696.55361414,
    237810.22449688,
    257421.57201802,
    202072.25316213,
    256981.90893995,
    375423.77165044,
    390653.48131144,
]


def test_complete_year_as_one_block() -> None:
    """Solve yearly problem as one block to see the difference between this optimal solution and the solution found by the heuristic."""
    database, network = create_database_and_network(
        HYDRO_MODEL_RULE_CURVES, return_to_initial_level=True
    )

    scenarios = 1
    problem = build_problem(
        network, database, TimeBlock(1, list(range(8736))), scenarios
    )
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == pytest.approx(55625371108.33334)

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

    reservoir_data = ReservoirParameters(
        capacity=1e7,
        initial_level=0.445 * 1e7,
        folder_name=str(Path(__file__).parent) + "/data/hydro_with_large_load",
        scenario=0,
    )

    solving_output, monthly_output = optimize_target(
        heuristic_parameters=HydroHeuristicParameters(5),
        data_aggregator_parameters=DataAggregatorParameters(
            [24 * get_number_of_days_in_month(m) for m in range(12)],
            list(range(12)),
        ),
        reservoir_data=reservoir_data,
        heuristic_model=HeuristicHydroModelBuilder(HYDRO_MODEL, "monthly").get_model(),
    )

    assert solving_output.status == pywraplp.Solver.OPTIMAL
    assert monthly_output.generating == pytest.approx(expected_monthly_generation)

    all_daily_generation: List[float] = []
    day_in_year = 0

    for month in range(12):
        number_day_month = get_number_of_days_in_month(month)

        solving_output, daily_output = optimize_target(
            heuristic_parameters=HydroHeuristicParameters(
                5, monthly_output.generating[month]
            ),
            data_aggregator_parameters=DataAggregatorParameters(
                [24] * 365,
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
    """Solve weekly problems with heuristic weekly targets for the stock. Heuristic targets are larger at the end of the year due to an larger residual load. This isn't realistic because at the beginning of the year, in reality one cannot know that the residual will be larger."""
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

    assert total_cost == pytest.approx(58423664977)


def create_database_and_network(
    hydro_model: Model,
    return_to_initial_level: bool,
) -> Tuple[DataBase, Network]:
    capacity = 1e07
    initial_level = 0.445 * capacity
    demand_data = np.loadtxt(
        Path(__file__).parent / "/data/hydro_with_large_load/load.txt",
        usecols=0,
    )
    inflow_data = (
        np.loadtxt(
            Path(__file__).parent / "/data/hydro_with_large_load/mod.txt",
            usecols=0,
        ).repeat(24)
        / 24
    )
    rule_curve_data = np.loadtxt(
        Path(__file__).parent / "/data/hydro_with_large_load/reservoir.txt"
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
