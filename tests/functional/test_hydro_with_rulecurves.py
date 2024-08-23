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

from andromede.hydro_heuristic.data import compute_weekly_target, save_generation_target
from andromede.hydro_heuristic.problem import (
    DataAggregatorParameters,
    ReservoirParameters,
    update_initial_level,
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
from tests.functional.conftest import antares_hydro_heuristic_step
from tests.functional.libs.lib_hydro_heuristic import HYDRO_MODEL_WITH_TARGET


@pytest.fixture
def data_path() -> str:
    return str(Path(__file__).parent) + "/data/hydro_with_rulecurves"


@pytest.fixture
def expected_weekly_target(data_path: str) -> List[float]:
    return list(np.loadtxt(data_path + "/expected_weekly_target.txt"))


@pytest.fixture
def capacity() -> float:
    capacity = 1e07
    return capacity


@pytest.fixture
def reservoir_data(data_path: str, capacity: float) -> ReservoirParameters:
    reservoir_data = ReservoirParameters(
        capacity,
        initial_level=0.445 * capacity,
        folder_name=data_path,
        scenario=0,
    )

    return reservoir_data


@pytest.fixture
def monthly_generation(capacity: float) -> List[float]:
    return [
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


def test_hydro_heuristic_monthly_part(
    reservoir_data: ReservoirParameters,
    capacity: float,
    monthly_aggregator_parameters: DataAggregatorParameters,
    monthly_hydro_heuristic_model: Model,
) -> None:
    """Check that the cost of the monthly problem is the same in the POC and in Antares."""
    intermonthly = 1

    solving_output, _ = antares_hydro_heuristic_step(
        monthly_aggregator_parameters,
        monthly_hydro_heuristic_model,
        intermonthly,
        reservoir_data,
    )

    assert solving_output.status == pywraplp.Solver.OPTIMAL
    assert solving_output.objective / capacity == pytest.approx(10.1423117689793)


def test_hydro_heuristic_daily_part(
    expected_weekly_target: List[float],
    capacity: float,
    reservoir_data: ReservoirParameters,
    daily_aggregator_parameters: List[DataAggregatorParameters],
    daily_hydro_heuristic_model: Model,
    monthly_generation: List[float],
    data_path: str,
) -> None:
    """Check that the costs of the daily problems are the same in the POC and in Antares."""
    interdaily = 1
    all_daily_generation: List[float] = []

    for month in range(12):
        solving_output, daily_output = antares_hydro_heuristic_step(
            daily_aggregator_parameters[month],
            daily_hydro_heuristic_model,
            interdaily,
            reservoir_data,
            monthly_generation[month],
        )

        update_initial_level(reservoir_data, daily_output)

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

        all_daily_generation = save_generation_target(
            all_daily_generation, daily_output.generating
        )

    weekly_target = compute_weekly_target(all_daily_generation)
    assert all_daily_generation == pytest.approx(
        list(np.loadtxt(data_path + "/daily_target.txt") * capacity / 100),
        abs=0.5,
    )
    assert weekly_target == pytest.approx(expected_weekly_target)


def test_complete_year_as_weekly_blocks_with_hydro_heuristic(
    expected_weekly_target: List[float], data_path: str
) -> None:
    """Solve weekly problems with heuristic weekly targets for the stock."""
    database, network = create_database_and_network(
        data_path, HYDRO_MODEL_WITH_TARGET, return_to_initial_level=False
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
    data_path: str,
    hydro_model: Model,
    return_to_initial_level: bool,
) -> Tuple[DataBase, Network]:
    capacity = 1e07
    initial_level = 0.445 * capacity
    demand_data = np.loadtxt(data_path + "/load.txt", usecols=0)
    inflow_data = np.loadtxt(data_path + "/mod.txt", usecols=0).repeat(24) / 24
    rule_curve_data = np.loadtxt(data_path + "/reservoir.txt").repeat(24, axis=0)

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
