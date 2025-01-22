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
from tests.functional.libs.lib_thermal_reserve_pmin_mutualise import (
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
    
  
    de_milp = pd.DataFrame(data = {"Fonction_objectif":milp_resolution.solver.Objective().Value()[0]})
    de_milp.to_csv("result_milp.csv",index=False)

    #rajouter un chronomètre