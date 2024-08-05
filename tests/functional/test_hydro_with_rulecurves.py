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

expected_weekly_target = [
    109351.86292514109,
    111726.1238133478,
    111672.02178563867,
    113437.13342869015,
    62616.900712692266,
    23991.30072993157,
    24205.8685804484,
    23841.307084756725,
    61261.93871434613,
    89844.8189589692,
    88014.90475844462,
    88233.53746669635,
    75513.68104089717,
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
    52834.94251817542,
    64170.764366982155,
    69887.53747203582,
    117690.35564280929,
    225600.3527384371,
    225343.98594768142,
    225396.68087341834,
    269286.9804404632,
    220748.07777396217,
    221848.1338577599,
    222669.867308102,
    231799.58049729763,
    235689.46113471934,
    228057.0061722157,
    233248.7929951121,
    238444.8799521864,
    242073.10581958073,
    230837.7730157587,
    240452.7654725604,
    239759.55615180839,
    239858.33673477554,
]


def test_hydro_heuristic_monthly_part() -> None:
    """ """
    capacity = 1e07

    solving_output, monthly_output = optimize_target(
        heuristic_parameters=HydroHeuristicParameters(1),
        data_aggregator_parameters=DataAggregatorParameters(
            [24 * get_number_of_days_in_month(m) for m in range(12)],
            list(range(12)),
        ),
        reservoir_data=ReservoirParameters(
            capacity,
            initial_level=0.445 * capacity,
            folder_name="hydro_with_rulecurves",
            scenario=0,
        ),
        heuristic_model=HeuristicHydroModelBuilder(HYDRO_MODEL, "monthly").get_model(),
    )

    assert solving_output.status == pywraplp.Solver.OPTIMAL
    assert solving_output.objective / capacity == pytest.approx(10.1423117689793)


def test_hydro_heuristic_daily_part() -> None:
    """ """
    capacity = 1e07

    reservoir_data = ReservoirParameters(
        capacity,
        initial_level=0.445 * capacity,
        folder_name="hydro_with_rulecurves",
        scenario=0,
    )

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

        solving_output, daily_output = optimize_target(
            heuristic_parameters=HydroHeuristicParameters(1, monthly_generation[month]),
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
        assert solving_output.objective / capacity == pytest.approx(
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
            all_daily_generation, daily_output.generating
        )
        day_in_year += number_day_month

    weekly_target = calculate_weekly_target(
        all_daily_generation,
    )
    assert all_daily_generation == pytest.approx(
        list(
            np.loadtxt(
                Path(__file__).parent
                / "../../tests/functional/data/hydro_with_rulecurves/daily_target.txt"
            )
            * capacity
            / 100
        ),
        abs=0.5,
    )
    assert weekly_target == pytest.approx(expected_weekly_target)


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

    assert total_cost == pytest.approx(57013275574)


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
