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
from typing import List, Optional

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
    BINDING_CONSTRAINT,
    HYDRO_MODEL,
    HYDRO_MODEL_WITH_TARGET,
)


def test_hydro_heuristic() -> None:
    """Check that weekly targets are the same in the POC and in Antares."""
    capacity = 2945
    reservoir_data = ReservoirParameters(
        capacity,
        initial_level=0.5 * capacity,
        folder_name=str(Path(__file__).parent)
        + "../../tests/functional/data/hydro_small_capacity",
        scenario=0,
    )

    solving_output, monthly_output = optimize_target(
        heuristic_parameters=HydroHeuristicParameters(1),
        data_aggregator_parameters=DataAggregatorParameters(
            [24 * get_number_of_days_in_month(m) for m in range(12)],
            list(range(12)),
        ),
        reservoir_data=reservoir_data,
        heuristic_model=HeuristicHydroModelBuilder(HYDRO_MODEL, "monthly").get_model(),
    )

    assert solving_output.status == pywraplp.Solver.OPTIMAL

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
    expected_output_file = open(
        "tests/functional/data/hydro_small_capacity/values-weekly.txt",
        "r",
    )
    expected_output = expected_output_file.readlines()
    for week in range(52):
        assert float(expected_output[week + 7].strip().split("\t")[42]) - 0.75 * float(
            expected_output[week + 7].strip().split("\t")[43]
        ) == pytest.approx(weekly_target[week], abs=1)


def test_complete_year_as_weekly_blocks() -> None:
    """Solve weekly problems with heuristic weekly targets for the stock."""
    database, network = create_database_and_network(
        HYDRO_MODEL_WITH_TARGET, return_to_initial_level=False, bc=False
    )

    capacity = 2945
    initial_level = 0.5 * capacity

    expected_output_file = open(
        "tests/functional/data/hydro_small_capacity/values-weekly.txt",
        "r",
    )
    expected_output = expected_output_file.readlines()

    for week in range(52):
        database.add_data(
            "H",
            "overall_target",
            ConstantData(
                float(expected_output[week + 7].strip().split("\t")[42])
                - 0.75 * float(expected_output[week + 7].strip().split("\t")[43])
            ),
        )
        database.add_data("H", "initial_level", ConstantData(initial_level))
        problem = build_problem(
            network,
            database,
            TimeBlock(1, list(range(168 * week, 168 * (week + 1)))),
            1,
        )
        status = problem.solver.Solve()
        assert status == problem.solver.OPTIMAL

        output = OutputValues(problem)
        initial_level = output.component("H").var("level").value[0][-1]  # type:ignore


def test_complete_year_as_weekly_blocks_with_binding_constraint() -> None:
    """Solve weekly problems with heuristic weekly targets for the stock with a binding constraint that implements a minimum generation for the stock. As this constraint is not seen by the heuristic, the problem is infeasible."""
    database, network = create_database_and_network(
        HYDRO_MODEL_WITH_TARGET, return_to_initial_level=False, bc=True
    )

    capacity = 2945
    initial_level = 0.5 * capacity

    expected_output_file = open(
        "tests/functional/data/hydro_small_capacity/values-weekly.txt",
        "r",
    )
    expected_output = expected_output_file.readlines()

    week = 0
    database.add_data(
        "H",
        "overall_target",
        ConstantData(
            float(expected_output[week + 7].strip().split("\t")[42])
            - 0.75 * float(expected_output[week + 7].strip().split("\t")[43])
        ),
    )
    database.add_data("H", "initial_level", ConstantData(initial_level))
    problem = build_problem(
        network,
        database,
        TimeBlock(1, list(range(168 * week, 168 * (week + 1)))),
        1,
    )
    status = problem.solver.Solve()
    assert status == problem.solver.INFEASIBLE


def test_complete_year_as_weekly_blocks_with_hourly_infeasibilities() -> None:
    """Solve weekly problems with heuristic weekly targets for the stock with modified inflow. Daily inflows remain the same. Inflows at the first hour of each day are large and there is oveflow that the heuristic didn't see due to agregation of data."""
    inflow_data = (
        np.loadtxt(
            Path(__file__).parent
            / "../../tests/functional/data/hydro_small_capacity/mod.txt",
            usecols=0,
        ).repeat(24)
        / 24
    )
    variation_inflow = np.tile(np.array([2300] + [-100] * 23), 365)

    database, network = create_database_and_network(
        HYDRO_MODEL_WITH_TARGET,
        return_to_initial_level=False,
        bc=False,
        inflow_data=list(inflow_data + variation_inflow),
    )

    capacity = 2945
    initial_level = 0.5 * capacity

    expected_output_file = open(
        "tests/functional/data/hydro_small_capacity/values-weekly.txt",
        "r",
    )
    expected_output = expected_output_file.readlines()

    week = 0
    database.add_data(
        "H",
        "overall_target",
        ConstantData(
            float(expected_output[week + 7].strip().split("\t")[42])
            - 0.75 * float(expected_output[week + 7].strip().split("\t")[43])
        ),
    )
    database.add_data("H", "initial_level", ConstantData(initial_level))
    problem = build_problem(
        network,
        database,
        TimeBlock(1, list(range(168 * week, 168 * (week + 1)))),
        1,
    )
    status = problem.solver.Solve()
    assert status == problem.solver.INFEASIBLE


def create_database_and_network(
    hydro_model: Model,
    return_to_initial_level: bool,
    bc: bool,
    inflow_data: Optional[list[float]] = None,
) -> tuple[DataBase, Network]:
    capacity = 2945
    initial_level = 0.5 * capacity
    demand_data = np.loadtxt(
        Path(__file__).parent
        / "../../tests/functional/data/hydro_small_capacity/load.txt",
        usecols=0,
    )
    if inflow_data is None:
        inflow_data = list(
            np.loadtxt(
                Path(__file__).parent
                / "../../tests/functional/data/hydro_small_capacity/mod.txt",
                usecols=0,
            ).repeat(24)
            / 24
        )
    rule_curve_data = np.loadtxt(
        Path(__file__).parent
        / "../../tests/functional/data/hydro_small_capacity/reservoir.txt"
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
    if bc:
        lb = create_component(model=BINDING_CONSTRAINT, id="lb")

    hydro = create_component(model=hydro_model, id="H")

    database = DataBase()

    database.add_data("1", "spillage_cost", ConstantData(0))
    database.add_data("1", "ens_cost", ConstantData(3000))
    database.add_data(
        "D",
        "demand",
        TimeSeriesData({TimeIndex(t): demand_data[t] for t in range(8760)}),
    )

    database.add_data("G1", "p_max", ConstantData(3000))
    database.add_data("G1", "cost", ConstantData(100))
    database.add_data("G2", "p_max", ConstantData(1250))
    database.add_data("G2", "cost", ConstantData(200))
    database.add_data("G3", "p_max", ConstantData(750))
    database.add_data("G3", "cost", ConstantData(300))

    database.add_data("H", "min_generating", ConstantData(0))

    database.add_data(
        "H",
        "max_generating",
        ConstantData(204),
    )

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

    database.add_data("lb", "lower_bound", ConstantData(10))

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
    if bc:
        network.add_component(lb)
    network.connect(PortRef(node, "balance_port"), PortRef(demand, "balance_port"))
    network.connect(PortRef(node, "balance_port"), PortRef(thermal_1, "balance_port"))
    network.connect(PortRef(node, "balance_port"), PortRef(thermal_2, "balance_port"))
    network.connect(PortRef(node, "balance_port"), PortRef(thermal_3, "balance_port"))
    network.connect(PortRef(node, "balance_port"), PortRef(hydro, "balance_port"))
    if bc:
        network.connect(PortRef(lb, "balance_port"), PortRef(hydro, "balance_port"))
    return database, network
