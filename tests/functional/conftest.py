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

from typing import List, Optional, Tuple

import ortools.linear_solver.pywraplp as pywraplp
import pytest

from andromede.hydro_heuristic.data import (
    compute_weekly_target,
    get_number_of_days_in_month,
    save_generation_target,
)
from andromede.hydro_heuristic.heuristic_model import HeuristicHydroModelBuilder
from andromede.hydro_heuristic.problem import (
    DataAggregatorParameters,
    HydroHeuristicData,
    HydroHeuristicParameters,
    OutputHeuristic,
    ReservoirParameters,
    SolvingOutput,
    build_hydro_heuristic_problem,
    get_database,
    get_default_solver_parameters,
    retrieve_important_heuristic_output,
    update_initial_level,
)
from andromede.model import Model
from tests.functional.libs.lib_hydro_heuristic import HYDRO_MODEL


@pytest.fixture
def monthly_hydro_heuristic_model() -> Model:
    return HeuristicHydroModelBuilder(HYDRO_MODEL, "monthly").build_model()


@pytest.fixture
def daily_hydro_heuristic_model() -> Model:
    return HeuristicHydroModelBuilder(HYDRO_MODEL, "daily").build_model()


@pytest.fixture
def monthly_aggregator_parameters() -> DataAggregatorParameters:
    monthly_aggregator_parameters = DataAggregatorParameters(
        [24 * get_number_of_days_in_month(m) for m in range(12)],
        list(range(12)),
    )

    return monthly_aggregator_parameters


@pytest.fixture
def daily_aggregator_parameters() -> List[DataAggregatorParameters]:
    daily_aggregator_parameters = []
    day_in_year = 0
    for month in range(12):
        number_day_month = get_number_of_days_in_month(month)
        daily_aggregator_parameters.append(
            DataAggregatorParameters(
                [24 for d in range(365)],
                list(range(day_in_year, day_in_year + number_day_month)),
            )
        )
        day_in_year += number_day_month

    return daily_aggregator_parameters


def antares_hydro_heuristic_workflow(
    monthly_aggregator_parameters: DataAggregatorParameters,
    monthly_hydro_heuristic_model: Model,
    intermonthly: int,
    daily_aggregator_parameters: List[DataAggregatorParameters],
    daily_hydro_heuristic_model: Model,
    interdaily: int,
    reservoir_data: ReservoirParameters,
) -> List[float]:
    # Annual part with monthly timesteps
    solving_output, monthly_output = antares_hydro_heuristic_step(
        monthly_aggregator_parameters,
        monthly_hydro_heuristic_model,
        intermonthly,
        reservoir_data,
    )

    assert solving_output.status == pywraplp.Solver.OPTIMAL

    # Monthly part with daily timesteps
    all_daily_generation: List[float] = []

    for month in range(12):
        solving_output, daily_output = antares_hydro_heuristic_step(
            daily_aggregator_parameters[month],
            daily_hydro_heuristic_model,
            interdaily,
            reservoir_data,
            monthly_output.generating[month],
        )
        assert solving_output.status == pywraplp.Solver.OPTIMAL

        update_initial_level(reservoir_data, daily_output)
        all_daily_generation = save_generation_target(
            all_daily_generation, daily_output.generating
        )

    # Computation of weekly targets
    weekly_target = compute_weekly_target(all_daily_generation)
    return weekly_target


def antares_hydro_heuristic_step(
    aggregator_parameters: DataAggregatorParameters,
    hydro_heuristic_model: Model,
    breakdown: int,
    reservoir_data: ReservoirParameters,
    total_target: Optional[float] = None,
) -> Tuple[SolvingOutput, OutputHeuristic]:
    data = HydroHeuristicData(aggregator_parameters, reservoir_data)
    data.compute_target(HydroHeuristicParameters(breakdown, total_target))

    heuristic_problem = build_hydro_heuristic_problem(
        database=get_database(data),
        heuristic_model=hydro_heuristic_model,
        timesteps=len(aggregator_parameters.timesteps),
    )
    status = heuristic_problem.solver.Solve(get_default_solver_parameters())
    solving_output = SolvingOutput(status, heuristic_problem.solver.Objective().Value())

    heuristic_output = retrieve_important_heuristic_output(heuristic_problem)
    return solving_output, heuristic_output
