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

import ortools.linear_solver.pywraplp as pywraplp
import pytest

from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    DEMAND_MODEL,
    NODE_BALANCE_MODEL,
    SPILLAGE_MODEL,
    UNSUPPLIED_ENERGY_MODEL,
)
from andromede.study.data import ComponentParameterIndex
from andromede.thermal_heuristic.data import ExpectedOutput, ExpectedOutputIndexes
from andromede.thermal_heuristic.model import (
    Model,
    AccurateModelBuilder,
    FastModelBuilder,
    HeuristicAccurateModelBuilder,
    HeuristicFastModelBuilder,
)
from andromede.thermal_heuristic.problem import (
    ThermalProblemBuilder,
    TimeScenarioHourParameter,
)
from tests.functional.libs.lib_thermal_heuristic import (
    BINDING_CONSTRAINT,
    THERMAL_CLUSTER_MODEL_MILP,
)


@pytest.fixture
def data_path() -> str:
    return "data/thermal_heuristic_two_clusters_with_bc"


@pytest.fixture
def models() -> list[Model]:
    return [
        DEMAND_MODEL,
        NODE_BALANCE_MODEL,
        SPILLAGE_MODEL,
        UNSUPPLIED_ENERGY_MODEL,
        BINDING_CONSTRAINT,
    ]


def test_milp_version(data_path: str, models: list[Model]) -> None:
    """ """
    thermal_problem_builder = ThermalProblemBuilder(
        fast=False,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_MODEL_MILP.id,
        port_types=[BALANCE_PORT_TYPE],
        models=[THERMAL_CLUSTER_MODEL_MILP] + models,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, 168),
    )

    main_resolution_step = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    main_resolution_step.solve()

    assert main_resolution_step.objective == 16822864

    expected_output = ExpectedOutput(
        mode="milp",
        week=0,
        scenario=0,
        dir_path=data_path,
        list_cluster=thermal_problem_builder.get_milp_heuristic_components(),
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
        ),
    )
    expected_output.check_output_values(main_resolution_step.output)


def test_lp_version(data_path: str, models: list[Model]) -> None:
    """ """

    thermal_problem_builder = ThermalProblemBuilder(
        fast=False,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_MODEL_MILP.id,
        port_types=[BALANCE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model] + models,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, 168),
    )

    main_resolution_step = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    main_resolution_step.solve()

    assert main_resolution_step.objective == pytest.approx(16802840.55)

    expected_output = ExpectedOutput(
        mode="lp",
        week=0,
        scenario=0,
        dir_path=data_path,
        list_cluster=thermal_problem_builder.get_milp_heuristic_components(),
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
        ),
    )
    expected_output.check_output_values(main_resolution_step.output)


def test_accurate_heuristic(data_path: str, models: list[Model]) -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    thermal_problem_builder = ThermalProblemBuilder(
        fast=False,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_MODEL_MILP.id,
        port_types=[BALANCE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model] + models,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, 168),
    )

    # First optimization
    resolution_step_1 = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    resolution_step_1.solve()

    # Get number of on units and round it to integer
    thermal_problem_builder.update_database_accurate(
        resolution_step_1.output, 0, 0, None
    )

    for g in thermal_problem_builder.get_milp_heuristic_components():
        for time_step in range(
            thermal_problem_builder.time_scenario_hour_parameter.hour
        ):
            assert thermal_problem_builder.database.get_value(
                ComponentParameterIndex(g, "nb_units_min"), time_step, 0
            ) == (2 if time_step != 12 and g == "G1" else (3 if g == "G1" else 0))

        # Solve heuristic problem
        resolution_step_accurate_heuristic = (
            thermal_problem_builder.get_resolution_step_heuristic(
                week=0,
                scenario=0,
                id=g,
                model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model,
            )
        )
        resolution_step_accurate_heuristic.solve()

        thermal_problem_builder.update_database_accurate(
            resolution_step_accurate_heuristic.output, 0, 0, [g]
        )

        for time_step in range(
            thermal_problem_builder.time_scenario_hour_parameter.hour
        ):
            assert thermal_problem_builder.database.get_value(
                ComponentParameterIndex(g, "nb_units_min"), time_step, 0
            ) == (2 if time_step != 12 and g == "G1" else (3 if g == "G1" else 0))

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    resolution_step_2.solve(expected_status=pywraplp.Solver.INFEASIBLE)


def test_fast_heuristic(data_path: str, models: list[Model]) -> None:
    """ """

    number_hours = 168

    thermal_problem_builder = ThermalProblemBuilder(
        fast=True,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_MODEL_MILP.id,
        port_types=[BALANCE_PORT_TYPE],
        models=[FastModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model] + models,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, 168),
    )

    # First optimization
    resolution_step_1 = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    resolution_step_1.solve()

    thermal_problem_builder.update_database_fast_before_heuristic(
        resolution_step_1.output, 0, 0
    )

    for g in thermal_problem_builder.get_milp_heuristic_components():
        # Solve heuristic problem
        resolution_step_heuristic = (
            thermal_problem_builder.get_resolution_step_heuristic(
                id=g,
                week=0,
                scenario=0,
                model=HeuristicFastModelBuilder(
                    number_hours, delta=thermal_problem_builder.compute_delta(g)
                ).model,
            )
        )
        resolution_step_heuristic.solve()
        thermal_problem_builder.update_database_fast_after_heuristic(
            resolution_step_heuristic.output, 0, 0, [g]
        )

        for time_step in range(number_hours):
            assert thermal_problem_builder.database.get_value(
                ComponentParameterIndex(g, "min_generating"), time_step, 0
            ) == (
                3 * 700
                if time_step in [t for t in range(10, 20)] and g == "G1"
                else (2 * 700 if g == "G1" else 0)
            )

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    resolution_step_2.solve(expected_status=pywraplp.Solver.INFEASIBLE)
