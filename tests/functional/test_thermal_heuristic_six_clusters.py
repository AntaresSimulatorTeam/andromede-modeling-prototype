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

from andromede.study import TimeScenarioSeriesData
from andromede.study.data import ComponentParameterIndex
from andromede.thermal_heuristic.model import (
    AccurateModelBuilder,
    FastModelBuilder,
    HeuristicAccurateModelBuilder,
    HeuristicFastModelBuilder,
)
from andromede.thermal_heuristic.problem import (
    ThermalProblemBuilder,
    TimeScenarioHourParameter,
    WeekScenarioIndex,
)
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP


@pytest.fixture
def solver_parameters() -> pywraplp.MPSolverParameters:
    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)
    return parameters


@pytest.fixture
def data_path() -> str:
    return "data/thermal_heuristic_six_clusters"


@pytest.fixture
def week_scenario_index() -> WeekScenarioIndex:
    return WeekScenarioIndex(0, 0)


def test_accurate_heuristic(
    solver_parameters: pywraplp.MPSolverParameters,
    data_path: str,
    week_scenario_index: WeekScenarioIndex,
) -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168

    thermal_problem_builder = ThermalProblemBuilder(
        fast=False,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_MODEL_MILP.id,
        port_types=[],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model],
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, number_hours),
    )

    for j, cluster in enumerate(
        thermal_problem_builder.get_milp_heuristic_components()
    ):
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
            index=list(range(number_hours)),
            columns=[week_scenario_index.scenario],
        )
        thermal_problem_builder.database.add_data(
            cluster, "nb_units_min", TimeScenarioSeriesData(nb_on_1)
        )

        # Solve heuristic problem
        resolution_step_accurate_heuristic = (
            thermal_problem_builder.get_resolution_step_heuristic(
                index=week_scenario_index,
                id=cluster,
                model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model,
            )
        )
        resolution_step_accurate_heuristic.solve(solver_parameters)

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


def test_fast_heuristic(data_path: str, week_scenario_index: WeekScenarioIndex) -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """
    number_hours = 168

    thermal_problem_builder = ThermalProblemBuilder(
        fast=True,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_MODEL_MILP.id,
        port_types=[],
        models=[FastModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model],
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, number_hours),
    )

    for j, cluster in enumerate(
        thermal_problem_builder.get_milp_heuristic_components()
    ):
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
            index=list(range(number_hours)),
            columns=[week_scenario_index.scenario],
        )

        thermal_problem_builder.database.add_data(
            cluster, "n_guide", TimeScenarioSeriesData(nb_on_1)
        )

        # Solve heuristic problem
        resolution_step_heuristic = (
            thermal_problem_builder.get_resolution_step_heuristic(
                id=cluster,
                index=week_scenario_index,
                model=HeuristicFastModelBuilder(
                    number_hours, delta=thermal_problem_builder.compute_delta(cluster)
                ).model,
            )
        )

        resolution_step_heuristic.solve()

        thermal_problem_builder.update_database_fast_after_heuristic(
            resolution_step_heuristic.output, week_scenario_index, [cluster]
        )

        expected_output = np.loadtxt(
            f"tests/functional/data/thermal_heuristic_six_clusters/fast/itr2_fast_cluster{j+1}.txt"
        )
        for t in range(number_hours):
            assert thermal_problem_builder.database.get_value(
                ComponentParameterIndex(cluster, "min_generating"),
                t,
                week_scenario_index.scenario,
            ) == pytest.approx(expected_output[t])
