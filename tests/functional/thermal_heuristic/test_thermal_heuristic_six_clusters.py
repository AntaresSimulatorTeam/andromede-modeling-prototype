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
from typing import List

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd
import pytest

from andromede.simulation import OutputValues
from andromede.study import TimeScenarioSeriesData
from andromede.study.data import ComponentParameterIndex
from andromede.study.parsing import InputComponents
from andromede.thermal_heuristic.cluster_parameter import compute_slot_length
from andromede.thermal_heuristic.model import (
    AccurateModelBuilder,
    FastModelBuilder,
    HeuristicAccurateModelBuilder,
    HeuristicFastModelBuilder,
)
from andromede.thermal_heuristic.problem import (
    BlockScenarioIndex,
    ThermalProblemBuilder,
    TimeScenarioHourParameter,
    get_database,
    get_network,
)
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP


@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent.parent / "data/thermal_heuristic_six_clusters"


def test_accurate_heuristic(
    solver_parameters: pywraplp.MPSolverParameters,
    data_path: Path,
    week_scenario_index: BlockScenarioIndex,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """
    Check that the accurate heuristic finds the same solution in the POC and in Antares with the same input generated by Antares.
    """

    number_hours = 168
    network = get_network(
        input_components,
        port_types=[],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model],
    )
    database = get_database(
        input_components,
        data_path,
        fast=False,
        cluster=heuristic_components,
        time_scenario_hour_parameter=time_scenario_parameters,
    )

    thermal_problem_builder = ThermalProblemBuilder(
        network=network,
        database=database,
        time_scenario_hour_parameter=time_scenario_parameters,
    )

    for j, cluster in enumerate(heuristic_components):
        input_data = np.loadtxt(data_path / "accurate/itr1_accurate_cluster{j+1}.txt")
        nb_on_1 = pd.DataFrame(
            np.transpose(np.ceil(np.round(input_data, 12))),
            index=list(range(number_hours)),
            columns=[week_scenario_index.scenario],
        )
        thermal_problem_builder.database.add_data(
            cluster, "nb_units_min", TimeScenarioSeriesData(nb_on_1)
        )

        # Solve heuristic problem
        resolution_step_accurate_heuristic = (
            thermal_problem_builder.heuristic_resolution_step(
                index=week_scenario_index,
                id_component=cluster,
                model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model,
            )
        )
        status = resolution_step_accurate_heuristic.solver.Solve(solver_parameters)
        assert status == pywraplp.Solver.OPTIMAL

        nb_on_heuristic = np.transpose(
            np.ceil(
                np.array(
                    OutputValues(resolution_step_accurate_heuristic)
                    .component(cluster)
                    .var("nb_on")
                    .value
                )
            )
        )

        expected_output = np.loadtxt(
            data_path / "accurate/itr2_accurate_cluster{j+1}.txt"
        )
        assert list(nb_on_heuristic[:, 0]) == [
            pytest.approx(x) for x in expected_output
        ]


def test_fast_heuristic(
    data_path: Path,
    week_scenario_index: BlockScenarioIndex,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """
    Check that the fast heuristic finds the same solution in the POC and in Antares with the same input generated by Antares.
    """
    number_hours = 168

    network = get_network(
        input_components,
        port_types=[],
        models=[FastModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model],
    )
    database = get_database(
        input_components,
        data_path,
        fast=True,
        cluster=heuristic_components,
        time_scenario_hour_parameter=time_scenario_parameters,
    )

    thermal_problem_builder = ThermalProblemBuilder(
        network=network,
        database=database,
        time_scenario_hour_parameter=time_scenario_parameters,
    )

    for j, cluster in enumerate(heuristic_components):
        pmax = thermal_problem_builder.database.get_value(
            ComponentParameterIndex(cluster, "p_max"), 0, 0
        )
        input_data = np.loadtxt(data_path / "fast/itr1_fast_cluster{j+1}.txt")

        nb_on_1 = pd.DataFrame(
            np.ceil(np.round(input_data / pmax, 12)),  # type: ignore
            index=list(range(number_hours)),
            columns=[week_scenario_index.scenario],
        )

        thermal_problem_builder.database.add_data(
            cluster, "n_guide", TimeScenarioSeriesData(nb_on_1)
        )

        # Solve heuristic problem
        resolution_step_heuristic = thermal_problem_builder.heuristic_resolution_step(
            id_component=cluster,
            index=week_scenario_index,
            model=HeuristicFastModelBuilder(
                number_hours,
                slot_length=compute_slot_length(
                    cluster, thermal_problem_builder.database
                ),
            ).model,
        )
        status = resolution_step_heuristic.solver.Solve()
        assert status == pywraplp.Solver.OPTIMAL

        thermal_problem_builder.update_database_heuristic(
            OutputValues(resolution_step_heuristic),
            week_scenario_index,
            [cluster],
            var_to_read="n",
            param_to_update="min_generating",
            fn_to_apply=lambda x, y, z: min(x * y, z),
            param_needed_to_compute=["p_min", "max_generating"],
        )

        expected_output = np.loadtxt(data_path / "fast/itr2_fast_cluster{j+1}.txt")
        for t in range(number_hours):
            assert thermal_problem_builder.database.get_value(
                ComponentParameterIndex(cluster, "min_generating"),
                t,
                week_scenario_index.scenario,
            ) == pytest.approx(expected_output[t])