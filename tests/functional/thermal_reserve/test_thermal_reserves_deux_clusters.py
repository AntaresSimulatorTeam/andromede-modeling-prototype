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

from andromede.thermal_heuristic.time_scenario_parameter import (
    BlockScenarioIndex,
    TimeScenarioHourParameter,
    timesteps,
)

@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent.parent / "data_reserve/thermal_reserves_deux_clusters_one_res"


def test_milp(
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
    
    # Resolution with MILP
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

    milp_resolution = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    status = milp_resolution.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL
    result_milp = OutputValues(milp_resolution)
    

    nbr_on_milp_1 = result_milp._components['BASE']._variables['nb_on'].value
    energy_production_milp_1 = result_milp._components['BASE']._variables['energy_generation'].value
    primary_up_on_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_primary_on'].value
    primary_up_off_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_primary_off'].value
    primary_down_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_down_primary'].value 
    secondary_up_on_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_secondary_on'].value
    secondary_up_off_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_secondary_off'].value
    secondary_down_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_down_secondary'].value 
    tertiary1_up_on_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_tertiary1_on'].value
    tertiary1_up_off_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_tertiary1_off'].value
    tertiary1_down_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_down_tertiary1'].value 
  
    de_milp_1 = pd.DataFrame(data = {"energy_production": energy_production_milp_1[0],"nbr_on": nbr_on_milp_1[0],
                                   "primary_up_on": primary_up_on_production_milp_1[0],"primary_up_off": primary_up_off_production_milp_1[0],"primary_down":primary_down_production_milp_1[0],
                                   "secondary_up_on": secondary_up_on_production_milp_1[0],
                                   "secondary_up_off": secondary_up_off_production_milp_1[0],"secondary_down":secondary_down_production_milp_1[0],
                                   "tertiary1_up_on": tertiary1_up_on_production_milp_1[0],
                                   "tertiary1_up_off": tertiary1_up_off_production_milp_1[0],"tertiary1_down":tertiary1_down_production_milp_1[0],
                                   "Fonction_objectif":milp_resolution.solver.Objective().Value()})
    de_milp_1.to_csv("result_milp_1.csv",index=False)
   
    nbr_on_milp_2 = result_milp._components['PEAK']._variables['nb_on'].value
    energy_production_milp_2 = result_milp._components['PEAK']._variables['energy_generation'].value
    primary_up_on_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_primary_on'].value
    primary_up_off_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_primary_off'].value
    primary_down_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_down_primary'].value 
    secondary_up_on_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_secondary_on'].value
    secondary_up_off_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_secondary_off'].value
    secondary_down_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_down_secondary'].value 
    tertiary1_up_on_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_tertiary1_on'].value
    tertiary1_up_off_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_tertiary1_off'].value
    tertiary1_down_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_down_tertiary1'].value 

    de_milp_2 = pd.DataFrame(data = {"energy_production": energy_production_milp_2[0],"nbr_on": nbr_on_milp_2[0],
                                   "primary_up_on": primary_up_on_production_milp_2[0],"primary_up_off": primary_up_off_production_milp_2[0],"primary_down":primary_down_production_milp_2[0],
                                   "secondary_up_on": secondary_up_on_production_milp_2[0],
                                   "secondary_up_off": secondary_up_off_production_milp_2[0],"secondary_down":secondary_down_production_milp_2[0],
                                   "tertiary1_up_on": tertiary1_up_on_production_milp_2[0],
                                   "tertiary1_up_off": tertiary1_up_off_production_milp_2[0],"tertiary1_down":tertiary1_down_production_milp_2[0]}
                            )
    de_milp_2.to_csv("result_milp_2.csv",index=False) 
  
  


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
        fn_to_apply= heuristique_opti_repartition,
        version = "choix",
        option = "choix",
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

    
    # nbr_on_base = [database.get_data('BASE','nb_units_min').get_value(t,0) for i, t in enumerate(timesteps(week_scenario_index, time_scenario_parameters))]
    # de_accurate_step2_base = pd.DataFrame(data = {"nbr_on_base": nbr_on_base})
    # de_accurate_step2_base.to_csv("results_intermediaire_base.csv",index=False)

    for g in heuristic_components:

        # Solve heuristic problem
        resolution_step_accurate_heuristic = (
            thermal_problem_builder.heuristic_resolution_step(
                week_scenario_index,
                id_component=g,
                model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_WITH_RESERVE_MODEL_MILP).model,
            )
        )
        status = resolution_step_accurate_heuristic.solver.Solve()
        assert status == pywraplp.Solver.OPTIMAL

        thermal_problem_builder.update_database_heuristic(
            OutputValues(resolution_step_accurate_heuristic),
            week_scenario_index,
            [g],
            param_to_update= [["nb_units_min","nb_units_max"]],
            var_to_read=["nb_on"],
            fn_to_apply= old_heuristique,
        )

    # thermal_problem_builder.update_database_heuristic(
    #     OutputValues(resolution_step_1),
    #     week_scenario_index,
    #     heuristic_components,
    #     param_to_update= [["nb_units_off_primary_min","nb_units_off_primary_max"],["nb_units_off_secondary_min","nb_units_off_secondary_max"]
    #                        ,["nb_units_off_tertiary1_min","nb_units_off_tertiary1_max"],["nb_units_off_tertiary2_min","nb_units_off_tertiary2_max"]],
    #     var_to_read=["energy_generation","generation_reserve_up_primary_on","generation_reserve_up_primary_off",
    #                  "generation_reserve_down_primary","generation_reserve_up_secondary_on","generation_reserve_up_secondary_off",
    #                  "generation_reserve_down_secondary","generation_reserve_up_tertiary1_on","generation_reserve_up_tertiary1_off",
    #                  "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2_on","generation_reserve_up_tertiary2_off",
    #                  "generation_reserve_down_tertiary2","nb_off_primary","nb_off_secondary","nb_off_tertiary1","nb_off_tertiary2"],
    #     fn_to_apply= heuristique_eteint,
    #     version = " ", #reduction ou non
    #     option = "opti",
    #     param_needed_to_compute=["nb_units_max","p_max","p_min","nb_units_max_invisible",
    #                              "participation_max_primary_reserve_up_on","participation_max_primary_reserve_up_off",
    #                              "participation_max_primary_reserve_down","participation_max_secondary_reserve_up_on",
    #                              "participation_max_secondary_reserve_up_off","participation_max_secondary_reserve_down",
    #                              "participation_max_tertiary1_reserve_up_on","participation_max_tertiary1_reserve_up_off",
    #                              "participation_max_tertiary1_reserve_down","participation_max_tertiary2_reserve_up_on",
    #                              "participation_max_tertiary2_reserve_up_off","participation_max_tertiary2_reserve_down",
    #                              "cost","fixed_cost",
    #                              "cost_participation_primary_reserve_up_on","cost_participation_primary_reserve_up_off","cost_participation_primary_reserve_down",
    #                              "cost_participation_secondary_reserve_up_on","cost_participation_secondary_reserve_up_off","cost_participation_secondary_reserve_down",
    #                              "cost_participation_tertiary1_reserve_up_on","cost_participation_tertiary1_reserve_up_off","cost_participation_tertiary1_reserve_down",
    #                              "cost_participation_tertiary2_reserve_up_on","cost_participation_tertiary2_reserve_up_off","cost_participation_tertiary2_reserve_down"],
    #     param_node_needed_to_compute=["spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
    #                                   "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
    #                                   "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
    #                                   "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost",
    #                                   "primary_reserve_up_oversupplied_cost","primary_reserve_down_oversupplied_cost",
    #                                   "secondary_reserve_up_oversupplied_cost","secondary_reserve_down_oversupplied_cost",
    #                                   "tertiary1_reserve_up_oversupplied_cost","tertiary1_reserve_down_oversupplied_cost",
    #                                   "tertiary2_reserve_up_oversupplied_cost","tertiary2_reserve_down_oversupplied_cost"],
    # )

    result_step1 = OutputValues(resolution_step_1)

    # nbr_on_base = OutputValues(resolution_step_accurate_heuristic)._components['BASE']._variables['nb_on'].value
    # nbr_off_primary_base = result_step1._components['BASE']._variables['nb_off_primary'].value
    # nbr_off_secondary_base = result_step1._components['BASE']._variables['nb_off_secondary'].value
    # de_accurate_step2_base = pd.DataFrame(data = {"nbr_on_base": nbr_on_base[0],"nb_off_primary_base":nbr_off_primary_base[0],"nb_off_secondary_base":nbr_off_secondary_base[0]})
    # de_accurate_step2_base.to_csv("results_intermediaire_base.csv",index=False)
    
    # nbr_on_peak = OutputValues(resolution_step_accurate_heuristic)._components['PEAK']._variables['nb_on'].value
    # nbr_off_primary_peak = result_step1._components['PEAK']._variables['nb_off_primary'].value
    # nbr_off_secondary_peak = result_step1._components['PEAK']._variables['nb_off_secondary'].value
    # de_accurate_step2_peak = pd.DataFrame(data = {"nbr_on_peak": nbr_on_peak[0],"nb_off_primary_peak":nbr_off_primary_peak[0],"nb_off_secondary_peak":nbr_off_secondary_peak[0]})
    # de_accurate_step2_peak.to_csv("results_intermediaire_peak.csv",index=False)
    
 
    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    status = resolution_step_2.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL

    result_step2 = OutputValues(resolution_step_2)

    nbr_on_accurate_step1_base = result_step1._components['BASE']._variables['nb_on'].value
    nbr_off_primary_accurate_step1_base = result_step1._components['BASE']._variables['nb_off_primary'].value
    energy_production_accurate_step1_base = result_step1._components['BASE']._variables['energy_generation'].value
    reserve_primary_up_on_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_up_primary_on'].value
    reserve_primary_up_off_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_up_primary_off'].value   
    reserve_primary_down_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_down_primary'].value   
    nbr_off_secondary_accurate_step1_base = result_step1._components['BASE']._variables['nb_off_secondary'].value
    reserve_secondary_up_on_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_up_secondary_on'].value
    reserve_secondary_up_off_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_up_secondary_off'].value
    reserve_secondary_down_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_down_secondary'].value   
    nbr_off_tertiary1_accurate_step1_base = result_step1._components['BASE']._variables['nb_off_tertiary1'].value
    reserve_tertiary1_up_on_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_up_tertiary1_on'].value
    reserve_tertiary1_up_off_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_up_tertiary1_off'].value
    reserve_tertiary1_down_production_accurate_step1_base = result_step1._components['BASE']._variables['generation_reserve_down_tertiary1'].value   
   
    nbr_on_accurate_step2_base = result_step2._components['BASE']._variables['nb_on'].value
    nbr_off_primary_accurate_step2_base = result_step2._components['BASE']._variables['nb_off_primary'].value
    energy_production_accurate_step2_base = result_step2._components['BASE']._variables['energy_generation'].value
    reserve_primary_up_on_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_up_primary_on'].value
    reserve_primary_up_off_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_up_primary_off'].value
    reserve_primary_down_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_down_primary'].value  
    nbr_off_secondary_accurate_step2_base = result_step2._components['BASE']._variables['nb_off_secondary'].value
    reserve_secondary_up_on_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_up_secondary_on'].value
    reserve_secondary_up_off_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_up_secondary_off'].value
    reserve_secondary_down_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_down_secondary'].value  
    nbr_off_tertiary1_accurate_step2_base = result_step2._components['BASE']._variables['nb_off_tertiary1'].value
    reserve_tertiary1_up_on_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_up_tertiary1_on'].value
    reserve_tertiary1_up_off_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_up_tertiary1_off'].value
    reserve_tertiary1_down_production_accurate_step2_base = result_step2._components['BASE']._variables['generation_reserve_down_tertiary1'].value  

    de_accurate_step1_base = pd.DataFrame(data = {"energy_production_base": energy_production_accurate_step1_base[0],"nbr_on": nbr_on_accurate_step1_base[0],
                                             "nbr_off_primary_base": nbr_off_primary_accurate_step1_base[0],
                                             "reserve_primary_up_on_base":reserve_primary_up_on_production_accurate_step1_base[0],
                                             "reserve_primary_up_off_base":reserve_primary_up_off_production_accurate_step1_base[0],
                                             "reserve_primary_down_base":reserve_primary_down_production_accurate_step1_base[0],
                                             "nbr_off_secondary_base": nbr_off_secondary_accurate_step1_base[0],"reserve_secondary_up_on_base":reserve_secondary_up_on_production_accurate_step1_base[0],"reserve_secondary_up_off_base":reserve_secondary_up_off_production_accurate_step1_base[0], "reserve_secondary_down_base":reserve_secondary_down_production_accurate_step1_base[0],
                                             "nbr_off_tertiary1_base": nbr_off_tertiary1_accurate_step1_base[0],"reserve_tertiary1_up_on_base":reserve_tertiary1_up_on_production_accurate_step1_base[0],"reserve_tertiary1_up_off_base":reserve_tertiary1_up_off_production_accurate_step1_base[0], "reserve_tertiary1_down_base":reserve_tertiary1_down_production_accurate_step1_base[0],
                                             "Fonction_objectif":resolution_step_1.solver.Objective().Value()})
    de_accurate_step1_base.to_csv("result_accurate_step1_base.csv",index=False)
    de_accurate_step2_base = pd.DataFrame(data = {"energy_production_base": energy_production_accurate_step2_base[0],"nbr_on": nbr_on_accurate_step2_base[0],
                                               "nbr_off_primary_base": nbr_off_primary_accurate_step2_base[0],
                                              "reserve_primary_up_on_base":reserve_primary_up_on_production_accurate_step2_base[0],
                                              "reserve_primary_up_off":reserve_primary_up_off_production_accurate_step2_base[0],
                                              "reserve_primary_down_base":reserve_primary_down_production_accurate_step2_base[0],
                                               "nbr_off_secondary_base": nbr_off_secondary_accurate_step2_base[0],"reserve_secondary_up_on_base":reserve_secondary_up_on_production_accurate_step2_base[0],"reserve_secondary_up_off_base":reserve_secondary_up_off_production_accurate_step2_base[0], "reserve_secondary_down_base":reserve_secondary_down_production_accurate_step2_base[0],
                                               "nbr_off_tertiary1_base": nbr_off_tertiary1_accurate_step2_base[0],"reserve_tertiary1_up_on_base":reserve_tertiary1_up_on_production_accurate_step2_base[0],"reserve_tertiary1_up_off_base":reserve_tertiary1_up_off_production_accurate_step2_base[0], "reserve_tertiary1_down_base":reserve_tertiary1_down_production_accurate_step2_base[0],
                                              "Fonction_objectif":resolution_step_2.solver.Objective().Value()})
    de_accurate_step2_base.to_csv("result_accurate_step2_base.csv",index=False)

    nbr_on_accurate_step1_peak = result_step1._components['PEAK']._variables['nb_on'].value
    nbr_off_primary_accurate_step1_peak = result_step1._components['PEAK']._variables['nb_off_primary'].value
    energy_production_accurate_step1_peak = result_step1._components['PEAK']._variables['energy_generation'].value
    reserve_primary_up_on_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_up_primary_on'].value
    reserve_primary_up_off_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_up_primary_off'].value   
    reserve_primary_down_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_down_primary'].value   
    nbr_off_secondary_accurate_step1_peak = result_step1._components['PEAK']._variables['nb_off_secondary'].value
    reserve_secondary_up_on_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_up_secondary_on'].value
    reserve_secondary_up_off_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_up_secondary_off'].value
    reserve_secondary_down_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_down_secondary'].value   
    nbr_off_tertiary1_accurate_step1_peak = result_step1._components['PEAK']._variables['nb_off_tertiary1'].value
    reserve_tertiary1_up_on_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_up_tertiary1_on'].value
    reserve_tertiary1_up_off_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_up_tertiary1_off'].value
    reserve_tertiary1_down_production_accurate_step1_peak = result_step1._components['PEAK']._variables['generation_reserve_down_tertiary1'].value   
    
    nbr_on_accurate_step2_peak = result_step2._components['PEAK']._variables['nb_on'].value
    nbr_off_primary_accurate_step2_peak = result_step2._components['PEAK']._variables['nb_off_primary'].value
    energy_production_accurate_step2_peak = result_step2._components['PEAK']._variables['energy_generation'].value
    reserve_primary_up_on_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_up_primary_on'].value
    reserve_primary_up_off_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_up_primary_off'].value
    reserve_primary_down_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_down_primary'].value  
    nbr_off_secondary_accurate_step2_peak = result_step2._components['PEAK']._variables['nb_off_secondary'].value
    reserve_secondary_up_on_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_up_secondary_on'].value
    reserve_secondary_up_off_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_up_secondary_off'].value
    reserve_secondary_down_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_down_secondary'].value  
    nbr_off_tertiary1_accurate_step2_peak = result_step2._components['PEAK']._variables['nb_off_tertiary1'].value
    reserve_tertiary1_up_on_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_up_tertiary1_on'].value
    reserve_tertiary1_up_off_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_up_tertiary1_off'].value
    reserve_tertiary1_down_production_accurate_step2_peak = result_step2._components['PEAK']._variables['generation_reserve_down_tertiary1'].value  

    de_accurate_step1_peak = pd.DataFrame(data = {"energy_production_peak": energy_production_accurate_step1_peak[0],"nbr_on": nbr_on_accurate_step1_peak[0],
                                             "nbr_off_primary_peak": nbr_off_primary_accurate_step1_peak[0],
                                             "reserve_primary_up_on_peak":reserve_primary_up_on_production_accurate_step1_peak[0],
                                             "reserve_primary_up_off_peak":reserve_primary_up_off_production_accurate_step1_peak[0],
                                             "reserve_primary_down_peak":reserve_primary_down_production_accurate_step1_peak[0],
                                             "nbr_off_secondary_peak": nbr_off_secondary_accurate_step1_peak[0],"reserve_secondary_up_on_peak":reserve_secondary_up_on_production_accurate_step1_peak[0],"reserve_secondary_up_off_peak":reserve_secondary_up_off_production_accurate_step1_peak[0], "reserve_secondary_down_peak":reserve_secondary_down_production_accurate_step1_peak[0],
                                             "nbr_off_tertiary1_peak": nbr_off_tertiary1_accurate_step1_peak[0],"reserve_tertiary1_up_on_peak":reserve_tertiary1_up_on_production_accurate_step1_peak[0],"reserve_tertiary1_up_off_peak":reserve_tertiary1_up_off_production_accurate_step1_peak[0], "reserve_tertiary1_down_peak":reserve_tertiary1_down_production_accurate_step1_peak[0],
                                            })
    de_accurate_step1_peak.to_csv("result_accurate_step1_peak.csv",index=False)
    de_accurate_step2_peak = pd.DataFrame(data = {"energy_production_peak": energy_production_accurate_step2_peak[0],"nbr_on": nbr_on_accurate_step2_peak[0],
                                               "nbr_off_primary_peak": nbr_off_primary_accurate_step2_peak[0],
                                              "reserve_primary_up_on_peak":reserve_primary_up_on_production_accurate_step2_peak[0],
                                               "reserve_primary_up_off":reserve_primary_up_off_production_accurate_step2_peak[0],
                                              "reserve_primary_down_peak":reserve_primary_down_production_accurate_step2_peak[0],
                                               "nbr_off_secondary_peak": nbr_off_secondary_accurate_step2_peak[0],"reserve_secondary_up_on_peak":reserve_secondary_up_on_production_accurate_step2_peak[0],"reserve_secondary_up_off_peak":reserve_secondary_up_off_production_accurate_step2_peak[0], "reserve_secondary_down_peak":reserve_secondary_down_production_accurate_step2_peak[0],
                                               "nbr_off_tertiary1_peak": nbr_off_tertiary1_accurate_step2_peak[0],"reserve_tertiary1_up_on_peak":reserve_tertiary1_up_on_production_accurate_step2_peak[0],"reserve_tertiary1_up_off_peak":reserve_tertiary1_up_off_production_accurate_step2_peak[0], "reserve_tertiary1_down_peak":reserve_tertiary1_down_production_accurate_step2_peak[0],
                                           })
    de_accurate_step2_peak.to_csv("result_accurate_step2_peak.csv",index=False)
