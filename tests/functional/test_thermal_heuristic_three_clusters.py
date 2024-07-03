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
from typing import Dict

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd
import pytest

from andromede.simulation import OutputValues
from andromede.study import ConstantData, TimeScenarioSeriesData
from andromede.study.data import AbstractDataStructure
from andromede.thermal_heuristic.data import ExpectedOutput, ExpectedOutputIndexes
from andromede.thermal_heuristic.problem import (
    create_main_problem,
    create_problem_accurate_heuristic,
    create_problem_fast_heuristic,
)


def test_milp_version() -> None:
    """ """
    number_hours = 168
    scenarios = 2
    output_indexes = ExpectedOutputIndexes(
        idx_generation=4, idx_nodu=12, idx_spillage=20, idx_unsupplied=19
    )

    for scenario in range(scenarios):
        for week in range(2):
            problem = create_main_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=False,
                fast=False,
                week=week,
                scenario=scenario,
                data_dir=Path(__file__).parent
                / "data/thermal_heuristic_three_clusters",
            )

            parameters = pywraplp.MPSolverParameters()
            parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
            parameters.SetIntegerParam(parameters.SCALING, 0)
            parameters.SetDoubleParam(parameters.RELATIVE_MIP_GAP, 1e-5)

            status = problem.solver.Solve(parameters)

            assert status == problem.solver.OPTIMAL

            expected_output = ExpectedOutput(
                mode="milp",
                week=week,
                scenario=scenario,
                dir_path="data/thermal_heuristic_three_clusters",
                list_cluster=["G1", "G2", "G3"],
                output_idx=output_indexes,
            )
            expected_output.check_output_values(
                problem,
            )

            expected_cost = [[78933742, 102103587], [17472101, 17424769]]
            assert problem.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    output_indexes = ExpectedOutputIndexes(
        idx_generation=4, idx_nodu=12, idx_spillage=21, idx_unsupplied=20
    )

    number_hours = 168
    scenarios = 2

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for scenario in range(scenarios):
        for week in range(2):
            # First optimization
            problem_optimization_1 = create_main_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=True,
                fast=False,
                week=week,
                scenario=scenario,
                data_dir=Path(__file__).parent
                / "data/thermal_heuristic_three_clusters",
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
                    week=week,
                    scenario=scenario,
                    data_dir=Path(__file__).parent
                    / "data/thermal_heuristic_three_clusters",
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
            problem_optimization_2 = create_main_problem(
                nb_on_min,
                number_hours,
                lp_relaxation=True,
                fast=False,
                week=week,
                scenario=scenario,
                data_dir=Path(__file__).parent
                / "data/thermal_heuristic_three_clusters",
            )
            status = problem_optimization_2.solver.Solve(parameters)

            assert status == problem_optimization_2.solver.OPTIMAL

            expected_output = ExpectedOutput(
                mode="accurate",
                week=week,
                scenario=scenario,
                dir_path="data/thermal_heuristic_three_clusters",
                list_cluster=["G1", "G2", "G3"],
                output_idx=output_indexes,
            )
            expected_output.check_output_values(
                problem_optimization_2,
            )

            expected_cost = [
                [78996726, 102215087 - 69500],
                [17589534, 17641808],
            ]
            assert problem_optimization_2.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """
    output_indexes = ExpectedOutputIndexes(
        idx_generation=4, idx_nodu=12, idx_spillage=21, idx_unsupplied=20
    )

    number_hours = 168
    scenarios = 2
    weeks = 2

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for scenario in range(scenarios):
        for week in range(weeks):
            # First optimization
            problem_optimization_1 = create_main_problem(
                {"G1": ConstantData(0), "G2": ConstantData(0), "G3": ConstantData(0)},
                number_hours,
                lp_relaxation=True,
                fast=True,
                week=week,
                scenario=scenario,
                data_dir=Path(__file__).parent
                / "data/thermal_heuristic_three_clusters",
            )
            status = problem_optimization_1.solver.Solve(parameters)

            assert status == problem_optimization_1.solver.OPTIMAL

            # Get number of on units
            output_1 = OutputValues(problem_optimization_1)

            # Solve heuristic problem
            mingen: Dict[str, AbstractDataStructure] = {}
            for g in ["G1", "G2", "G3"]:  #
                mingen_heuristic = create_problem_fast_heuristic(
                    output_1.component(g).var("generation").value[0],  # type:ignore
                    number_hours,
                    thermal_cluster=g,
                    week=week,
                    scenario=scenario,
                    data_dir=Path(__file__).parent
                    / "data/thermal_heuristic_three_clusters",
                )

                mingen[g] = TimeScenarioSeriesData(mingen_heuristic)

            # Second optimization with lower bound modified
            problem_optimization_2 = create_main_problem(
                mingen,
                number_hours,
                lp_relaxation=True,
                fast=True,
                week=week,
                scenario=scenario,
                data_dir=Path(__file__).parent
                / "data/thermal_heuristic_three_clusters",
            )
            status = problem_optimization_2.solver.Solve(parameters)

            assert status == problem_optimization_2.solver.OPTIMAL

            expected_output = ExpectedOutput(
                mode="fast",
                week=week,
                scenario=scenario,
                dir_path="data/thermal_heuristic_three_clusters",
                list_cluster=["G1", "G2", "G3"],
                output_idx=output_indexes,
            )
            expected_output.check_output_values(
                problem_optimization_2,
            )

            expected_cost = [
                [79277215 - 630089, 102461792 - 699765],
                [17803738 - 661246, 17720390 - 661246],
            ]
            assert problem_optimization_2.solver.Objective().Value() == pytest.approx(
                expected_cost[scenario][week]
            )
