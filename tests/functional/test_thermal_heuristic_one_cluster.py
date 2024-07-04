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

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from andromede.simulation import OutputValues
from andromede.study import ConstantData, TimeScenarioSeriesData
from andromede.thermal_heuristic.data import ExpectedOutput, ExpectedOutputIndexes
from andromede.thermal_heuristic.problem import (
    ThermalProblemBuilder,
)

from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    DEMAND_MODEL,
    NODE_BALANCE_MODEL,
    SPILLAGE_MODEL,
    UNSUPPLIED_ENERGY_MODEL,
)
from tests.functional.libs.lib_thermal_heuristic import THERMAL_CLUSTER_MODEL_MILP


def test_milp_version() -> None:
    """
    Model on 168 time steps with one thermal generation and one demand on a single node.
        - Demand is constant to 2000 MW except for the 13th hour for which it is 2050 MW
        - Thermal generation is characterized with:
            - P_min = 700 MW
            - P_max = 1000 MW
            - Min up time = 3
            - Min down time = 10
            - Generation cost = 50€ / MWh
            - Startup cost = 50
            - Fixed cost = 1 /h
            - Number of unit = 3
        - Unsupplied energy = 1000 €/MWh
        - Spillage = 0 €/MWh

    The optimal solution consists in turning on two thermal plants at the begining, turning on a third thermal plant at the 13th hour and turning off the first thermal plant at the 14th hour, the other two thermal plants stay on for the rest of the week producing 1000MW each. At the 13th hour, the production is [700,700,700] to satisfy Pmin constraints.

    The optimal cost is then :
          50 x 2 x 1000 x 167 (prod step 1-12 and 14-168)
        + 50 x 3 x 700 (prod step 13)
        + 50 (start up step 13)
        + 2 x 1 x 167 (fixed cost step 1-12 and 14-168)
        + 3 x 1 (fixed cost step 13)
        = 16 805 387
    """
    number_hours = 168

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=False,
        fast=False,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_one_cluster",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[BALANCE_PORT_TYPE],
        models=[
            DEMAND_MODEL,
            NODE_BALANCE_MODEL,
            SPILLAGE_MODEL,
            UNSUPPLIED_ENERGY_MODEL,
        ],
    )

    problem = thermal_problem_builder.get_main_problem(
        lower_bound={"G": ConstantData(0)},
        week=0,
        scenario=0,
    )
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 16805387

    expected_output = ExpectedOutput(
        mode="milp",
        week=0,
        scenario=0,
        dir_path="data/thermal_heuristic_one_cluster",
        list_cluster=["G"],
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
        ),
    )
    expected_output.check_output_values(problem)


def test_lp_version() -> None:
    """
    Model on 168 time steps with one thermal generation and one demand on a single node.
        - Demand is constant to 2000 MW except for the 13th hour for which it is 2050 MW
        - Thermal generation is characterized with:
            - P_min = 700 MW
            - P_max = 1000 MW
            - Min up time = 3
            - Min down time = 10
            - Generation cost = 50€ / MWh
            - Startup cost = 50
            - Fixed cost = 1 /h
            - Number of unit = 3
        - Unsupplied energy = 1000 €/MWh
        - Spillage = 0 €/MWh

    The optimal solution consists in producing exactly the demand at each hour. The number of on units is equal to the production divided by P_max.

    The optimal cost is then :
          50 x 2000 x 167 (prod step 1-12 and 14-168)
        + 50 x 2050 (prod step 13)
        + 2 x 1 x 168 (fixed cost step 1-12 and 14-168)
        + 2050/1000 x 1 (fixed cost step 13)
        + 0,05 x 50 (start up cost step 13)
        = 16 802 840,55
    """
    number_hours = 168

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=True,
        fast=False,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_one_cluster",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[BALANCE_PORT_TYPE],
        models=[
            DEMAND_MODEL,
            NODE_BALANCE_MODEL,
            SPILLAGE_MODEL,
            UNSUPPLIED_ENERGY_MODEL,
        ],
    )

    problem = thermal_problem_builder.get_main_problem(
        lower_bound={"G": ConstantData(0)},
        week=0,
        scenario=0,
    )
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == pytest.approx(16802840.55)

    expected_output = ExpectedOutput(
        mode="lp",
        week=0,
        scenario=0,
        dir_path="data/thermal_heuristic_one_cluster",
        list_cluster=["G"],
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=29, idx_unsupplied=25
        ),
    )
    expected_output.check_output_values(
        problem,
    )


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=True,
        fast=False,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_one_cluster",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[BALANCE_PORT_TYPE],
        models=[
            DEMAND_MODEL,
            NODE_BALANCE_MODEL,
            SPILLAGE_MODEL,
            UNSUPPLIED_ENERGY_MODEL,
        ],
    )

    # First optimization
    problem_optimization_1 = thermal_problem_builder.get_main_problem(
        lower_bound={"G": ConstantData(0)},
        week=0,
        scenario=0,
    )
    status = problem_optimization_1.solver.Solve()

    assert status == problem_optimization_1.solver.OPTIMAL

    # Get number of on units and round it to integer
    output_1 = OutputValues(problem_optimization_1)
    nb_on_1 = pd.DataFrame(
        np.transpose(
            np.ceil(np.round(np.array(output_1.component("G").var("nb_on").value), 12))
        ),
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    n_guide = TimeScenarioSeriesData(nb_on_1)
    for time_step in range(number_hours):
        assert nb_on_1.iloc[time_step, 0] == 2 if time_step != 12 else 3

    # Solve heuristic problem
    problem_accurate_heuristic = thermal_problem_builder.get_problem_accurate_heuristic(
        {"G": n_guide}, week=0, scenario=0, cluster_id="G"
    )
    status = problem_accurate_heuristic.solver.Solve()

    assert status == problem_accurate_heuristic.solver.OPTIMAL

    output_heuristic = OutputValues(problem_accurate_heuristic)
    nb_on_heuristic = pd.DataFrame(
        np.transpose(
            np.ceil(np.array(output_heuristic.component("G").var("nb_on").value))
        ),
        index=[i for i in range(number_hours)],
        columns=[0],
    )
    nb_on_min = TimeScenarioSeriesData(nb_on_heuristic)

    for time_step in range(number_hours):
        assert nb_on_heuristic.iloc[time_step, 0] == 2 if time_step != 12 else 3

    # Second optimization with lower bound modified
    problem_optimization_2 = thermal_problem_builder.get_main_problem(
        lower_bound={"G": nb_on_min},
        week=0,
        scenario=0,
    )
    status = problem_optimization_2.solver.Solve()

    assert status == problem_optimization_2.solver.OPTIMAL
    assert problem_optimization_2.solver.Objective().Value() == 16805387

    expected_output = ExpectedOutput(
        mode="accurate",
        week=0,
        scenario=0,
        dir_path="data/thermal_heuristic_one_cluster",
        list_cluster=["G"],
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=33, idx_unsupplied=29
        ),
    )
    expected_output.check_output_values(problem_optimization_2)


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    Model on 168 time steps with one thermal generation and one demand on a single node.
        - Demand is constant to 2000 MW except for the 13th hour for which it is 2050 MW
        - Thermal generation is characterized with:
            - P_min = 700 MW
            - P_max = 1000 MW
            - Min up time = 3
            - Min down time = 10
            - Generation cost = 50€ / MWh
            - Startup cost = 50
            - Fixed cost = 1 /h
            - Number of unit = 3
        - Unsupplied energy = 1000 €/MWh
        - Spillage = 0 €/MWh

    The optimal solution consists in having 3 units turned on between time steps 10 and 19 with production equal to 2100 to respect pmin and 2 the rest of the time.

    The optimal cost is then :
          50 x 2000 x 158 (prod step 1-9 and 20-168)
        + 50 x 2100 x 10 (prod step 10-19)
        = 16 850 000
    """

    number_hours = 168

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=number_hours,
        lp_relaxation=True,
        fast=True,
        data_dir=Path(__file__).parent / "data/thermal_heuristic_one_cluster",
        initial_thermal_model=THERMAL_CLUSTER_MODEL_MILP,
        port_types=[BALANCE_PORT_TYPE],
        models=[
            DEMAND_MODEL,
            NODE_BALANCE_MODEL,
            SPILLAGE_MODEL,
            UNSUPPLIED_ENERGY_MODEL,
        ],
    )

    # First optimization
    problem_optimization_1 = thermal_problem_builder.get_main_problem(
        lower_bound={"G": ConstantData(0)},
        week=0,
        scenario=0,
    )
    status = problem_optimization_1.solver.Solve()

    assert status == problem_optimization_1.solver.OPTIMAL

    # Get number of on units
    output_1 = OutputValues(problem_optimization_1)

    # Solve heuristic problem
    problem_heuristic = thermal_problem_builder.get_problem_fast_heuristic(
        output_1.component("G").var("generation").value[0],  # type:ignore
        thermal_cluster="G",
        week=0,
        scenario=0,
    )
    mingen_heuristic = thermal_problem_builder.get_output_heuristic_fast(
        problem_heuristic, 0, 0, "G"
    )

    mingen = TimeScenarioSeriesData(mingen_heuristic)

    for time_step in range(number_hours):
        assert (
            mingen_heuristic.iloc[time_step, 0] == 3 * 700
            if time_step in [t for t in range(10, 20)]
            else 2 * 700
        )

    # Second optimization with lower bound modified
    problem_optimization_2 = thermal_problem_builder.get_main_problem(
        lower_bound={"G": mingen},
        week=0,
        scenario=0,
    )
    status = problem_optimization_2.solver.Solve()

    assert status == problem_optimization_2.solver.OPTIMAL
    assert problem_optimization_2.solver.Objective().Value() == pytest.approx(16850000)

    expected_output = ExpectedOutput(
        mode="fast",
        week=0,
        scenario=0,
        dir_path="data/thermal_heuristic_one_cluster",
        list_cluster=["G"],
        output_idx=ExpectedOutputIndexes(
            idx_generation=4, idx_nodu=6, idx_spillage=33, idx_unsupplied=29
        ),
    )
    expected_output.check_output_values(problem_optimization_2)
