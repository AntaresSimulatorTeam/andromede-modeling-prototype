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

# from andromede.libs.standard import BALANCE_PORT_TYPE
from andromede.simulation import OutputValues
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
    get_network,
)
from tests.functional.conftest import ExpectedOutput, ExpectedOutputIndexes
from tests.functional.libs.lib_thermal_heuristic import (
    THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP,
    DEMAND_WITH_RESERVE_MODEL,
    RESERVE_PORT_TYPE,
    NODE_WITH_RESERVE_MODEL
)


@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent.parent / "data/thermal_heuristic_reserve_hausse"


def test_milp_version(
    data_path: Path,
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    
    network = get_network(
        input_components,
        port_types=[RESERVE_PORT_TYPE],
        models=[THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP] + [DEMAND_WITH_RESERVE_MODEL] + [NODE_WITH_RESERVE_MODEL],
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
    status = main_resolution_step.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL

    b = OutputValues(main_resolution_step)
    total_production = OutputValues(main_resolution_step)._components['G']._variables['total_generation'].value
    nbr_on = OutputValues(main_resolution_step)._components['G']._variables['nb_on'].value
    a = b
    # assert main_resolution_step.solver.Objective().Value() == 16805387

    # expected_output = ExpectedOutput(
    #     mode="milp",
    #     index=week_scenario_index,
    #     dir_path=data_path,
    #     list_cluster=heuristic_components,
    #     output_idx=ExpectedOutputIndexes(
    #         idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
    #     ),
    # )
    # expected_output.check_output_values(OutputValues(main_resolution_step))


# def test_accurate_heuristic(
#     data_path: Path,
#     models: list[Model],
#     week_scenario_index: BlockScenarioIndex,
#     input_components: InputComponents,
#     heuristic_components: List[str],
#     time_scenario_parameters: TimeScenarioHourParameter,
# ) -> None:
#     """
#     Solve the same problem as before with the heuristic accurate of Antares. The accurate heuristic is able to retrieve the milp optimal solution because when the number of on units found in the linear relaxation is ceiled, we found the optimal number of on units which is already feasible.
#     """

#     number_hours = 168
#     network = get_network(
#         input_components,
#         port_types=[BALANCE_PORT_TYPE] + [RESERVE_PORT_TYPE],
#         models=[AccurateModelBuilder(THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP).model]  + [DEMAND_WITH_RESERVE_MODEL] + models,
#     )
#     database = get_database(
#         input_components,
#         data_path,
#         fast=False,
#         cluster=heuristic_components,
#         time_scenario_hour_parameter=time_scenario_parameters,
#     )

#     thermal_problem_builder = ThermalProblemBuilder(
#         network=network,
#         database=database,
#         time_scenario_hour_parameter=time_scenario_parameters,
#     )

#     # First optimization
#     resolution_step_1 = thermal_problem_builder.main_resolution_step(
#         week_scenario_index
#     )
#     status = resolution_step_1.solver.Solve()
#     assert status == pywraplp.Solver.OPTIMAL

#     # Get number of on units and round it to integer
#     thermal_problem_builder.update_database_heuristic(
#         OutputValues(resolution_step_1),
#         week_scenario_index,
#         heuristic_components,
#         param_to_update="nb_units_min",
#         var_to_read="nb_on",
#         fn_to_apply=lambda x: ceil(round(x, 12)),
#     )
#     result_pre_heurist = []
#     for time_step in range(number_hours):
#         result_pre_heurist.append(
#             thermal_problem_builder.database.get_value(
#                 ComponentParameterIndex(heuristic_components[0], "nb_units_min"),
#                 time_step,
#                 0,
#             )
#         )
    

#     # Solve heuristic problem
#     resolution_step_accurate_heuristic = (
#         thermal_problem_builder.heuristic_resolution_step(
#             week_scenario_index,
#             id_component=heuristic_components[0],
#             model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model,
#         )
#     )
#     status = resolution_step_accurate_heuristic.solver.Solve()
#     assert status == pywraplp.Solver.OPTIMAL

#     thermal_problem_builder.update_database_heuristic(
#         OutputValues(resolution_step_accurate_heuristic),
#         week_scenario_index,
#         heuristic_components,
#         param_to_update="nb_units_min",
#         var_to_read="nb_on",
#         fn_to_apply=lambda x: ceil(round(x, 12)),
#     )
#     difference = []
#     for time_step in range(number_hours):
#         difference.append(result_pre_heurist[time_step] -
#             thermal_problem_builder.database.get_value(
#                 ComponentParameterIndex(heuristic_components[0], "nb_units_min"),
#                 time_step,
#                 0,
#             )
#         )

#     # for time_step in range(number_hours):
#     #     assert (
#     #         thermal_problem_builder.database.get_value(
#     #             ComponentParameterIndex(heuristic_components[0], "nb_units_min"),
#     #             time_step,
#     #             0,
#     #         )
#     #         == 2
#     #         if time_step != 12
#     #         else 3
#     #     )

#     # Second optimization with lower bound modified
#     resolution_step_2 = thermal_problem_builder.main_resolution_step(
#         week_scenario_index
#     )
#     status = resolution_step_2.solver.Solve()
#     assert status == pywraplp.Solver.OPTIMAL
#     # assert resolution_step_2.solver.Objective().Value() == 16805387

#     # expected_output = ExpectedOutput(
#     #     mode="accurate",
#     #     index=week_scenario_index,
#     #     dir_path=data_path,
#     #     list_cluster=heuristic_components,
#     #     output_idx=ExpectedOutputIndexes(
#     #         idx_generation=4, idx_nodu=6, idx_spillage=33, idx_unsupplied=29
#     #     ),
#     # )
#     production = OutputValues(resolution_step_2)._components['G']._variables['generation'].value
#     # return(production)
#     # expected_output.check_output_values(OutputValues(resolution_step_2))

