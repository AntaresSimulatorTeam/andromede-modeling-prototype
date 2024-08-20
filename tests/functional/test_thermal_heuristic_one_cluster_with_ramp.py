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
    THERMAL_CLUSTER_MODEL_MILP_WITH_RAMP,
)


@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent / "data/thermal_heuristic_one_cluster_with_ramp"


@pytest.fixture
def models() -> list[Model]:
    return [DEMAND_MODEL, NODE_BALANCE_MODEL, SPILLAGE_MODEL, UNSUPPLIED_ENERGY_MODEL]


@pytest.fixture
def week_scenario_index() -> BlockScenarioIndex:
    return BlockScenarioIndex(0, 0)


@pytest.fixture
def input_components(data_path: Path) -> InputComponents:
    return get_input_components(data_path / "components.yml")


@pytest.fixture
def heuristic_components(input_components: InputComponents) -> List[str]:
    return get_heuristic_components(input_components, THERMAL_CLUSTER_MODEL_MILP.id)


@pytest.fixture
def time_scenario_parameters() -> TimeScenarioHourParameter:
    return TimeScenarioHourParameter(1, 1, 168)


def test_milp_version(
    data_path: Path,
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """Solve weekly problem with one cluster and ramp constraints with milp."""

    network = get_network(
        input_components,
        port_types=[BALANCE_PORT_TYPE],
        models=[THERMAL_CLUSTER_MODEL_MILP_WITH_RAMP] + models,
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

    main_resolution_step = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    expected_output = ExpectedOutput(
        mode="milp",
        index=week_scenario_index,
        dir_path=data_path,
        list_cluster=heuristic_components,
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=52, idx_unsupplied=51
        ),
    )
    expected_output.check_output_values(main_resolution_step.output)

    assert (
        sum(
            main_resolution_step.output.component("G")
            .var("nb_start")
            .value[0]  # type:ignore
        )
        == 4
    )
    assert (
        sum(
            main_resolution_step.output.component("G")
            .var("nb_stop")
            .value[0]  # type:ignore
        )
        == 4
    )

    assert main_resolution_step.objective == pytest.approx(29040)


def test_classic_accurate_heuristic(
    data_path: Path,
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """Solve weekly problem with one cluster and ramp constraints with accurate heuristic. The solution found is not integer."""

    number_hours = 168
    network = get_network(
        input_components,
        port_types=[BALANCE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP_WITH_RAMP).model]
        + models,
    )
    database = get_database(
        input_components,
        data_path,
        fast=False,
        cluster=heuristic_components,
        time_scenario_hour_parameter=time_scenario_parameters,
    )

    thermal_problem_builder = ThermalProblemBuilder(
        database=database,
        network=network,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, number_hours),
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
    assert [
        thermal_problem_builder.database.get_value(
            ComponentParameterIndex(heuristic_components[0], "nb_units_min"),
            time_step,
            0,
        )
        for time_step in range(13)
    ] == [0] + [1] * 11 + [0]

    # Solve heuristic problem
    resolution_step_accurate_heuristic = (
        thermal_problem_builder.heuristic_resolution_step(
            week_scenario_index,
            id_component=heuristic_components[0],
            model=HeuristicAccurateModelBuilder(
                THERMAL_CLUSTER_MODEL_MILP_WITH_RAMP
            ).model,
        )
    )

    thermal_problem_builder.update_database_heuristic(
        resolution_step_accurate_heuristic.output,
        week_scenario_index,
        heuristic_components,
        param_to_update="nb_units_min",
        var_to_read="nb_on",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )

    assert [
        thermal_problem_builder.database.get_value(
            ComponentParameterIndex(heuristic_components[0], "nb_units_min"),
            time_step,
            0,
        )
        for time_step in range(13)
    ] == [0] + [1] * 11 + [0]

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    assert resolution_step_2.objective == pytest.approx(29011.4616736)

    assert [
        resolution_step_2.output.component(heuristic_components[0])
        .var("nb_on")
        .value[0][time_step]  # type:ignore
        for time_step in range(13)
    ] == [
        0.0,
        1.0,
        1.0,
        1.0377358490566038,
        1.0733357066571734,
        1.1069204779784654,
        1.1386042245079862,
        1.1129440000000002,
        1.0776,
        1.0399999999999998,
        1.0,
        1.0,
        0.0,
    ]  # non integer !!!!!!

    assert [
        resolution_step_2.output.component(heuristic_components[0])
        .var("nb_start")
        .value[0][time_step]  # type:ignore
        for time_step in range(13)
    ] == [
        0.0,
        1.0,
        0.0,
        0.037735849056603786,
        0.03559985760056958,
        0.033584771321292096,
        0.03168374652952084,
        0.007563135492013902,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]

    assert [
        resolution_step_2.output.component(heuristic_components[0])
        .var("nb_stop")
        .value[0][time_step]  # type:ignore
        for time_step in range(13)
    ] == [
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.03322336000000001,
        0.03534400000000002,
        0.03759999999999999,
        0.04,
        0.0,
        1.0,
    ]


def test_modified_accurate_heuristic(
    data_path: Path,
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """Solve weekly problem with one cluster and ramp constraints with modified accurate heuristic such that the number of on units, starting units and stoping units are fixed at the end of the heuristic."""

    number_hours = 168
    network = get_network(
        input_components,
        port_types=[BALANCE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP_WITH_RAMP).model]
        + models,
    )
    database = get_database(
        input_components,
        data_path,
        fast=False,
        cluster=heuristic_components,
        time_scenario_hour_parameter=time_scenario_parameters,
    )
    thermal_problem_builder = ThermalProblemBuilder(
        database=database,
        network=network,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, number_hours),
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

    # Solve heuristic problem
    resolution_step_accurate_heuristic = (
        thermal_problem_builder.heuristic_resolution_step(
            week_scenario_index,
            id_component=heuristic_components[0],
            model=HeuristicAccurateModelBuilder(
                THERMAL_CLUSTER_MODEL_MILP_WITH_RAMP
            ).model,
        )
    )

    thermal_problem_builder.update_database_heuristic(
        resolution_step_accurate_heuristic.output,
        week_scenario_index,
        heuristic_components,
        param_to_update="nb_units_min",
        var_to_read="nb_on",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )
    thermal_problem_builder.update_database_heuristic(
        resolution_step_accurate_heuristic.output,
        week_scenario_index,
        heuristic_components,
        param_to_update="nb_units_max",
        var_to_read="nb_on",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )
    thermal_problem_builder.update_database_heuristic(
        resolution_step_accurate_heuristic.output,
        week_scenario_index,
        heuristic_components,
        param_to_update="nb_start_max",
        var_to_read="nb_start",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )
    thermal_problem_builder.update_database_heuristic(
        resolution_step_accurate_heuristic.output,
        week_scenario_index,
        heuristic_components,
        param_to_update="nb_stop_max",
        var_to_read="nb_stop",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )

    assert [
        thermal_problem_builder.database.get_value(
            ComponentParameterIndex(heuristic_components[0], "nb_units_min"),
            time_step,
            0,
        )
        for time_step in range(13)
    ] == [0] + [1] * 11 + [0]

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    assert resolution_step_2.objective == pytest.approx(84010)

    expected_output = ExpectedOutput(
        mode="accurate",
        index=week_scenario_index,
        dir_path=data_path,
        list_cluster=heuristic_components,
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=53, idx_unsupplied=52
        ),
    )
    expected_output.check_output_values(resolution_step_2.output)


def test_classic_fast_heuristic(
    data_path: Path,
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """Solve weekly problem with one cluster and ramp constraints with fast heuristic. The solution found is not feasible bevause ramp constraints are not respected if we consider that the number of on units is 1."""

    number_hours = 168

    network = get_network(
        input_components,
        port_types=[BALANCE_PORT_TYPE],
        models=[FastModelBuilder(THERMAL_CLUSTER_MODEL_MILP_WITH_RAMP).model] + models,
    )
    database = get_database(
        input_components,
        data_path,
        fast=True,
        cluster=heuristic_components,
        time_scenario_hour_parameter=time_scenario_parameters,
    )

    thermal_problem_builder = ThermalProblemBuilder(
        database=database,
        network=network,
        time_scenario_hour_parameter=time_scenario_parameters,
    )

    # First optimization
    resolution_step_1 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    assert [
        resolution_step_1.output.component(heuristic_components[0])
        .var("generation")
        .value[0][time_step]  # type:ignore
        for time_step in range(13)
    ] == [0, 50, 100, 150, 200, 250, 300, 250, 200, 150, 100, 50, 0]

    thermal_problem_builder.update_database_heuristic(
        resolution_step_1.output,
        week_scenario_index,
        list_cluster_id=heuristic_components,
        var_to_read="generation",
        param_to_update="n_guide",
        fn_to_apply=lambda x, y: ceil(round(x / y, 12)),
        param_needed_to_compute=["p_max"],
    )
    # Solve heuristic problem
    resolution_step_heuristic = thermal_problem_builder.heuristic_resolution_step(
        id_component=heuristic_components[0],
        index=week_scenario_index,
        model=HeuristicFastModelBuilder(
            number_hours,
            slot_length=compute_slot_length(
                heuristic_components[0], thermal_problem_builder.database
            ),
        ).model,
    )
    thermal_problem_builder.update_database_heuristic(
        resolution_step_heuristic.output,
        week_scenario_index,
        heuristic_components,
        var_to_read="n",
        param_to_update="min_generating",
        fn_to_apply=lambda x, y, z: min(x * y, z),
        param_needed_to_compute=["p_min", "max_generating"],
    )

    assert [
        thermal_problem_builder.database.get_value(
            ComponentParameterIndex(heuristic_components[0], "min_generating"),
            time_step,
            0,
        )
        for time_step in range(13)
    ] == [0] + [100] * 11 + [0]

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    assert resolution_step_2.objective == pytest.approx(29000)

    assert [
        resolution_step_2.output.component(heuristic_components[0])
        .var("generation")
        .value[0][time_step]  # type:ignore
        for time_step in range(13)
    ] == [0, 100, 100, 150, 200, 250, 300, 250, 200, 150, 100, 100, 0]
    # with NODU=1, ramp constraints not respected
