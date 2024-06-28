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
import pandas as pd

from andromede.hydro_heuristic.heuristic_model import HeuristicHydroModelBuilder
from andromede.simulation import (
    BlockBorderManagement,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.simulation.optimization import OptimizationProblem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
    create_component,
)
from tests.functional.libs.lib_hydro_heuristic import HYDRO_MODEL
from andromede.hydro_heuristic.data import HydroHeuristicData


def create_hydro_problem(
    horizon: str,
    hydro_data: HydroHeuristicData,
) -> OptimizationProblem:
    database = generate_database(
        hydro_data=hydro_data,
    )

    database = add_objective_coefficients_to_database(database, horizon)

    time_block = TimeBlock(1, [i for i in range(len(hydro_data.target))])
    scenarios = 1

    hydro = create_component(
        model=HeuristicHydroModelBuilder(HYDRO_MODEL, horizon).get_model(), id="H"
    )

    network = Network("test")
    network.add_component(hydro)

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=(BlockBorderManagement.CYCLE),
    )

    return problem


def solve_hydro_problem(problem: OptimizationProblem) -> tuple[int, list[float], float]:
    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    problem.solver.EnableOutput()

    status = problem.solver.Solve(parameters)

    output = OutputValues(problem)

    return (
        status,
        output.component("H").var("generating").value[0],  # type:ignore
        output.component("H").var("level").value[0][-1],  # type:ignore
    )


def generate_database(
    hydro_data: HydroHeuristicData,
) -> DataBase:
    database = DataBase()

    database.add_data("H", "capacity", ConstantData(hydro_data.capacity))
    database.add_data("H", "initial_level", ConstantData(hydro_data.initial_level))

    inflow_data = pd.DataFrame(
        hydro_data.inflow,
        index=[i for i in range(len(hydro_data.inflow))],
        columns=[0],
    )
    database.add_data("H", "inflow", TimeScenarioSeriesData(inflow_data))

    target_data = pd.DataFrame(
        hydro_data.target,
        index=[i for i in range(len(hydro_data.target))],
        columns=[0],
    )
    database.add_data("H", "generating_target", TimeScenarioSeriesData(target_data))
    database.add_data("H", "overall_target", ConstantData(sum(hydro_data.target)))

    database.add_data(
        "H",
        "lower_rule_curve",
        TimeSeriesData(
            {
                TimeIndex(i): hydro_data.lower_rule_curve[i] * hydro_data.capacity
                for i in range(len(hydro_data.lower_rule_curve))
            }
        ),
    )
    database.add_data(
        "H",
        "upper_rule_curve",
        TimeSeriesData(
            {
                TimeIndex(i): hydro_data.upper_rule_curve[i] * hydro_data.capacity
                for i in range(len(hydro_data.lower_rule_curve))
            }
        ),
    )
    database.add_data("H", "min_generating", ConstantData(0))

    database.add_data(
        "H",
        "max_generating",
        TimeSeriesData(
            {
                TimeIndex(i): hydro_data.max_generating[i]
                for i in range(len(hydro_data.max_generating))
            }
        ),
    )

    database.add_data(
        "H",
        "max_epsilon",
        TimeSeriesData(
            {
                TimeIndex(i): hydro_data.capacity if i == 0 else 0
                for i in range(len(hydro_data.max_generating))
            }
        ),
    )

    return database


def add_objective_coefficients_to_database(
    database: DataBase, horizon: str
) -> DataBase:
    objective_function_cost = {
        "gamma_d": 1,
        "gamma_delta": 1 if horizon == "monthly" else 2,
        "gamma_y": 100000 if horizon == "monthly" else 68,
        "gamma_w": 0 if horizon == "monthly" else 34,
        "gamma_v+": 100 if horizon == "monthly" else 0,
        "gamma_v-": 100 if horizon == "monthly" else 68,
        "gamma_o": 0 if horizon == "monthly" else 23 * 68 + 1,
        "gamma_s": 0 if horizon == "monthly" else -1 / 32,
    }

    for name, coeff in objective_function_cost.items():
        database.add_data("H", name, ConstantData(coeff))

    return database
