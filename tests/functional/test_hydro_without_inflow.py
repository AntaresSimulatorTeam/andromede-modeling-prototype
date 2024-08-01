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
from andromede.hydro_heuristic.heuristic_model import HeuristicHydroModelBuilder

weekly_generation = np.array(
    [
        1146984,
        1326912,
        848176,
        196577,
        13755,
        97279,
        173275,
        44154,
        203481,
        180828,
        54701,
        99758,
        -56398,
        115504,
        422,
        -33918,
        34460,
        2103,
        -17772,
        -52055,
        -20063,
        29862,
        -54541,
        -39715,
        -78495,
        -52954,
        -84570,
        -368825,
        -153642,
        -437611,
        -363752,
        -281616,
        -194688,
        -155247,
        -174545,
        -157275,
        -165210,
        -163579,
        17827,
        48997,
        84822,
        111583,
        408906,
        564588,
        -95571,
        -751848,
        -581470,
        -361090,
        -463976,
        -133420,
        -157252,
        -153856,
    ]
)


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
    assert problem.solver.Objective().Value() == pytest.approx(56633341500)

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
        ) == pytest.approx(weekly_generation[week], rel=1e-6, abs=1e-11)


def test_hydro_heuristic() -> None:
    """ """
    scenarios = 1
    intermonthly_breakdown = 1
    interdaily_breakdown = 1
    folder_name = "hydro_without_inflow"

    capacity = 1e7

    for scenario in range(scenarios):
        initial_level = 0.445 * capacity

        initial_level, status, _, monthly_generation = optimize_target(
            intermonthly_breakdown,
            folder_name,
            capacity,
            scenario,
            initial_level,
            hours_aggregated_time_steps=[
                24 * get_number_of_days_in_month(m) for m in range(12)
            ],
            timesteps=list(range(12)),
            total_target=None,
            heuristic_model=HeuristicHydroModelBuilder(
                HYDRO_MODEL, "monthly"
            ).get_model(),
        )

        assert status == pywraplp.Solver.OPTIMAL
        assert monthly_generation == [0 for m in range(12)]

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
                hours_aggregated_time_steps=[24 for d in range(365)],
                timesteps=list(range(day_in_year, day_in_year + number_day_month)),
                total_target=monthly_generation[month],
                heuristic_model=HeuristicHydroModelBuilder(
                    HYDRO_MODEL, "daily"
                ).get_model(),
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
        assert weekly_target == [0 for w in range(52)]


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
        database.add_data("H", "overall_target", ConstantData(0))
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

    assert total_cost == pytest.approx(59811131400)


def create_database_and_network(
    hydro_model: Model,
    return_to_initial_level: bool,
) -> tuple[DataBase, Network]:
    capacity = 1e07
    initial_level = 0.445 * capacity
    demand_data = np.loadtxt(
        Path(__file__).parent
        / "../../tests/functional/data/hydro_without_inflow/load.txt",
        usecols=0,
    )
    rule_curve_data = np.loadtxt(
        Path(__file__).parent
        / "../../tests/functional/data/hydro_without_inflow/reservoir.txt"
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
        ConstantData(0),
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
