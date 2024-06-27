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

import pandas as pd
import pytest
import numpy as np
from typing import List, Dict
import ortools.linear_solver.pywraplp as pywraplp

from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP
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
    TimeScenarioSeriesData,
    TimeSeriesData,
    TimeIndex,
    create_component,
)
from andromede.study.data import AbstractDataStructure
from andromede.thermal_heuristic.model import (
    get_accurate_heuristic_model,
    get_model_fast_heuristic,
)
from andromede.thermal_heuristic.data import (
    get_max_failures,
    get_max_unit,
    get_max_unit_for_min_down_time,
)


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168
    scenario = 0
    week = 0

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for j, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):
        nb_on_1 = pd.DataFrame(
            np.transpose(
                np.ceil(
                    np.round(
                        np.loadtxt(
                            f"tests/functional/data_second_complex_case/accurate/itr1_accurate_cluster{j+1}.txt"
                        ),
                        12,
                    )
                )
            ),
            index=[i for i in range(number_hours)],
            columns=[0],
        )
        n_guide = TimeScenarioSeriesData(nb_on_1)

        # Solve heuristic problem
        problem_accurate_heuristic = create_problem_accurate_heuristic(
            {
                "G" + str(i): ConstantData(0) if "G" + str(i) != cluster else n_guide
                for i in range(1, 7)
            },
            number_hours,
            thermal_cluster=cluster,
            week=week,
            scenario=scenario,
        )
        status = problem_accurate_heuristic.solver.Solve(parameters)

        assert status == problem_accurate_heuristic.solver.OPTIMAL

        output_heuristic = OutputValues(problem_accurate_heuristic)
        nb_on_heuristic = np.transpose(
            np.ceil(np.array(output_heuristic.component(cluster).var("nb_on").value))
        )

        expected_output = np.loadtxt(
            f"tests/functional/data_second_complex_case/accurate/itr2_accurate_cluster{j+1}.txt"
        )
        for time_step in range(number_hours):
            assert nb_on_heuristic[time_step, 0] == expected_output[time_step]


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """
    number_hours = 168
    scenario = 0
    week = 0

    for j, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):
        nb_on_1 = np.loadtxt(
            f"tests/functional/data_second_complex_case/fast/itr1_fast_cluster{j+1}.txt"
        )

        # Solve heuristic problem
        mingen_heuristic = create_problem_fast_heuristic(
            nb_on_1,  # type:ignore
            number_hours,
            thermal_cluster=cluster,
            week=week,
            scenario=scenario,
        )

        expected_output = np.loadtxt(
            f"tests/functional/data_second_complex_case/fast/itr2_fast_cluster{j+1}.txt"
        )
        for time_step in range(number_hours):
            assert mingen_heuristic.values[time_step, 0] == expected_output[time_step]


def generate_database(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    week: int,
    scenario: int,
) -> DataBase:

    delta, pmax, pmin, cost, units = get_data()

    database = DataBase()

    for i, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):

        max_generating = get_failures_for_cluster(week, scenario, cluster, number_hours)
        max_units = get_max_unit(pmax[cluster], units[cluster], max_generating)
        max_failures = get_max_failures(max_units)
        nb_units_max_min_down_time = get_max_unit_for_min_down_time(
            delta[cluster], max_units
        )

        database.add_data(cluster, "p_max", ConstantData(pmax[cluster]))
        database.add_data(cluster, "p_min", ConstantData(pmin[cluster]))
        database.add_data(cluster, "cost", ConstantData(cost[cluster]))
        database.add_data(cluster, "startup_cost", ConstantData(10 * (i + 1)))
        database.add_data(cluster, "fixed_cost", ConstantData(i + 1))
        database.add_data(cluster, "d_min_up", ConstantData(delta[cluster]))
        database.add_data(cluster, "d_min_down", ConstantData(delta[cluster]))
        database.add_data(cluster, "nb_units_min", lower_bound[cluster])
        database.add_data(
            cluster,
            "nb_units_max",
            TimeScenarioSeriesData(max_units),
        )
        database.add_data(
            cluster,
            "max_generating",
            TimeScenarioSeriesData(max_generating),
        )
        database.add_data(
            cluster,
            "max_failure",
            TimeScenarioSeriesData(max_failures),
        )
        database.add_data(
            cluster,
            "nb_units_max_min_down_time",
            TimeScenarioSeriesData(nb_units_max_min_down_time),
        )
        database.add_data(cluster, "min_generating", lower_bound[cluster])

    return database


def get_data() -> (
    tuple[
        Dict[str, int], Dict[str, int], Dict[str, int], Dict[str, int], Dict[str, int]
    ]
):
    delta = {"G1": 3, "G2": 3, "G3": 2, "G4": 1, "G5": 1, "G6": 3}
    pmax = {"G1": 64, "G2": 221, "G3": 486, "G4": 218, "G5": 29, "G6": 159}
    pmin = {"G1": 32, "G2": 111, "G3": 194, "G4": 87, "G5": 14, "G6": 80}
    cost = {
        "G1": 165,
        "G2": 117,
        "G3": 106,
        "G4": 135,
        "G5": 191,
        "G6": 166,
    }
    units = {"G1": 21, "G2": 13, "G3": 13, "G4": 2, "G5": 7, "G6": 16}
    return delta, pmax, pmin, cost, units


def get_failures_for_cluster(
    week: int, scenario: int, cluster: str, number_hours: int
) -> pd.DataFrame:
    input_file = np.loadtxt(
        f"tests/functional/data_second_complex_case/series_{cluster}.txt",
        delimiter="\t",
    )

    failures_data = pd.DataFrame(
        data=input_file[
            number_hours * week : number_hours * week + number_hours, scenario
        ],
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return failures_data


def create_problem_accurate_heuristic(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> OptimizationProblem:

    database = generate_database(
        lower_bound, number_hours, week=week, scenario=scenario
    )

    time_block = TimeBlock(1, [i for i in range(number_hours)])
    scenarios = 1

    gen = create_component(
        model=get_accurate_heuristic_model(THERMAL_CLUSTER_MODEL_MILP),
        id=thermal_cluster,
    )

    network = Network("test")
    network.add_component(gen)

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
    )

    return problem


def create_problem_fast_heuristic(
    lower_bound: List[float],
    number_hours: int,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> pd.DataFrame:

    data_delta, data_pmax, data_pmin, _, data_nmax = get_data()
    delta = data_delta[thermal_cluster]
    pmax = data_pmax[thermal_cluster]
    pmin = data_pmin[thermal_cluster]
    nmax = data_nmax[thermal_cluster]
    pdispo = get_failures_for_cluster(week, scenario, thermal_cluster, number_hours)

    number_blocks = number_hours // delta

    database = DataBase()

    database.add_data("B", "n_max", ConstantData(nmax))
    database.add_data("B", "delta", ConstantData(delta))

    nb_on_1 = np.ceil(
        np.round(
            np.array(lower_bound) / pmax,
            12,
        )
    )

    database.add_data(
        "B",
        "n_guide",
        TimeSeriesData({TimeIndex(i): nb_on_1[i] for i in range(number_hours)}),
    )
    for h in range(delta):
        start_ajust = number_hours - delta + h
        database.add_data(
            "B",
            f"alpha_ajust_{h}",
            TimeSeriesData(
                {
                    TimeIndex(t): 1 if (t >= start_ajust) or (t < h) else 0
                    for t in range(number_hours)
                }
            ),
        )
        for k in range(number_blocks):
            start_k = k * delta + h
            end_k = min(start_ajust, (k + 1) * delta + h)
            database.add_data(
                "B",
                f"alpha_{k}_{h}",
                TimeSeriesData(
                    {
                        TimeIndex(t): 1 if (t >= start_k) and (t < end_k) else 0
                        for t in range(number_hours)
                    }
                ),
            )

    time_block = TimeBlock(1, [i for i in range(number_hours)])

    block = create_component(
        model=get_model_fast_heuristic(number_blocks, delta=delta), id="B"
    )

    network = Network("test")
    network.add_component(block)

    problem = build_problem(
        network,
        database,
        time_block,
        1,
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
    )

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    problem.solver.EnableOutput()

    status = problem.solver.Solve(parameters)

    assert status == problem.solver.OPTIMAL

    output_heuristic = OutputValues(problem)
    n_heuristic = np.array(
        output_heuristic.component("B").var("n").value[0]  # type:ignore
    ).reshape((168, 1))

    mingen_heuristic = pd.DataFrame(
        np.minimum(n_heuristic * pmin, pdispo),
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return mingen_heuristic
