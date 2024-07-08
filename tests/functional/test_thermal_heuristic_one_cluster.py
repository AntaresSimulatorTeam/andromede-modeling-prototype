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
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd
import pytest

from andromede.libs.standard import (
    BALANCE_PORT_TYPE,
    DEMAND_MODEL,
    NODE_BALANCE_MODEL,
    SPILLAGE_MODEL,
    UNSUPPLIED_ENERGY_MODEL,
)
from andromede.simulation import OutputValues
from andromede.study import ConstantData, TimeScenarioSeriesData
from andromede.study.data import ComponentParameterIndex
from andromede.thermal_heuristic.data import ExpectedOutput, ExpectedOutputIndexes
from andromede.thermal_heuristic.problem import ThermalProblemBuilder
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
    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=168,
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
        number_week=1,
        list_scenario=list(range(1)),
    )

    main_resolution_step = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    status = main_resolution_step.solve()

    assert status == pywraplp.Solver.OPTIMAL
    assert main_resolution_step.objective == 16805387

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
    expected_output.check_output_values(main_resolution_step.output)


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
    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=168,
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
        number_week=1,
        list_scenario=list(range(1)),
    )

    main_resolution_step = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    status = main_resolution_step.solve()

    assert status == pywraplp.Solver.OPTIMAL
    assert main_resolution_step.objective == pytest.approx(16802840.55)

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
    expected_output.check_output_values(main_resolution_step.output)


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    thermal_problem_builder = ThermalProblemBuilder(
        number_hours=168,
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
        number_week=1,
        list_scenario=list(range(1)),
    )

    # First optimization
    resolution_step_1 = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    status = resolution_step_1.solve()
    assert status == pywraplp.Solver.OPTIMAL

    # Get number of on units and round it to integer
    thermal_problem_builder.update_database_accurate(
        resolution_step_1.output, 0, 0, None
    )
    for time_step in range(thermal_problem_builder.number_hours):
        assert (
            thermal_problem_builder.database.get_value(
                ComponentParameterIndex("G", "nb_units_min"), time_step, 0
            )
            == 2
            if time_step != 12
            else 3
        )

    # Solve heuristic problem
    resolution_step_accurate_heuristic = (
        thermal_problem_builder.get_resolution_step_accurate_heuristic(
            week=0, scenario=0, cluster_id="G"
        )
    )
    status = resolution_step_accurate_heuristic.solve()
    assert status == pywraplp.Solver.OPTIMAL

    thermal_problem_builder.update_database_accurate(
        resolution_step_accurate_heuristic.output, 0, 0, None
    )

    for time_step in range(thermal_problem_builder.number_hours):
        assert (
            thermal_problem_builder.database.get_value(
                ComponentParameterIndex("G", "nb_units_min"), time_step, 0
            )
            == 2
            if time_step != 12
            else 3
        )

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    status = resolution_step_2.solve()
    assert status == pywraplp.Solver.OPTIMAL
    assert resolution_step_2.objective == 16805387

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
    expected_output.check_output_values(resolution_step_2.output)


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
        number_week=1,
        list_scenario=list(range(1)),
    )

    # First optimization
    resolution_step_1 = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    status = resolution_step_1.solve()
    assert status == pywraplp.Solver.OPTIMAL

    thermal_problem_builder.update_database_fast_before_heuristic(
        resolution_step_1.output, 0, 0
    )
    # Solve heuristic problem
    resolution_step_heuristic = (
        thermal_problem_builder.get_resolution_step_fast_heuristic(
            thermal_cluster="G",
            week=0,
            scenario=0,
        )
    )
    resolution_step_heuristic.solve()
    thermal_problem_builder.update_database_fast_after_heuristic(
        resolution_step_heuristic.output, 0, 0, None
    )

    for time_step in range(number_hours):
        assert (
            thermal_problem_builder.database.get_value(
                ComponentParameterIndex("G", "min_generating"), time_step, 0
            )
            == 3 * 700
            if time_step in [t for t in range(10, 20)]
            else 2 * 700
        )

    # Second optimization with lower bound modified
    resolution_step_2 = thermal_problem_builder.get_main_resolution_step(
        week=0,
        scenario=0,
    )
    status = resolution_step_2.solve()
    assert status == pywraplp.Solver.OPTIMAL
    assert resolution_step_2.objective == pytest.approx(16850000)

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
    expected_output.check_output_values(resolution_step_2.output)
