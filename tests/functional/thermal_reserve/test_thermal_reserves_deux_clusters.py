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
from tests.functional.libs.heuristic import nouvelle_heuristique, heuristique_opti, heuristique_opti_sans_start_up, old_heuristique

@pytest.fixture
def data_path() -> Path:
    return Path(__file__).parent.parent / "data_reserve/thermal_reserves_deux_clusters"

def test_difference_milp_accurate(
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
    

    # resolution with accurate

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
        param_to_update= ["nb_units_min"],
        var_to_read=["nb_on","energy_generation","generation_reserve_up_primary","generation_reserve_down_primary",
                     "generation_reserve_up_secondary","generation_reserve_down_secondary","generation_reserve_up_tertiary1",
                     "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2","generation_reserve_down_tertiary2"],
        fn_to_apply= heuristique_opti_sans_start_up,
        param_needed_to_compute=["p_max","p_min","participation_max_primary_reserve_up","participation_max_primary_reserve_down",
                                 "participation_max_secondary_reserve_up","participation_max_secondary_reserve_down",
                                 "participation_max_tertiary1_reserve_up","participation_max_tertiary1_reserve_down",
                                 "participation_max_tertiary2_reserve_up","participation_max_tertiary2_reserve_down",
                                 "cost","startup_cost","fixed_cost"],
        param_node_needed_to_compute=["spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
                                      "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
                                      "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
                                      "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost"],
        # param_start_up = "simple"
    )
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
                    param_to_update= ["nb_units_min","nb_units_max"],
                    var_to_read=["nb_on","energy_generation","generation_reserve_up_primary","generation_reserve_down_primary",
                     "generation_reserve_up_secondary","generation_reserve_down_secondary","generation_reserve_up_tertiary1",
                     "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2","generation_reserve_down_tertiary2"],
                    fn_to_apply= old_heuristique,
                    param_needed_to_compute=["p_max","p_min","participation_max_primary_reserve_up","participation_max_primary_reserve_down",
                                 "participation_max_secondary_reserve_up","participation_max_secondary_reserve_down",
                                 "participation_max_tertiary1_reserve_up","participation_max_tertiary1_reserve_down",
                                 "participation_max_tertiary2_reserve_up","participation_max_tertiary2_reserve_down",
                                 "cost","startup_cost","fixed_cost"],
                    param_node_needed_to_compute=["spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
                                      "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
                                      "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
                                      "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost"],
                )          

    
    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    status = resolution_step_2.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL

    result_step1 = OutputValues(resolution_step_1)
    result_step2 = OutputValues(resolution_step_2)

    nbr_on_milp_1 = result_milp._components['BASE']._variables['nb_on'].value
    energy_production_milp_1 = result_milp._components['BASE']._variables['energy_generation'].value
    reserve_up_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_primary'].value
    reserve_down_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_down_primary'].value 

    nbr_on_accurate_step1_1 = result_step1._components['BASE']._variables['nb_on'].value
    energy_production_accurate_step1_1 = result_step1._components['BASE']._variables['energy_generation'].value
    reserve_up_production_accurate_step1_1 = result_step1._components['BASE']._variables['generation_reserve_up_primary'].value
    reserve_down_production_accurate_step1_1 = result_step1._components['BASE']._variables['generation_reserve_down_primary'].value   
    
    nbr_on_accurate_step2_old1 = result_step2._components['BASE']._variables['nb_on'].value
    energy_production_accurate_step2_old1 = result_step2._components['BASE']._variables['energy_generation'].value
    reserve_up_production_accurate_step2_old1 = result_step2._components['BASE']._variables['generation_reserve_up_primary'].value
    reserve_down_production_accurate_step2_old1 = result_step2._components['BASE']._variables['generation_reserve_down_primary'].value  

    de_milp_1 = pd.DataFrame(data = {"energy_production": energy_production_milp_1[0],"nbr_on": nbr_on_milp_1[0],
                                   "reserve_up":reserve_up_production_milp_1[0],"reserve down":reserve_down_production_milp_1[0]})
    de_milp_1.to_csv("result_milp_1.csv",index=False)
    de_accurate_step1_1 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step1_1[0],"nbr_on": nbr_on_accurate_step1_1[0],
                                             "reserve_up":reserve_up_production_accurate_step1_1[0],"reserve down":reserve_down_production_accurate_step1_1[0]})
    de_accurate_step1_1.to_csv("result_accurate_step1_1.csv",index=False)
    de_accurate_step2_old1 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step2_old1[0],"nbr_on": nbr_on_accurate_step2_old1[0],
                                             "reserve_up":reserve_up_production_accurate_step2_old1[0],"reserve down":reserve_down_production_accurate_step2_old1[0]})
    de_accurate_step2_old1.to_csv("result_accurate_step2_old1.csv",index=False)

    nbr_on_milp_2 = result_milp._components['PEAK']._variables['nb_on'].value
    energy_production_milp_2 = result_milp._components['PEAK']._variables['energy_generation'].value
    reserve_up_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_primary'].value
    reserve_down_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_down_primary'].value 

    nbr_on_accurate_step1_2 = result_step1._components['PEAK']._variables['nb_on'].value
    energy_production_accurate_step1_2 = result_step1._components['PEAK']._variables['energy_generation'].value
    reserve_up_production_accurate_step1_2 = result_step1._components['PEAK']._variables['generation_reserve_up_primary'].value
    reserve_down_production_accurate_step1_2 = result_step1._components['PEAK']._variables['generation_reserve_down_primary'].value   
    
    nbr_on_accurate_step2_old2 = result_step2._components['PEAK']._variables['nb_on'].value
    energy_production_accurate_step2_old2 = result_step2._components['PEAK']._variables['energy_generation'].value
    reserve_up_production_accurate_step2_old2 = result_step2._components['PEAK']._variables['generation_reserve_up_primary'].value
    reserve_down_production_accurate_step2_old2 = result_step2._components['PEAK']._variables['generation_reserve_down_primary'].value  

    de_milp_2 = pd.DataFrame(data = {"energy_production": energy_production_milp_2[0],"nbr_on": nbr_on_milp_2[0],
                                   "reserve_up":reserve_up_production_milp_2[0],"reserve down":reserve_down_production_milp_2[0],
                                   "Fonction_objectif":milp_resolution.solver.Objective().Value()})
    de_milp_2.to_csv("result_milp_2.csv",index=False)
    de_accurate_step1_2 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step1_2[0],"nbr_on": nbr_on_accurate_step1_2[0],
                                             "reserve_up":reserve_up_production_accurate_step1_2[0],"reserve down":reserve_down_production_accurate_step1_2[0],
                                             "Fonction_objectif":resolution_step_1.solver.Objective().Value()})
    de_accurate_step1_2.to_csv("result_accurate_step1_2.csv",index=False)
    de_accurate_step2_old2 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step2_old2[0],"nbr_on": nbr_on_accurate_step2_old2[0],
                                             "reserve_up":reserve_up_production_accurate_step2_old2[0],"reserve down":reserve_down_production_accurate_step2_old2[0],
                                             "Fonction_objectif":resolution_step_2.solver.Objective().Value()})
    de_accurate_step2_old2.to_csv("result_accurate_step2_old2.csv",index=False)
    
  













  

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
        param_to_update= ["nb_units_min"],
        var_to_read=["nb_on","energy_generation","generation_reserve_up_primary","generation_reserve_down_primary",
                     "generation_reserve_up_secondary","generation_reserve_down_secondary","generation_reserve_up_tertiary1",
                     "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2","generation_reserve_down_tertiary2"],
        fn_to_apply= heuristique_opti,
        param_needed_to_compute=["p_max","p_min","participation_max_primary_reserve_up","participation_max_primary_reserve_down",
                                 "participation_max_secondary_reserve_up","participation_max_secondary_reserve_down",
                                 "participation_max_tertiary1_reserve_up","participation_max_tertiary1_reserve_down",
                                 "participation_max_tertiary2_reserve_up","participation_max_tertiary2_reserve_down",
                                 "cost","startup_cost","fixed_cost"],
        param_node_needed_to_compute=["spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
                                      "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
                                      "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
                                      "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost"],
    )
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
                    param_to_update= ["nb_units_min","nb_units_max"],
                    var_to_read=["nb_on","energy_generation","generation_reserve_up_primary","generation_reserve_down_primary",
                     "generation_reserve_up_secondary","generation_reserve_down_secondary","generation_reserve_up_tertiary1",
                     "generation_reserve_down_tertiary1","generation_reserve_up_tertiary2","generation_reserve_down_tertiary2"],
                    fn_to_apply= old_heuristique,
                    param_needed_to_compute=["p_max","p_min","participation_max_primary_reserve_up","participation_max_primary_reserve_down",
                                 "participation_max_secondary_reserve_up","participation_max_secondary_reserve_down",
                                 "participation_max_tertiary1_reserve_up","participation_max_tertiary1_reserve_down",
                                 "participation_max_tertiary2_reserve_up","participation_max_tertiary2_reserve_down",
                                 "cost","startup_cost","fixed_cost"],
                    param_node_needed_to_compute=["spillage_cost","ens_cost","primary_reserve_up_not_supplied_cost","primary_reserve_down_not_supplied_cost",
                                      "secondary_reserve_up_not_supplied_cost","secondary_reserve_down_not_supplied_cost",
                                      "tertiary1_reserve_up_not_supplied_cost","tertiary1_reserve_down_not_supplied_cost",
                                      "tertiary2_reserve_up_not_supplied_cost","tertiary2_reserve_down_not_supplied_cost"],
                )          

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.main_resolution_step(
        week_scenario_index
    )
    status = resolution_step_2.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL 

    
    result_step2 = OutputValues(resolution_step_2)

    nbr_on_accurate_step2_opti2 = result_step2._components['PEAK']._variables['nb_on'].value
    energy_production_accurate_step2_opti2 = result_step2._components['PEAK']._variables['energy_generation'].value
    reserve_up_production_accurate_step2_opti2 = result_step2._components['PEAK']._variables['generation_reserve_up_primary'].value
    reserve_down_production_accurate_step2_opti2 = result_step2._components['PEAK']._variables['generation_reserve_down_primary'].value  

    nbr_on_accurate_step2_opti1 = result_step2._components['BASE']._variables['nb_on'].value
    energy_production_accurate_step2_opti1 = result_step2._components['BASE']._variables['energy_generation'].value
    reserve_up_production_accurate_step2_opti1 = result_step2._components['BASE']._variables['generation_reserve_up_primary'].value
    reserve_down_production_accurate_step2_opti1 = result_step2._components['BASE']._variables['generation_reserve_down_primary'].value  


    de_accurate_step2_opti2 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step2_opti2[0],"nbr_on": nbr_on_accurate_step2_opti2[0],
                                             "reserve_up":reserve_up_production_accurate_step2_opti2[0],"reserve down":reserve_down_production_accurate_step2_opti2[0],
                                             "Fonction_objectif":resolution_step_2.solver.Objective().Value()})
    de_accurate_step2_opti2.to_csv("result_accurate_step2_opti2.csv",index=False)

    de_accurate_step2_opti1 = pd.DataFrame(data = {"energy_production": energy_production_accurate_step2_opti1[0],"nbr_on": nbr_on_accurate_step2_opti1[0],
                                             "reserve_up":reserve_up_production_accurate_step2_opti1[0],"reserve down":reserve_down_production_accurate_step2_opti1[0]})
    de_accurate_step2_opti1.to_csv("result_accurate_step2_opti1.csv",index=False)

    assert nbr_on_accurate_step2_old2 == nbr_on_accurate_step2_opti2
    assert nbr_on_accurate_step2_old1 == nbr_on_accurate_step2_opti1


# def tests():
#     a = heuristique_opti(7.860139860139843,381.216783216782,180.78321678321603,-3.472199124950491e-13,0.0,0.0,0.0,0.0,0.0,0.0,
#                          97,48.5,23.0,25.0,23.0,23.0,23.0,23.0,23.0,23.0,50.0,160.654,
#                          0.0,0.0,10000.0,1000.0,1000.0,1000.0,1000.0,1000.0,1000.0,1000.0,1000.0)
#     assert a != 0
