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

from math import ceil,floor
from pathlib import Path
from typing import List

import ortools.linear_solver.pywraplp as pywraplp
import pytest
import pandas as pd

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
from tests.functional.libs.lib_thermal_reserve import (
    THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP,
    DEMAND_WITH_RESERVE_MODEL,
    RESERVE_PORT_TYPE,
    NODE_WITH_RESERVE_MODEL
)
from tests.functional.libs.heuristique import *

@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent.parent / "data_reserve/thermal_reserves_one_cluster"


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
    energy_production = OutputValues(main_resolution_step)._components['G']._variables['energy_generation'].value
    nbr_on = OutputValues(main_resolution_step)._components['G']._variables['nb_on'].value
    primary_reserve_up_production = OutputValues(main_resolution_step)._components['G']._variables['generation_reserve_up_primary'].value
    primary_reserve_down_production = OutputValues(main_resolution_step)._components['G']._variables['generation_reserve_down_primary'].value
    secondary_reserve_up_production = OutputValues(main_resolution_step)._components['G']._variables['generation_reserve_up_secondary'].value
    secondary_reserve_down_production = OutputValues(main_resolution_step)._components['G']._variables['generation_reserve_down_secondary'].value  
    UNSP_res_up = OutputValues(main_resolution_step)._components['N']._variables['unsupplied_up_reserve_primary'].value
    # return(reserve_up_production,reserve_down_production)

    de_milp = pd.DataFrame(data = {"energy_production": energy_production[0],"nbr_on": nbr_on[0],
                                   "reserve_up_primary":primary_reserve_up_production[0],"reserve_down_primary":primary_reserve_down_production[0],
                                   "reserve_up_secondary":secondary_reserve_up_production[0],"reserve_down_secondary":secondary_reserve_down_production[0]})
    de_milp.to_csv("result_milp.csv",index=False)


def test_accurate_heuristic(
    data_path: Path,
    models: list[Model],
    week_scenario_index: BlockScenarioIndex,
    input_components: InputComponents,
    heuristic_components: List[str],
    time_scenario_parameters: TimeScenarioHourParameter,
) -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares. The accurate heuristic is able to retrieve the milp optimal solution because when the number of on units found in the linear relaxation is ceiled, we found the optimal number of on units which is already feasible.
    """

    number_hours = 168
    network = get_network(
        input_components,
        port_types=[RESERVE_PORT_TYPE],
        models=[AccurateModelBuilder(THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP).model]  + [DEMAND_WITH_RESERVE_MODEL] + [NODE_WITH_RESERVE_MODEL],
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
    status = resolution_step_1.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL

    # Get number of on units and round it to integer
    thermal_problem_builder.update_database_heuristic(
        OutputValues(resolution_step_1),
        week_scenario_index,
        heuristic_components,
        param_to_update= [["nb_units_min"]],
        var_to_read=["nb_on","energy_generation","generation_reserve_up_primary_on","generation_reserve_up_primary_off",
                     "generation_reserve_down_primary","generation_reserve_up_secondary_on","generation_reserve_up_secondary_off",
                     "generation_reserve_down_secondary","generation_reserve_up_tertiary1_on","generation_reserve_up_tertiary1_off",
                     "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2_on","generation_reserve_up_tertiary2_off",
                     "generation_reserve_down_tertiary2","nb_off_primary","nb_off_secondary","nb_off_tertiary1","nb_off_tertiary2"],
        fn_to_apply= heuristique_opti_entier,
        version = "perte",
        # option = "quantité",
        param_needed_to_compute=["p_max","p_min","nb_units_max_invisible",
                                 "participation_max_primary_reserve_up_on","participation_max_primary_reserve_up_off",
                                 "participation_max_primary_reserve_down","participation_max_secondary_reserve_up_on",
                                 "participation_max_secondary_reserve_up_off","participation_max_secondary_reserve_down",
                                 "participation_max_tertiary1_reserve_up_on","participation_max_tertiary1_reserve_up_off",
                                 "participation_max_tertiary1_reserve_down","participation_max_tertiary2_reserve_up_on",
                                 "participation_max_tertiary2_reserve_up_off","participation_max_tertiary2_reserve_down",
                                 "cost","startup_cost","fixed_cost",
                                 "cost_participation_primary_reserve_up_on","cost_participation_primary_reserve_up_off","cost_participation_primary_reserve_down",
                                 "cost_participation_secondary_reserve_up_on","cost_participation_secondary_reserve_up_off","cost_participation_secondary_reserve_down",
                                 "cost_participation_tertiary1_reserve_up_on","cost_participation_tertiary1_reserve_up_off","cost_participation_tertiary1_reserve_down",
                                 "cost_participation_tertiary2_reserve_up_on","cost_participation_tertiary2_reserve_up_off","cost_participation_tertiary2_reserve_down"],
        param_node_needed_to_compute=["spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
                                      "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
                                      "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
                                      "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost",
                                      "primary_reserve_up_oversupplied_cost","primary_reserve_down_oversupplied_cost",
                                      "secondary_reserve_up_oversupplied_cost","secondary_reserve_down_oversupplied_cost",
                                      "tertiary1_reserve_up_oversupplied_cost","tertiary1_reserve_down_oversupplied_cost",
                                      "tertiary2_reserve_up_oversupplied_cost","tertiary2_reserve_down_oversupplied_cost"],
    )


    # Solve heuristic problem
    resolution_step_accurate_heuristic = (
        thermal_problem_builder.heuristic_resolution_step(
            week_scenario_index,
            id_component=heuristic_components[0],
            model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP).model,
        )
    )
    status = resolution_step_accurate_heuristic.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL

    thermal_problem_builder.update_database_heuristic(
        OutputValues(resolution_step_accurate_heuristic),
        week_scenario_index,
        heuristic_components,
        param_to_update= [["nb_units_min","nb_units_max"]],
        var_to_read=["nb_on"],
        fn_to_apply= old_heuristique,
    )

    thermal_problem_builder.update_database_heuristic(
        OutputValues(resolution_step_1),
        week_scenario_index,
        heuristic_components,
        param_to_update= [["nb_units_off_primary_min","nb_units_off_primary_max"],["nb_units_off_secondary_min","nb_units_off_secondary_max"]
                           ,["nb_units_off_tertiary1_min","nb_units_off_tertiary1_max"],["nb_units_off_tertiary2_min","nb_units_off_tertiary2_max"]],
        var_to_read=["energy_generation","generation_reserve_up_primary_on","generation_reserve_up_primary_off",
                     "generation_reserve_down_primary","generation_reserve_up_secondary_on","generation_reserve_up_secondary_off",
                     "generation_reserve_down_secondary","generation_reserve_up_tertiary1_on","generation_reserve_up_tertiary1_off",
                     "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2_on","generation_reserve_up_tertiary2_off",
                     "generation_reserve_down_tertiary2","nb_off_primary","nb_off_secondary","nb_off_tertiary1","nb_off_tertiary2"],
        fn_to_apply= heuristique_eteint,
        version = " ", #reduction ou non
        option = "opti",
        param_needed_to_compute=["nb_units_max","p_max","p_min","nb_units_max_invisible",
                                 "participation_max_primary_reserve_up_on","participation_max_primary_reserve_up_off",
                                 "participation_max_primary_reserve_down","participation_max_secondary_reserve_up_on",
                                 "participation_max_secondary_reserve_up_off","participation_max_secondary_reserve_down",
                                 "participation_max_tertiary1_reserve_up_on","participation_max_tertiary1_reserve_up_off",
                                 "participation_max_tertiary1_reserve_down","participation_max_tertiary2_reserve_up_on",
                                 "participation_max_tertiary2_reserve_up_off","participation_max_tertiary2_reserve_down",
                                 "cost","fixed_cost",
                                 "cost_participation_primary_reserve_up_on","cost_participation_primary_reserve_up_off","cost_participation_primary_reserve_down",
                                 "cost_participation_secondary_reserve_up_on","cost_participation_secondary_reserve_up_off","cost_participation_secondary_reserve_down",
                                 "cost_participation_tertiary1_reserve_up_on","cost_participation_tertiary1_reserve_up_off","cost_participation_tertiary1_reserve_down",
                                 "cost_participation_tertiary2_reserve_up_on","cost_participation_tertiary2_reserve_up_off","cost_participation_tertiary2_reserve_down"],
        param_node_needed_to_compute=["spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
                                      "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
                                      "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
                                      "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost",
                                      "primary_reserve_up_oversupplied_cost","primary_reserve_down_oversupplied_cost",
                                      "secondary_reserve_up_oversupplied_cost","secondary_reserve_down_oversupplied_cost",
                                      "tertiary1_reserve_up_oversupplied_cost","tertiary1_reserve_down_oversupplied_cost",
                                      "tertiary2_reserve_up_oversupplied_cost","tertiary2_reserve_down_oversupplied_cost"],
    )


    result_step1 = OutputValues(resolution_step_1)

    # nbr_on = OutputValues(resolution_step_accurate_heuristic)._components['G']._variables['nb_on'].value
    # nbr_off_primary = OutputValues(resolution_step_1)._components['G']._variables['nb_off_primary'].value
    # nbr_off_secondary = OutputValues(resolution_step_1)._components['G']._variables['nb_off_secondary'].value
    # de_accurate_step2 = pd.DataFrame(data = {"nbr_on": nbr_on[0],"nb_off_primary":nbr_off_primary[0],"nb_off_secondary":nbr_off_secondary[0]})
    # de_accurate_step2.to_csv("results_intermediaire.csv",index=False)
    
 
    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    status = resolution_step_2.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL

    result_step2 = OutputValues(resolution_step_2)

    nbr_on_accurate_step1 = result_step1._components['G']._variables['nb_on'].value
    nbr_off_primary_accurate_step1 = result_step1._components['G']._variables['nb_off_primary'].value
    energy_production_accurate_step1 = result_step1._components['G']._variables['energy_generation'].value
    reserve_primary_up_on_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_up_primary_on'].value
    reserve_primary_up_off_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_up_primary_off'].value   
    reserve_primary_down_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_down_primary'].value   
    nbr_off_secondary_accurate_step1 = result_step1._components['G']._variables['nb_off_secondary'].value
    reserve_secondary_up_on_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_up_secondary_on'].value
    reserve_secondary_up_off_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_up_secondary_off'].value
    reserve_secondary_down_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_down_secondary'].value   
    
    nbr_on_accurate_step2 = result_step2._components['G']._variables['nb_on'].value
    nbr_off_primary_accurate_step2 = result_step2._components['G']._variables['nb_off_primary'].value
    energy_production_accurate_step2 = result_step2._components['G']._variables['energy_generation'].value
    reserve_primary_up_on_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_up_primary_on'].value
    reserve_primary_up_off_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_up_primary_off'].value
    reserve_primary_down_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_down_primary'].value  
    nbr_off_secondary_accurate_step2 = result_step2._components['G']._variables['nb_off_secondary'].value
    reserve_secondary_up_on_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_up_secondary_on'].value
    reserve_secondary_up_off_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_up_secondary_off'].value
    reserve_secondary_down_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_down_secondary'].value  

    de_accurate_step1 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step1[0],"nbr_on": nbr_on_accurate_step1[0],
                                             "nbr_off_primary": nbr_off_primary_accurate_step1[0],
                                             "reserve_primary_up_on":reserve_primary_up_on_production_accurate_step1[0],
                                             "reserve_primary_up_off":reserve_primary_up_off_production_accurate_step1[0],
                                             "reserve_primary_down":reserve_primary_down_production_accurate_step1[0],
                                             "nbr_off_secondary": nbr_off_secondary_accurate_step1[0],"reserve_secondary_up_on":reserve_secondary_up_on_production_accurate_step1[0],"reserve_secondary_up_off":reserve_secondary_up_off_production_accurate_step1[0], "reserve_secondary_down":reserve_secondary_down_production_accurate_step1[0],
                                             "Fonction_objectif":resolution_step_1.solver.Objective().Value()})
    de_accurate_step1.to_csv("result_accurate_step1.csv",index=False)
    de_accurate_step2 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step2[0],"nbr_on": nbr_on_accurate_step2[0],
                                              "nbr_off_primary": nbr_off_primary_accurate_step2[0],
                                              "reserve_primary_up_on":reserve_primary_up_on_production_accurate_step2[0],
                                              "reserve_primary_up_off":reserve_primary_up_off_production_accurate_step2[0],
                                              "reserve_primary_down":reserve_primary_down_production_accurate_step2[0],
                                             "nbr_off_secondary": nbr_off_secondary_accurate_step2[0],"reserve_secondary_up_on":reserve_secondary_up_on_production_accurate_step2[0],"reserve_secondary_up_off":reserve_secondary_up_off_production_accurate_step2[0], "reserve_secondary_down":reserve_secondary_down_production_accurate_step2[0],
                                              "Fonction_objectif":resolution_step_2.solver.Objective().Value()})
    de_accurate_step2.to_csv("result_accurate_step2.csv",index=False)


def test_taille():
    arrondi_eteint(version = ' ', option = 'cout_defaillance', energy_generation = 423.0,
    generation_reserve_up_primary_on = 0.0, generation_reserve_up_primary_off = 92.0,
    generation_reserve_down_primary = 30.0, generation_reserve_up_secondary_on = 0.0,
    generation_reserve_up_secondary_off = 61.0,
    generation_reserve_down_secondary = 0.0,
    generation_reserve_up_tertiary1_on = 0.0,
    generation_reserve_up_tertiary1_off = 0.0,
    generation_reserve_down_tertiary1 = 0.0,
    generation_reserve_up_tertiary2_on = 0.0,
    generation_reserve_up_tertiary2_off = 0.0,
    generation_reserve_down_tertiary2 = 0.0,
    nbr_off_primary_float = 1.0222222222222221,
    nbr_off_secondary_float = 0.6421052631578946, nbr_off_tertiary1_float = 0.0,
    nbr_off_tertiary2_float = 0.0, nbr_on = 5.0, p_max = 100.0, p_min = 80.0,
    nbr_units_max = 7.0, participation_max_primary_reserve_up_on = 27.0,
    participation_max_primary_reserve_up_off = 90.0,
    participation_max_primary_reserve_down = 27.0,
    participation_max_secondary_reserve_up_on = 27.0,
    participation_max_secondary_reserve_up_off = 95.0,
    participation_max_secondary_reserve_down = 27.0,
    participation_max_tertiary1_reserve_up_on = 27.0,
    participation_max_tertiary1_reserve_up_off = 0.0,
    participation_max_tertiary1_reserve_down = 27.0,
    participation_max_tertiary2_reserve_up_on = 27.0,
    participation_max_tertiary2_reserve_up_off = 0.0,
    participation_max_tertiary2_reserve_down = 27.0, cost = 35.0,
    fixed_cost = 1000.0, cost_participation_primary_reserve_up_on = 1.0,
    cost_participation_primary_reserve_up_off = 2.0,
    cost_participation_primary_reserve_down = 1.0,
    cost_participation_secondary_reserve_up_on = 2.1,
    cost_participation_secondary_reserve_up_off = 3.0,
    cost_participation_secondary_reserve_down = 0.0,
    cost_participation_tertiary1_reserve_up_on = 0.0,
    cost_participation_tertiary1_reserve_up_off = 0.0,
    cost_participation_tertiary1_reserve_down = 0.0,
    cost_participation_tertiary2_reserve_up_on = 0.0,
    cost_participation_tertiary2_reserve_up_off = 0.0,
    cost_participation_tertiary2_reserve_down = 0.0, spillage_cost = 0.0,
    ens_cost = 100.0, primary_reserve_up_not_supplied_cost = 1000.0,
    primary_reserve_down_not_supplied_cost = 1000.0,
    secondary_reserve_up_not_supplied_cost = 1000.0,
    secondary_reserve_down_not_supplied_cost = 1000.0,
    tertiary1_reserve_up_not_supplied_cost = 1000.0,
    tertiary1_reserve_down_not_supplied_cost = 1000.0,
    tertiary2_reserve_up_not_supplied_cost = 1000.0,
    tertiary2_reserve_down_not_supplied_cost = 1000.0,
    primary_reserve_up_oversupplied_cost = 0.0,
    primary_reserve_down_oversupplied_cost = 0.0,
    secondary_reserve_up_oversupplied_cost = 0.0,
    secondary_reserve_down_oversupplied_cost = 0.0,
    tertiary1_reserve_up_oversupplied_cost = 0.0,
    tertiary1_reserve_down_oversupplied_cost = 0.0,
    tertiary2_reserve_up_oversupplied_cost = 0.0,
    tertiary2_reserve_down_oversupplied_cost = 0.0)

# def test_difference_milp_accurate(
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
    
#     # Resolution with MILP
#     network = get_network(
#         input_components,
#         port_types=[RESERVE_PORT_TYPE],
#         models=[THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP] + [DEMAND_WITH_RESERVE_MODEL] + [NODE_WITH_RESERVE_MODEL],
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

#     milp_resolution = thermal_problem_builder.main_resolution_step(
#         week_scenario_index
#     )
#     status = milp_resolution.solver.Solve()
#     assert status == pywraplp.Solver.OPTIMAL

#     result_milp = OutputValues(milp_resolution)
    
#     # resolution with accurate

#     network = get_network(
#         input_components,
#         port_types=[RESERVE_PORT_TYPE],
#         models=[AccurateModelBuilder(THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP).model]  + [DEMAND_WITH_RESERVE_MODEL] + [NODE_WITH_RESERVE_MODEL],
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
#         param_to_update= ["nb_units_min"],
#         var_to_read=["nb_on","energy_generation","generation_reserve_up_primary_on","generation_reserve_down_primary",
#                      "generation_reserve_up_secondary_on","generation_reserve_down_secondary","generation_reserve_up_tertiary1_on",
#                      "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2_on","generation_reserve_down_tertiary2"],
#         fn_to_apply= heuristique_opti_defaillance_choix,
#         param_needed_to_compute=["p_max","p_min","participation_max_primary_reserve_up_on","participation_max_primary_reserve_down",
#                                  "participation_max_secondary_reserve_up_on","participation_max_secondary_reserve_down",
#                                  "participation_max_tertiary1_reserve_up_on","participation_max_tertiary1_reserve_down",
#                                  "participation_max_tertiary2_reserve_up_on","participation_max_tertiary2_reserve_down",
#                                  "cost","startup_cost","fixed_cost",
#                                  "cost_participation_primary_reserve_up","cost_participation_primary_reserve_down",
#                                  "cost_participation_secondary_reserve_up","cost_participation_secondary_reserve_down",
#                                  "cost_participation_tertiary1_reserve_up","cost_participation_tertiary1_reserve_down",
#                                  "cost_participation_tertiary2_reserve_up","cost_participation_tertiary2_reserve_down"],
#         param_node_needed_to_compute=["spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
#                                       "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
#                                       "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
#                                       "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost"],
#     )
    

#     # Solve heuristic problem
#     resolution_step_accurate_heuristic = (
#         thermal_problem_builder.heuristic_resolution_step(
#             week_scenario_index,
#             id_component=heuristic_components[0],
#             model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP).model,
#         )
#     )
#     status = resolution_step_accurate_heuristic.solver.Solve()
#     assert status == pywraplp.Solver.OPTIMAL

#     thermal_problem_builder.update_database_heuristic(
#         OutputValues(resolution_step_accurate_heuristic),
#         week_scenario_index,
#         heuristic_components,
#         param_to_update= ["nb_units_min","nb_units_max"],
#         var_to_read=["nb_on"],
#         fn_to_apply= old_heuristique,
#     )
    
    
#     # Second optimization with lower bound modified
#     resolution_step_2 = thermal_problem_builder.main_resolution_step(
#         week_scenario_index
#     )
#     status = resolution_step_2.solver.Solve()
#     assert status == pywraplp.Solver.OPTIMAL

#     result_step1 = OutputValues(resolution_step_1)
#     result_step2 = OutputValues(resolution_step_2)

#     nbr_on_milp = result_milp._components['G']._variables['nb_on'].value
#     nbr_off_milp = result_milp._components['G']._variables['nb_off_reserve_up'].value
#     energy_production_milp = result_milp._components['G']._variables['energy_generation'].value
#     reserve_up_on_production_milp = result_milp._components['G']._variables['generation_reserve_up_primary_on'].value
#     reserve_up_off_production_milp = result_milp._components['G']._variables['generation_reserve_up_primary_off'].value
#     reserve_down_production_milp = result_milp._components['G']._variables['generation_reserve_down_primary'].value 

#     nbr_on_accurate_step1 = result_step1._components['G']._variables['nb_on'].value
#     nbr_off_accurate_step1 = result_step1._components['G']._variables['nb_off_reserve_up'].value
#     energy_production_accurate_step1 = result_step1._components['G']._variables['energy_generation'].value
#     reserve_up_on_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_up_primary_on'].value
#     reserve_up_off_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_up_primary_off'].value
#     reserve_down_production_accurate_step1 = result_step1._components['G']._variables['generation_reserve_down_primary'].value   
    
#     nbr_on_accurate_step2 = result_step2._components['G']._variables['nb_on'].value
#     nbr_off_accurate_step2 = result_step2._components['G']._variables['nb_on'].value
#     energy_production_accurate_step2 = result_step2._components['G']._variables['energy_generation'].value
#     reserve_up_on_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_up_primary_on'].value
#     reserve_up_off_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_up_primary_off'].value
#     reserve_down_production_accurate_step2 = result_step2._components['G']._variables['generation_reserve_down_primary'].value  

#     de_milp = pd.DataFrame(data = {"energy_production": energy_production_milp[0],"nbr_on": nbr_on_milp[0],"nbr_off": nbr_off_milp[0],
#                                    "reserve_up_on":reserve_up_on_production_milp[0],"reserve_up_off":reserve_up_off_production_milp[0],"reserve down":reserve_down_production_milp[0],
#                                    "Fonction_objectif":milp_resolution.solver.Objective().Value()})
#     de_milp.to_csv("result_milp.csv",index=False)
#     de_accurate_step1 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step1[0],"nbr_on": nbr_on_accurate_step1[0],"nbr_off": nbr_off_accurate_step1[0],
#                                              "reserve_up_on":reserve_up_on_production_accurate_step1[0],"reserve_up_off":reserve_up_off_production_accurate_step1[0],"reserve down":reserve_down_production_accurate_step1[0],
#                                              "Fonction_objectif":resolution_step_1.solver.Objective().Value()})
#     de_accurate_step1.to_csv("result_accurate_step1.csv",index=False)
#     de_accurate_step2 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step2[0],"nbr_on": nbr_on_accurate_step2[0],"nbr_off": nbr_off_accurate_step2[0],
#                                              "reserve_up_on":reserve_up_on_production_accurate_step2[0],"reserve_up_off":reserve_up_off_production_accurate_step2[0],"reserve down":reserve_down_production_accurate_step2[0],
#                                              "Fonction_objectif":resolution_step_2.solver.Objective().Value()})
#     de_accurate_step2.to_csv("result_accurate_step2.csv",index=False)

#     # assert nbr_on_accurate_step1 == nbr_on_accurate_step2
#     # assert nbr_on_milp == nbr_on_accurate_step2
