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

import ortools.linear_solver.pywraplp as pywraplp
import pytest
import numpy as np

from andromede.hydro_heuristic.data import (
    get_number_of_days_in_month,
    update_generation_target,
    calculate_weekly_target,
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
    HYDRO_MODEL_WITH_TARGET,
)

from pathlib import Path

expected_weekly_target = [
    31657.48533235,
    32344.83648699,
    32329.17389009,
    32840.17566414,
    75897.66513222,
    112126.73520839,
    113129.54838763,
    111425.71870559,
    100352.7189676,
    89844.81895897,
    88014.90475844,
    88233.5374667,
    75513.6810409,
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
    52835.34251818,
    64170.76436698,
    69887.53747203,
    117690.35564281,
    225600.46547104,
    225344.09855218,
    225396.79350424,
    269287.12551898,
    220748.39177603,
    221848.4494246,
    222670.18404381,
    231799.91021952,
    235690.15509206,
    228057.96000508,
    233249.76854228,
    238445.87723163,
    242073.72189647,
    230837.30430287,
    240452.27723657,
    239759.06932336,
    239857.84970576,
]


def test_hydro_heuristic_monthly_part() -> None:
    """ """
    capacity = 1e07
    intermonthly_breakdown = 1
    folder_name = "hydro_with_rulecurves"
    initial_level = 0.445 * capacity

    initial_level, status, obj, _ = optimize_target(
        inter_breakdown=intermonthly_breakdown,
        folder_name=folder_name,
        capacity=capacity,
        scenario=0,
        initial_level=initial_level,
        horizon="monthly",
        timesteps=list(range(12)),
        total_target=None,
    )

    assert status == pywraplp.Solver.OPTIMAL

    assert obj / capacity == pytest.approx(10.1423117689793)


def test_hydro_heuristic_daily_part() -> None:
    """ """
    scenario = 0
    capacity = 1e07
    interdaily_breakdown = 1
    folder_name = "hydro_with_rulecurves"
    initial_level = 0.445 * capacity

    monthly_generation = [
        capacity * target
        for target in [
            0.0495627,
            0.00958564,
            0.0392228,
            0,
            0,
            0,
            0,
            0.028354,
            0.0966672,
            0.100279,
            0.100799,
            0.10467,
        ]
    ]  # equivalent solution found by Antares that is taken to be consistent

    all_daily_generation: List[float] = []
    day_in_year = 0

    for month in range(12):
        number_day_month = get_number_of_days_in_month(month)

        initial_level, status, obj, daily_generation = optimize_target(
            inter_breakdown=interdaily_breakdown,
            folder_name=folder_name,
            capacity=capacity,
            scenario=scenario,
            initial_level=initial_level,
            horizon="daily",
            timesteps=list(range(day_in_year, day_in_year + number_day_month)),
            total_target=monthly_generation[month],
        )
        assert status == pywraplp.Solver.OPTIMAL
        assert obj / capacity == pytest.approx(
            [
                -0.405595,
                -0.354666,
                -0.383454,
                -0.374267,
                -0.424858,
                -0.481078,
                -0.595347,
                0.0884837,
                -0.638019,
                -0.610892,
                -0.526716,
                -0.466928,
            ][month],
            abs=0.02,
        )

        all_daily_generation = update_generation_target(
            all_daily_generation, daily_generation
        )
        day_in_year += number_day_month

    weekly_target = calculate_weekly_target(
        all_daily_generation,
    )
    assert all_daily_generation == list(
        np.loadtxt("tests\\functional\\data\\hydro_with_rulecurves\\daily_target.txt")
        * capacity
        / 100
    )
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

    assert total_cost == pytest.approx(58423664977)


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
