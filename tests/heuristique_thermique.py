import ortools.linear_solver.pywraplp as pywraplp

from andromede.simulation import OutputValues
from andromede.thermal_heuristic.model import (
    HeuristicAccurateModelBuilder,
)
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd

from andromede.simulation import BlockBorderManagement, TimeBlock, build_problem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    TimeScenarioSeriesData,
    create_component,
)
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP


number_hours = 168

database = DataBase()

failures_1 = pd.DataFrame(
    np.zeros(168),  # A MODIFIER
    index=[i for i in range(number_hours)],
    columns=[1],  # A MODIFIER SI TU N'ES PAS SUR UN SCENARIO
)

database.add_data("G1", "p_max", ConstantData(410))
database.add_data("G1", "p_min", ConstantData(180))
database.add_data("G1", "cost", ConstantData(96))
database.add_data("G1", "startup_cost", ConstantData(100500))
database.add_data("G1", "fixed_cost", ConstantData(1))
database.add_data("G1", "d_min_up", ConstantData(8))
database.add_data("G1", "d_min_down", ConstantData(8))
database.add_data("G1", "nb_units_min", ConstantData(0))
database.add_data("G1", "nb_units_max", ConstantData(1))
database.add_data("G1", "nb_units_max_min_down_time", ConstantData(1))
database.add_data("G1", "max_generating", TimeScenarioSeriesData(failures_1))
database.add_data("G1", "min_generating", ConstantData(0))

time_block = TimeBlock(1, [i for i in range(number_hours)])

gen1 = create_component(
    model=HeuristicAccurateModelBuilder(THERMAL_CLUSTER_MODEL_MILP).model, id="G1"
)

network = Network("test")
network.add_component(gen1)

# Solve heuristic problem
resolution_step_accurate_heuristic = build_problem(
    network,
    database,
    TimeBlock(1, [i for i in range(number_hours)]),
    [1],
    border_management=BlockBorderManagement.CYCLE,
)
status = resolution_step_accurate_heuristic.solver.Solve()
assert status == pywraplp.Solver.OPTIMAL

sol = (
    OutputValues(resolution_step_accurate_heuristic)
    .component("G1")
    .var("nb_on")
    .value[0]
)
