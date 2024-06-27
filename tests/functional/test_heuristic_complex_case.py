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

from andromede.libs.standard import (
    DEMAND_MODEL,
    NODE_BALANCE_MODEL,
    SPILLAGE_MODEL,
    UNSUPPLIED_ENERGY_MODEL,
)
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
    Node,
    PortRef,
    TimeScenarioSeriesData,
    TimeSeriesData,
    TimeIndex,
    create_component,
)
from andromede.study.data import AbstractDataStructure
from andromede.thermal_heuristic.model import (
    get_accurate_heuristic_model,
    get_model_fast_heuristic,
    get_thermal_cluster_accurate_model,
    get_thermal_cluster_fast_model,
)
from andromede.thermal_heuristic.data import (
    get_max_failures,
    get_max_unit,
    get_max_unit_for_min_down_time,
    check_output_values,
)


def test_milp_version() -> None:
    """ """
    number_hours = 168
    scenarios = 2

    for scenario in range(scenarios):
        for week in range(2):
            problem = create_complex_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=False,
                fast=False,
                week=week,
                scenario=scenario,
            )

            parameters = pywraplp.MPSolverParameters()
            parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
            parameters.SetIntegerParam(parameters.SCALING, 0)

            status = problem.solver.Solve(parameters)

            assert status == problem.solver.OPTIMAL

            check_output_values(
                problem, "milp", week, scenario=scenario, dir_path="data_complex_case"
            )

            expected_cost = [[78933742, 102109698], [17472101, 17424769]]
            assert problem.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168
    scenarios = 2

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for scenario in range(scenarios):
        for week in range(2):
            # First optimization
            problem_optimization_1 = create_complex_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=True,
                fast=False,
                week=week,
                scenario=scenario,
            )
            status = problem_optimization_1.solver.Solve(parameters)

            assert status == problem_optimization_1.solver.OPTIMAL

            # Get number of on units and round it to integer
            output_1 = OutputValues(problem_optimization_1)
            nb_on_min: Dict[str, AbstractDataStructure] = {}
            for g in ["G1", "G2", "G3"]:
                nb_on_1 = pd.DataFrame(
                    np.transpose(
                        np.ceil(
                            np.round(
                                np.array(output_1.component(g).var("nb_on").value), 12
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
                        th: n_guide if th == g else ConstantData(0)
                        for th in ["G1", "G2", "G3"]
                    },
                    number_hours,
                    thermal_cluster=g,
                    week=week,
                    scenario=scenario,
                )
                status = problem_accurate_heuristic.solver.Solve(parameters)

                assert status == problem_accurate_heuristic.solver.OPTIMAL

                output_heuristic = OutputValues(problem_accurate_heuristic)
                nb_on_heuristic = pd.DataFrame(
                    np.transpose(
                        np.ceil(
                            np.array(output_heuristic.component(g).var("nb_on").value)
                        )
                    ),
                    index=[i for i in range(number_hours)],
                    columns=[0],
                )
                nb_on_min[g] = TimeScenarioSeriesData(nb_on_heuristic)

            # Second optimization with lower bound modified
            problem_optimization_2 = create_complex_problem(
                nb_on_min,
                number_hours,
                lp_relaxation=True,
                fast=False,
                week=week,
                scenario=scenario,
            )
            status = problem_optimization_2.solver.Solve(parameters)

            assert status == problem_optimization_2.solver.OPTIMAL

            check_output_values(
                problem_optimization_2,
                "accurate",
                week,
                scenario=scenario,
                dir_path="data_complex_case",
            )

            expected_cost = [
                [78996726, 102215087 - 69500],
                [17587733, 17641808],
            ]
            assert problem_optimization_2.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """

    number_hours = 168
    scenarios = 2
    weeks = 2

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for scenario in range(scenarios):
        for week in range(weeks):
            # First optimization
            problem_optimization_1 = create_complex_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=True,
                fast=True,
                week=week,
                scenario=scenario,
            )
            status = problem_optimization_1.solver.Solve(parameters)

            assert status == problem_optimization_1.solver.OPTIMAL

            # Get number of on units
            output_1 = OutputValues(problem_optimization_1)

            # Solve heuristic problem
            mingen: Dict[str, AbstractDataStructure] = {}
            for g in ["G1", "G2", "G3"]:  #
                pmax = {"G1": 410, "G2": 90, "G3": 275}[g]
                nb_on_1 = np.ceil(
                    np.round(
                        np.array(
                            output_1.component(g)
                            .var("generation")
                            .value[0]  # type:ignore
                        )
                        / pmax,
                        12,
                    )
                )
                n_guide = TimeSeriesData(
                    {TimeIndex(i): nb_on_1[i] for i in range(number_hours)}
                )
                mingen_heuristic = create_problem_fast_heuristic(
                    n_guide,
                    number_hours,
                    thermal_cluster=g,
                    week=week,
                    scenario=scenario,
                )

                mingen[g] = TimeScenarioSeriesData(mingen_heuristic)

            # Second optimization with lower bound modified
            problem_optimization_2 = create_complex_problem(
                mingen,
                number_hours,
                lp_relaxation=True,
                fast=True,
                week=week,
                scenario=scenario,
            )
            status = problem_optimization_2.solver.Solve(parameters)

            assert status == problem_optimization_2.solver.OPTIMAL

            check_output_values(
                problem_optimization_2,
                "fast",
                week,
                scenario,
                dir_path="data_complex_case",
            )

            expected_cost = [
                [79277215 - 630089, 102461792 - 699765],
                [17803738 - 661246, 17720390 - 661246],
            ]
            assert problem_optimization_2.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def create_complex_problem(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    lp_relaxation: bool,
    fast: bool,
    week: int,
    scenario: int,
) -> OptimizationProblem:

    database = generate_database(
        lower_bound, number_hours, week=week, scenario=scenario
    )

    time_block = TimeBlock(1, [i for i in range(number_hours)])
    scenarios = 1

    node = Node(model=NODE_BALANCE_MODEL, id="1")
    demand = create_component(model=DEMAND_MODEL, id="D")

    if fast:
        FAST_MODEL = get_thermal_cluster_fast_model(THERMAL_CLUSTER_MODEL_MILP)
        gen1 = create_component(model=FAST_MODEL, id="G1")
        gen2 = create_component(model=FAST_MODEL, id="G2")
        gen3 = create_component(model=FAST_MODEL, id="G3")
    elif lp_relaxation:
        ACCURATE_MODEL = get_thermal_cluster_accurate_model(THERMAL_CLUSTER_MODEL_MILP)
        gen1 = create_component(model=ACCURATE_MODEL, id="G1")
        gen2 = create_component(model=ACCURATE_MODEL, id="G2")
        gen3 = create_component(model=ACCURATE_MODEL, id="G3")
    else:
        gen1 = create_component(model=THERMAL_CLUSTER_MODEL_MILP, id="G1")
        gen2 = create_component(model=THERMAL_CLUSTER_MODEL_MILP, id="G2")
        gen3 = create_component(model=THERMAL_CLUSTER_MODEL_MILP, id="G3")

    spillage = create_component(model=SPILLAGE_MODEL, id="S")

    unsupplied_energy = create_component(model=UNSUPPLIED_ENERGY_MODEL, id="U")

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen1)
    network.add_component(gen2)
    network.add_component(gen3)
    network.add_component(spillage)
    network.add_component(unsupplied_energy)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen1, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen2, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(gen3, "balance_port"), PortRef(node, "balance_port"))
    network.connect(PortRef(spillage, "balance_port"), PortRef(node, "balance_port"))
    network.connect(
        PortRef(unsupplied_energy, "balance_port"), PortRef(node, "balance_port")
    )

    problem = build_problem(
        network,
        database,
        time_block,
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
        solver_id="XPRESS",
    )

    return problem


def generate_database(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    week: int,
    scenario: int,
) -> DataBase:
    database = DataBase()

    failures_1 = pd.DataFrame(
        np.repeat(get_failures_for_cluster1(week, scenario), 24),
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    max_units_1 = get_max_unit(410, 1, failures_1)
    max_failures_1 = get_max_failures(max_units_1)
    nb_units_max_min_down_time_1 = get_max_unit_for_min_down_time(8, max_units_1)

    database.add_data("G1", "p_max", ConstantData(410))
    database.add_data("G1", "p_min", ConstantData(180))
    database.add_data("G1", "cost", ConstantData(96))
    database.add_data("G1", "startup_cost", ConstantData(100500))
    database.add_data("G1", "fixed_cost", ConstantData(1))
    database.add_data("G1", "d_min_up", ConstantData(8))
    database.add_data("G1", "d_min_down", ConstantData(8))
    database.add_data("G1", "nb_units_min", lower_bound["G1"])
    database.add_data("G1", "nb_units_max", TimeScenarioSeriesData(max_units_1))
    database.add_data("G1", "max_generating", TimeScenarioSeriesData(failures_1))
    database.add_data("G1", "min_generating", lower_bound["G1"])
    database.add_data("G1", "max_failure", TimeScenarioSeriesData(max_failures_1))
    database.add_data(
        "G1",
        "nb_units_max_min_down_time",
        TimeScenarioSeriesData(nb_units_max_min_down_time_1),
    )

    database.add_data("G2", "p_max", ConstantData(90))
    database.add_data("G2", "p_min", ConstantData(60))
    database.add_data("G2", "cost", ConstantData(137))
    database.add_data("G2", "startup_cost", ConstantData(24500))
    database.add_data("G2", "fixed_cost", ConstantData(1))
    database.add_data("G2", "d_min_up", ConstantData(11))
    database.add_data("G2", "d_min_down", ConstantData(11))
    database.add_data("G2", "nb_units_min", lower_bound["G2"])
    database.add_data("G2", "nb_units_max", ConstantData(3))
    database.add_data("G2", "max_generating", ConstantData(270))
    database.add_data("G2", "min_generating", lower_bound["G2"])
    database.add_data("G2", "max_failure", ConstantData(0))
    database.add_data("G2", "nb_units_max_min_down_time", ConstantData(3))

    failures_3 = pd.DataFrame(
        np.repeat(get_failures_for_cluster3(week, scenario), 24),
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    max_units_3 = get_max_unit(275, 4, failures_3)
    max_failures_3 = get_max_failures(max_units_3)
    nb_units_max_min_down_time_3 = get_max_unit_for_min_down_time(9, max_units_3)

    database.add_data("G3", "p_max", ConstantData(275))
    database.add_data("G3", "p_min", ConstantData(150))
    database.add_data("G3", "cost", ConstantData(107))
    database.add_data("G3", "startup_cost", ConstantData(69500))
    database.add_data("G3", "fixed_cost", ConstantData(1))
    database.add_data("G3", "d_min_up", ConstantData(9))
    database.add_data("G3", "d_min_down", ConstantData(9))
    database.add_data("G3", "nb_units_min", lower_bound["G3"])
    database.add_data("G3", "nb_units_max", TimeScenarioSeriesData(max_units_3))
    database.add_data("G3", "max_generating", TimeScenarioSeriesData(failures_3))
    database.add_data("G3", "min_generating", lower_bound["G3"])
    database.add_data("G3", "max_failure", TimeScenarioSeriesData(max_failures_3))
    database.add_data(
        "G3",
        "nb_units_max_min_down_time",
        TimeScenarioSeriesData(nb_units_max_min_down_time_3),
    )

    database.add_data("U", "cost", ConstantData(10000))
    database.add_data("S", "cost", ConstantData(1))

    output_file = open(
        "tests/functional/data_complex_case/milp/"
        + str(scenario)
        + "/values-hourly.txt",
        "r",
    )
    output = output_file.readlines()

    demand_data = pd.DataFrame(
        data=[
            float(line.strip().split("\t")[10])
            for line in output[168 * week + 7 : 168 * week + 7 + 168]
        ],
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    demand_data[0] = demand_data[0] - 300

    demand_time_scenario_series = TimeScenarioSeriesData(demand_data)
    database.add_data("D", "demand", demand_time_scenario_series)
    return database


def get_failures_for_cluster3(week: int, scenario: int) -> List:
    if scenario == 0:
        if week == 0:
            failures_3 = [1100, 1100, 0, 1100, 1100, 1100, 1100]
        elif week == 1:
            failures_3 = [1100, 1100, 1100, 1100, 1100, 0, 1100]
    elif scenario == 1:
        failures_3 = [1100, 1100, 1100, 1100, 1100, 1100, 1100]

    return failures_3


def get_failures_for_cluster1(week: int, scenario: int) -> List:
    if scenario == 0:
        failures = [410, 410, 410, 410, 410, 410, 410]
    elif scenario == 1:
        failures = [410, 410, 410, 410, 0, 410, 410]

    return failures


def create_problem_accurate_heuristic(
    lower_bound: Dict[str, AbstractDataStructure],
    number_hours: int,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> OptimizationProblem:

    database = generate_database(
        lower_bound=lower_bound, number_hours=number_hours, week=week, scenario=scenario
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
    lower_bound: AbstractDataStructure,
    number_hours: int,
    thermal_cluster: str,
    week: int,
    scenario: int,
) -> pd.DataFrame:

    delta = {"G1": 8, "G2": 11, "G3": 9}[thermal_cluster]
    pmin = {"G1": 180, "G2": 60, "G3": 150}[thermal_cluster]
    pdispo = {
        "G1": np.reshape(
            np.repeat(get_failures_for_cluster1(week, scenario), 24), (number_hours, 1)
        ),
        "G2": np.array(270),
        "G3": np.reshape(
            np.repeat(get_failures_for_cluster3(week, scenario), 24), (number_hours, 1)
        ),
    }[thermal_cluster]
    nmax = {"G1": 1, "G2": 3, "G3": 4}[thermal_cluster]

    # nopt = {
    #     "G1": np.ones((number_hours)),
    #     "G2": np.array(
    #         [
    #             (
    #                 3.0
    #                 if i in list(range(50, 72))
    #                 else (1.0 if i in list(range(39, 50)) else 0.0)
    #             )
    #             for i in range(number_hours)
    #         ]
    #     ),
    # }[thermal_cluster]
    number_blocks = number_hours // delta

    database = DataBase()

    database.add_data("B", "n_max", ConstantData(nmax))
    database.add_data("B", "delta", ConstantData(delta))
    database.add_data("B", "n_guide", lower_bound)
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
    parameters.SetDoubleParam(parameters.RELATIVE_MIP_GAP, 1e-7)
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
