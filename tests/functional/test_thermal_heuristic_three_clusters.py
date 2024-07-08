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

from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    DEMAND_MODEL,
    NODE_BALANCE_MODEL,
    SPILLAGE_MODEL,
    UNSUPPLIED_ENERGY_MODEL,
)
from andromede.simulation import OutputValues
from andromede.study import ConstantData, TimeScenarioSeriesData
from andromede.study.data import AbstractDataStructure
from andromede.thermal_heuristic.data import ExpectedOutput, ExpectedOutputIndexes
from andromede.thermal_heuristic.problem import ThermalProblemBuilder
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP


def test_milp_version() -> None:
    """ """
    number_hours = 168
    scenarios = 2
    output_indexes = ExpectedOutputIndexes(
        idx_generation=4, idx_nodu=12, idx_spillage=20, idx_unsupplied=19
    )

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=False,
        fast=False,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_three_clusters",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[BALANCE_PORT_TYPE],
        models=[
            DEMAND_MODEL,
            NODE_BALANCE_MODEL,
            SPILLAGE_MODEL,
            UNSUPPLIED_ENERGY_MODEL,
        ],
        number_week=2,
        list_scenario=list(range(scenarios)),
    )

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    parameters.SetDoubleParam(parameters.RELATIVE_MIP_GAP, 1e-5)

    for scenario in range(scenarios):
        for week in range(2):
            resolution_step = thermal_problem_builder.get_main_resolution_step(
                week=week,
                scenario=scenario,
            )

            status = resolution_step.solve(parameters)

            assert status == pywraplp.Solver.OPTIMAL

            expected_output = ExpectedOutput(
                mode="milp",
                week=week,
                scenario=scenario,
                dir_path="data/thermal_heuristic_three_clusters",
                list_cluster=["G1", "G2", "G3"],
                output_idx=output_indexes,
            )
            expected_output.check_output_values(resolution_step.output)

            expected_cost = [[78933742, 102103587], [17472101, 17424769]]
            assert resolution_step.objective == pytest.approx(
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

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=True,
        fast=False,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_three_clusters",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[BALANCE_PORT_TYPE],
        models=[
            DEMAND_MODEL,
            NODE_BALANCE_MODEL,
            SPILLAGE_MODEL,
            UNSUPPLIED_ENERGY_MODEL,
        ],
        number_week=2,
        list_scenario=list(range(scenarios)),
    )

    for scenario in range(scenarios):
        for week in range(2):
            # First optimization
            resolution_step_1 = thermal_problem_builder.get_main_resolution_step(
                week=week,
                scenario=scenario,
            )
            status = resolution_step_1.solve(parameters)
            assert status == pywraplp.Solver.OPTIMAL

            thermal_problem_builder.update_database_accurate(
                resolution_step_1.output, week, scenario, None
            )

            for g in ["G1", "G2", "G3"]:
                # Solve heuristic problem
                resolution_step_accurate_heuristic = (
                    thermal_problem_builder.get_resolution_step_accurate_heuristic(
                        week=week,
                        scenario=scenario,
                        cluster_id=g,
                    )
                )
                status = resolution_step_accurate_heuristic.solve(parameters)
                assert status == pywraplp.Solver.OPTIMAL

                thermal_problem_builder.update_database_accurate(
                    resolution_step_accurate_heuristic.output, week, scenario, [g]
                )

            # Second optimization with lower bound modified
            resolution_step_2 = thermal_problem_builder.get_main_resolution_step(
                week=week,
                scenario=scenario,
            )
            status = resolution_step_2.solve(parameters)
            assert status == pywraplp.Solver.OPTIMAL

            expected_output = ExpectedOutput(
                mode="accurate",
                week=week,
                scenario=scenario,
                dir_path="data/thermal_heuristic_three_clusters",
                list_cluster=["G1", "G2", "G3"],
                output_idx=output_indexes,
            )
            expected_output.check_output_values(resolution_step_2.output)

            expected_cost = [
                [78996726, 102215087 - 69500],
                [17589534, 17641808],
            ]
            assert resolution_step_2.objective == pytest.approx(
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

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=True,
        fast=True,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_three_clusters",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[BALANCE_PORT_TYPE],
        models=[
            DEMAND_MODEL,
            NODE_BALANCE_MODEL,
            SPILLAGE_MODEL,
            UNSUPPLIED_ENERGY_MODEL,
        ],
        number_week=2,
        list_scenario=list(range(scenarios)),
    )

    for scenario in range(scenarios):
        for week in range(weeks):
            # First optimization
            resolution_step_1 = thermal_problem_builder.get_main_resolution_step(
                week=week,
                scenario=scenario,
            )
            status = resolution_step_1.solve(parameters)
            assert status == pywraplp.Solver.OPTIMAL

            thermal_problem_builder.update_database_fast_before_heuristic(
                resolution_step_1.output, week, scenario
            )

            for g in ["G1", "G2", "G3"]:  #
                resolution_step_heuristic = (
                    thermal_problem_builder.get_resolution_step_fast_heuristic(
                        thermal_cluster=g,
                        week=week,
                        scenario=scenario,
                    )
                )
                status = resolution_step_heuristic.solve()
                assert status == pywraplp.Solver.OPTIMAL

                thermal_problem_builder.update_database_fast_after_heuristic(
                    resolution_step_heuristic.output, week, scenario, [g]
                )

            # Second optimization with lower bound modified
            resolution_step_2 = thermal_problem_builder.get_main_resolution_step(
                week=week,
                scenario=scenario,
            )
            status = resolution_step_2.solve(parameters)
            assert status == pywraplp.Solver.OPTIMAL

            expected_output = ExpectedOutput(
                mode="fast",
                week=week,
                scenario=scenario,
                dir_path="data/thermal_heuristic_three_clusters",
                list_cluster=["G1", "G2", "G3"],
                output_idx=output_indexes,
            )
            expected_output.check_output_values(
                resolution_step_2.output,
            )

            expected_cost = [
                [79277215 - 630089, 102461792 - 699765],
                [17803738 - 661246, 17720390 - 661246],
            ]
            assert resolution_step_2.objective == pytest.approx(
                expected_cost[scenario][week]
            )
