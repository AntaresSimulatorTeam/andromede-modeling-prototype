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

import pytest

from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
)
from andromede.study.data import ComponentParameterIndex
from andromede.thermal_heuristic.data import ExpectedOutput, ExpectedOutputIndexes
from andromede.thermal_heuristic.model import (
    AccurateModelBuilder,
    HeuristicAccurateModelBuilder,
    Model,
)
from andromede.thermal_heuristic.problem import (
    ThermalProblemBuilder,
    TimeScenarioHourParameter,
    WeekScenarioIndex,
)
from tests.functional.libs.lib_thermal_heuristic import (
    THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP,
    NODE_WITH_RESERVE_MODEL,
    DEMAND_WITH_RESERVE_MODEL,
)


@pytest.fixture
def data_path() -> str:
    return "data/thermal_heuristic_day_ahead_reserve"


@pytest.fixture
def models() -> list[Model]:
    return [NODE_WITH_RESERVE_MODEL, DEMAND_WITH_RESERVE_MODEL]


@pytest.fixture
def week_scenario_index() -> WeekScenarioIndex:
    return WeekScenarioIndex(0, 0)


def test_milp_with_day_ahead_reserve(
    data_path: str, models: list[Model], week_scenario_index: WeekScenarioIndex
) -> None:
    """ """
    thermal_problem_builder = ThermalProblemBuilder(
        fast=False,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP.id,
        port_types=[BALANCE_PORT_TYPE],
        models=[THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP] + models,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, 168),
    )

    cluster = thermal_problem_builder.heuristic_components()[0]

    main_resolution_step = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    assert main_resolution_step.objective == 16805387

    expected_output = ExpectedOutput(
        mode="milp",
        index=week_scenario_index,
        dir_path=data_path,
        list_cluster=[cluster],
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
        ),
    )
    expected_output.check_output_values(main_resolution_step.output)


def test_milp_without_day_ahead_reserve(
    data_path: str, models: list[Model], week_scenario_index: WeekScenarioIndex
) -> None:
    """ """
    thermal_problem_builder = ThermalProblemBuilder(
        fast=False,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP.id,
        port_types=[BALANCE_PORT_TYPE],
        models=[THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP] + models,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, 168),
    )

    cluster = thermal_problem_builder.heuristic_components()[0]

    main_resolution_step = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    assert main_resolution_step.objective == 16805387

    expected_output = ExpectedOutput(
        mode="milp",
        index=week_scenario_index,
        dir_path=data_path,
        list_cluster=[cluster],
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
        ),
    )
    expected_output.check_output_values(main_resolution_step.output)


def test_accurate_heuristic_with_day_ahead_reserve(
    data_path: str, models: list[Model], week_scenario_index: WeekScenarioIndex
) -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares. The accurate heuristic is able to retrieve the milp optimal solution because when the number of on units found in the linear relaxation is ceiled, we found the optimal number of on units which is already feasible.
    """

    number_hours = 168
    thermal_problem_builder = ThermalProblemBuilder(
        fast=False,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP.id,
        port_types=[BALANCE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP).model]
        + models,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, number_hours),
    )

    cluster = thermal_problem_builder.heuristic_components()[0]

    # First optimization
    resolution_step_1 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    # Get number of on units and round it to integer
    thermal_problem_builder.update_database_heuristic(
        resolution_step_1.output,
        week_scenario_index,
        None,
        param_to_update="nb_units_min",
        var_to_read="nb_on",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )
    for time_step in range(number_hours):
        assert (
            thermal_problem_builder.database.get_value(
                ComponentParameterIndex(cluster, "nb_units_min"), time_step, 0
            )
            == 2
            if time_step != 12
            else 3
        )

    # Solve heuristic problem
    resolution_step_accurate_heuristic = (
        thermal_problem_builder.heuristic_resolution_step(
            week_scenario_index,
            id_component=cluster,
            model=HeuristicAccurateModelBuilder(
                THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP
            ).model,
        )
    )

    thermal_problem_builder.update_database_heuristic(
        resolution_step_accurate_heuristic.output,
        week_scenario_index,
        None,
        param_to_update="nb_units_min",
        var_to_read="nb_on",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )

    for time_step in range(number_hours):
        assert (
            thermal_problem_builder.database.get_value(
                ComponentParameterIndex(cluster, "nb_units_min"), time_step, 0
            )
            == 2
            if time_step != 12
            else 3
        )

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    assert resolution_step_2.objective == 16805387

    expected_output = ExpectedOutput(
        mode="accurate",
        index=week_scenario_index,
        dir_path=data_path,
        list_cluster=[cluster],
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=33, idx_unsupplied=29
        ),
    )
    expected_output.check_output_values(resolution_step_2.output)


def test_accurate_heuristic_without_day_ahead_reserve(
    data_path: str, models: list[Model], week_scenario_index: WeekScenarioIndex
) -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares. The accurate heuristic is able to retrieve the milp optimal solution because when the number of on units found in the linear relaxation is ceiled, we found the optimal number of on units which is already feasible.
    """

    number_hours = 168
    thermal_problem_builder = ThermalProblemBuilder(
        fast=False,
        data_dir=Path(__file__).parent / data_path,
        id_thermal_cluster_model=THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP.id,
        port_types=[BALANCE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP).model]
        + models,
        time_scenario_hour_parameter=TimeScenarioHourParameter(1, 1, number_hours),
    )

    cluster = thermal_problem_builder.heuristic_components()[0]

    # First optimization
    resolution_step_1 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )

    # Get number of on units and round it to integer
    thermal_problem_builder.update_database_heuristic(
        resolution_step_1.output,
        week_scenario_index,
        None,
        param_to_update="nb_units_min",
        var_to_read="nb_on",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )
    for time_step in range(number_hours):
        assert (
            thermal_problem_builder.database.get_value(
                ComponentParameterIndex(cluster, "nb_units_min"), time_step, 0
            )
            == 2
            if time_step != 12
            else 3
        )

    # Solve heuristic problem
    resolution_step_accurate_heuristic = (
        thermal_problem_builder.heuristic_resolution_step(
            week_scenario_index,
            id_component=cluster,
            model=HeuristicAccurateModelBuilder(
                THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP
            ).model,
        )
    )

    thermal_problem_builder.update_database_heuristic(
        resolution_step_accurate_heuristic.output,
        week_scenario_index,
        None,
        param_to_update="nb_units_min",
        var_to_read="nb_on",
        fn_to_apply=lambda x: ceil(round(x, 12)),
    )

    for time_step in range(number_hours):
        assert (
            thermal_problem_builder.database.get_value(
                ComponentParameterIndex(cluster, "nb_units_min"), time_step, 0
            )
            == 2
            if time_step != 12
            else 3
        )

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    assert resolution_step_2.objective == 16805387

    expected_output = ExpectedOutput(
        mode="accurate",
        index=week_scenario_index,
        dir_path=data_path,
        list_cluster=[cluster],
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=33, idx_unsupplied=29
        ),
    )
    expected_output.check_output_values(resolution_step_2.output)
