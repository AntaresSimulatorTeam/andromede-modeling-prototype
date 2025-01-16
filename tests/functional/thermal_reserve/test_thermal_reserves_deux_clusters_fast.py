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
import numpy as np

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
from tests.functional.libs.lib_thermal_reserve_fast import (
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


def test_fast(
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



    pmax = thermal_problem_builder.database.get_value(
        ComponentParameterIndex(heuristic_components[0], "p_max"), 0, 0
    )
    input_data = np.loadtxt(data_path / "itr1_fast_cluster.txt")
    nb_on_1 = pd.DataFrame(
        np.ceil(np.round(input_data / pmax, 12)),  # type: ignore
        index=list(range(168)),
        columns=[week_scenario_index.scenario],
    )

    status = milp_resolution.solver.Solve()
    assert status == pywraplp.Solver.OPTIMAL
    result_milp = OutputValues(milp_resolution)
    

    energy_production_milp_1 = result_milp._components['BASE']._variables['energy_generation'].value
    primary_up_on_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_primary_on'].value
    primary_up_off_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_primary_off'].value
    primary_down_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_down_primary'].value 
    tertiary_up_on_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_secondary_on'].value
    tertiary_up_off_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_up_secondary_off'].value
    tertiary_down_production_milp_1 = result_milp._components['BASE']._variables['generation_reserve_down_secondary'].value 

  
    de_milp_1 = pd.DataFrame(data = {"energy_production": energy_production_milp_1[0],
                                   "primary_up_on": primary_up_on_production_milp_1[0],"primary_up_off": primary_up_off_production_milp_1[0],"primary_down":primary_down_production_milp_1[0],
                                   "tertiary_up_on": tertiary_up_on_production_milp_1[0],
                                   "tertiary_up_off": tertiary_up_off_production_milp_1[0],"tertiary_down":tertiary_down_production_milp_1[0],
                                   "Fonction_objectif":milp_resolution.solver.Objective().Value()})
    de_milp_1.to_csv("result_milp_1.csv",index=False)
   
    energy_production_milp_2 = result_milp._components['PEAK']._variables['energy_generation'].value
    primary_up_on_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_primary_on'].value
    primary_up_off_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_primary_off'].value
    primary_down_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_down_primary'].value 
    tertiary_up_on_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_secondary_on'].value
    tertiary_up_off_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_up_secondary_off'].value
    tertiary_down_production_milp_2 = result_milp._components['PEAK']._variables['generation_reserve_down_secondary'].value 

    de_milp_2 = pd.DataFrame(data = {"energy_production": energy_production_milp_2[0],
                                   "primary_up_on": primary_up_on_production_milp_2[0],"primary_up_off": primary_up_off_production_milp_2[0],"primary_down":primary_down_production_milp_2[0],
                                   "tertiary_up_on": tertiary_up_on_production_milp_2[0],
                                   "tertiary_up_off": tertiary_up_off_production_milp_2[0],"tertiary_down":tertiary_down_production_milp_2[0]}
                            )
    de_milp_2.to_csv("result_milp_2.csv",index=False) 
  

