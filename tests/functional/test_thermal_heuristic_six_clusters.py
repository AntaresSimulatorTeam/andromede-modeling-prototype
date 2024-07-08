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

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd
import pytest

from andromede.simulation import OutputValues
from andromede.study import ConstantData, TimeScenarioSeriesData
from andromede.study.data import ComponentParameterIndex
from andromede.thermal_heuristic.problem import ThermalProblemBuilder
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168
    scenario = 0
    week = 0

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=True,
        fast=False,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_six_clusters",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[],
        models=[],
        number_week=1,
        list_scenario=list(range(1)),
    )

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for j, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):
        nb_on_1 = pd.DataFrame(
            np.transpose(
                np.ceil(
                    np.round(
                        np.loadtxt(
                            f"tests/functional/data/thermal_heuristic_six_clusters/accurate/itr1_accurate_cluster{j+1}.txt"
                        ),
                        12,
                    )
                )
            ),
            index=list(range(week * number_hours, (week + 1) * number_hours)),
            columns=[scenario],
        )
        thermal_problem_builder.database.add_data(
            cluster, "nb_units_min", TimeScenarioSeriesData(nb_on_1)
        )

        # Solve heuristic problem
        resolution_step_accurate_heuristic = (
            thermal_problem_builder.get_resolution_step_accurate_heuristic(
                week=week,
                scenario=scenario,
                cluster_id=cluster,
            )
        )
        status = resolution_step_accurate_heuristic.solve(parameters)

        assert status == pywraplp.Solver.OPTIMAL

        nb_on_heuristic = np.transpose(
            np.ceil(
                np.array(
                    resolution_step_accurate_heuristic.output.component(cluster)
                    .var("nb_on")
                    .value
                )
            )
        )

        expected_output = np.loadtxt(
            f"tests/functional/data/thermal_heuristic_six_clusters/accurate/itr2_accurate_cluster{j+1}.txt"
        )
        assert list(nb_on_heuristic[:, 0]) == [
            pytest.approx(x) for x in expected_output
        ]


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """
    number_hours = 168
    scenario = 0
    week = 0

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=True,
        fast=True,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_six_clusters",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[],
        models=[],
        number_week=1,
        list_scenario=list(range(1)),
    )

    for j, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):
        pmax = thermal_problem_builder.database.get_value(
            ComponentParameterIndex(cluster, "p_max"), 0, 0
        )
        nb_on_1 = pd.DataFrame(
            np.ceil(
                np.round(
                    np.loadtxt(
                        f"tests/functional/data/thermal_heuristic_six_clusters/fast/itr1_fast_cluster{j+1}.txt"
                    )  # type: ignore
                    / pmax,
                    12,
                )
            ),
            index=list(range(week * number_hours, (week + 1) * number_hours)),
            columns=[scenario],
        )

        thermal_problem_builder.database.add_data(
            cluster, "n_guide", TimeScenarioSeriesData(nb_on_1)
        )

        # Solve heuristic problem
        resolution_step_heuristic = (
            thermal_problem_builder.get_resolution_step_fast_heuristic(
                thermal_cluster=cluster,
                week=week,
                scenario=scenario,
            )
        )

        status = resolution_step_heuristic.solve()
        assert status == pywraplp.Solver.OPTIMAL
        thermal_problem_builder.update_database_fast_after_heuristic(
            resolution_step_heuristic.output, week, scenario, [cluster]
        )

        expected_output = np.loadtxt(
            f"tests/functional/data/thermal_heuristic_six_clusters/fast/itr2_fast_cluster{j+1}.txt"
        )
        for t in range(number_hours):
            assert thermal_problem_builder.database.get_value(
                ComponentParameterIndex(cluster, "min_generating"), t, scenario
            ) == pytest.approx(expected_output[t])
