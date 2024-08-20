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

from math import ceil
from pathlib import Path
from typing import List

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
from andromede.study.parsing import InputComponents
from andromede.thermal_heuristic.cluster_parameter import compute_slot_length
from andromede.thermal_heuristic.model import (
    AccurateModelBuilder,
    FastModelBuilder,
    HeuristicAccurateModelBuilder,
    HeuristicFastModelBuilder,
    Model,
)
from andromede.thermal_heuristic.problem import (
    BlockScenarioIndex,
    SolvingParameters,
    ThermalProblemBuilder,
    TimeScenarioHourParameter,
    get_database,
    get_heuristic_components,
    get_input_components,
    get_network,
)
from tests.functional.conftest import ExpectedOutput, ExpectedOutputIndexes
from tests.functional.libs.lib_thermal_heuristic import (
    THERMAL_CLUSTER_MODEL_MILP,
    UPPER_BOUND_ON_SUM_OF_GENERATION,
)


@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent / "data/thermal_heuristic_two_clusters_with_bc"


@pytest.fixture
def models() -> list[Model]:
    return [
        DEMAND_MODEL,
        NODE_BALANCE_MODEL,
        SPILLAGE_MODEL,
        UNSUPPLIED_ENERGY_MODEL,
        UPPER_BOUND_ON_SUM_OF_GENERATION,
    ]


@pytest.fixture
def input_components(data_path: Path) -> InputComponents:
    return get_input_components(data_path / "components.yml")


@pytest.fixture
def heuristic_components(input_components: InputComponents) -> List[str]:
    return get_heuristic_components(input_components, THERMAL_CLUSTER_MODEL_MILP.id)


@pytest.fixture
def time_scenario_parameters() -> TimeScenarioHourParameter:
    return TimeScenarioHourParameter(1, 1, 168)


@pytest.fixture
def week_scenario_index() -> BlockScenarioIndex:
    return BlockScenarioIndex(0, 0)


def test_milp_version(
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    data_path: Path,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """Solve weekly problem with two clusters and a binding constraint between these two clusters.
    The optimal solution consists in turning on the first unit all the and the second unit which is more expensive but more flexible when the load increases at the 13th timestep.
    """
    network = get_network(
        input_components,
        port_types=[BALANCE_PORT_TYPE],
        models=[THERMAL_CLUSTER_MODEL_MILP] + models,
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

    main_resolution_step = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    assert main_resolution_step.objective == 16822864

    expected_output = ExpectedOutput(
        mode="milp",
        index=week_scenario_index,
        dir_path=data_path,
        list_cluster=heuristic_components,
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
        ),
    )
    expected_output.check_output_values(main_resolution_step.output)


def test_lp_version(
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    data_path: Path,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """Solve the same problem as before with linear relaxation. The linear relaxation solution consists in turning one the first unit all the time and keep off the second unit."""
    network = get_network(
        input_components,
        port_types=[BALANCE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model] + models,
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

    main_resolution_step = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    assert main_resolution_step.objective == pytest.approx(16802840.55)

    expected_output = ExpectedOutput(
        mode="lp",
        index=week_scenario_index,
        dir_path=data_path,
        list_cluster=heuristic_components,
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
        ),
    )
    expected_output.check_output_values(main_resolution_step.output)


def test_accurate_heuristic(
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    data_path: Path,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares. The accurate heuristic decides to turn on 3 units of the first cluster but due to the binding constraint and p_min, the problem become infeasible.
    """

    number_hours = 168

    network = get_network(
        input_components,
        port_types=[BALANCE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model] + models,
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

    # First optimization
    resolution_step_1 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    # Get number of on units and round it to integer
    thermal_problem_builder.update_database_heuristic(
        resolution_step_1.output,
        week_scenario_index,
        heuristic_components,
        param_to_update="nb_units_min",
        var_to_read="nb_on",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )

    for g in heuristic_components:
        for time_step in range(number_hours):
            assert thermal_problem_builder.database.get_value(
                ComponentParameterIndex(g, "nb_units_min"), time_step, 0
            ) == (2 if time_step != 12 and g == "G1" else (3 if g == "G1" else 0))

        # Solve heuristic problem
        resolution_step_accurate_heuristic = (
            thermal_problem_builder.heuristic_resolution_step(
                week_scenario_index,
                id_component=g,
                model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model,
            )
        )

        thermal_problem_builder.update_database_heuristic(
            resolution_step_accurate_heuristic.output,
            week_scenario_index,
            [g],
            param_to_update="nb_units_min",
            var_to_read="nb_on",
            fn_to_apply=lambda x: ceil(round(x, 12)),
        )

        for time_step in range(number_hours):
            assert thermal_problem_builder.database.get_value(
                ComponentParameterIndex(g, "nb_units_min"), time_step, 0
            ) == (2 if time_step != 12 and g == "G1" else (3 if g == "G1" else 0))

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index,
        SolvingParameters(expected_status=pywraplp.Solver.INFEASIBLE),
    )


def test_fast_heuristic(
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    data_path: Path,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """Solve the same problem as before with the heuristic fast of Antares. The fast heuristic decides to turn on 3 units of the first cluster but due to the binding constraint and p_min, the problem become infeasible."""

    number_hours = 168

    network = get_network(
        input_components,
        port_types=[BALANCE_PORT_TYPE],
        models=[FastModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model] + models,
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

    # First optimization
    resolution_step_1 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    thermal_problem_builder.update_database_heuristic(
        resolution_step_1.output,
        week_scenario_index,
        list_cluster_id=heuristic_components,
        var_to_read="generation",
        param_to_update="n_guide",
        fn_to_apply=lambda x, y: ceil(round(x / y, 12)),
        param_needed_to_compute=["p_max"],
    )

    for g in heuristic_components:
        # Solve heuristic problem
        resolution_step_heuristic = thermal_problem_builder.heuristic_resolution_step(
            id_component=g,
            index=week_scenario_index,
            model=HeuristicFastModelBuilder(
                number_hours,
                slot_length=compute_slot_length(g, thermal_problem_builder.database),
            ).model,
        )
        thermal_problem_builder.update_database_heuristic(
            resolution_step_heuristic.output,
            week_scenario_index,
            [g],
            var_to_read="n",
            param_to_update="min_generating",
            fn_to_apply=lambda x, y, z: min(x * y, z),
            param_needed_to_compute=["p_min", "max_generating"],
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
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index,
        SolvingParameters(expected_status=pywraplp.Solver.INFEASIBLE),
    )
