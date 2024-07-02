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

from andromede.simulation import OutputValues
from andromede.study import ConstantData, TimeScenarioSeriesData
from andromede.thermal_heuristic.problem import (
    create_problem_accurate_heuristic,
    create_problem_fast_heuristic,
)


def test_accurate_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic accurate of Antares
    """

    number_hours = 168
    scenario = 0
    week = 0

    parameters = pywraplp.MPSolverParameters()
    parameters.SetIntegerParam(parameters.PRESOLVE, parameters.PRESOLVE_OFF)
    parameters.SetIntegerParam(parameters.SCALING, 0)

    for j, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):
        nb_on_1 = pd.DataFrame(
            np.transpose(
                np.ceil(
                    np.round(
                        np.loadtxt(
                            f"tests/functional/data/thermal_heuristic_six_clusters/accurate/itr1_accurate_cluster{j+1}.txt"
                        ),
                        12,
                    )
                )
            ),
            index=[i for i in range(number_hours)],
            columns=[0],
        )
        n_guide = TimeScenarioSeriesData(nb_on_1)

        # Solve heuristic problem
        problem_accurate_heuristic = create_problem_accurate_heuristic(
            {
                "G" + str(i): ConstantData(0) if "G" + str(i) != cluster else n_guide
                for i in range(1, 7)
            },
            number_hours,
            data_dir=Path(__file__).parent / "data/thermal_heuristic_six_clusters",
            thermal_cluster=cluster,
            week=week,
            scenario=scenario,
        )
        status = problem_accurate_heuristic.solver.Solve(parameters)

        assert status == problem_accurate_heuristic.solver.OPTIMAL

        output_heuristic = OutputValues(problem_accurate_heuristic)
        nb_on_heuristic = np.transpose(
            np.ceil(np.array(output_heuristic.component(cluster).var("nb_on").value))
        )

        expected_output = np.loadtxt(
            f"tests/functional/data/thermal_heuristic_six_clusters/accurate/itr2_accurate_cluster{j+1}.txt"
        )
        assert nb_on_heuristic[:, 0] == [pytest.approx(x) for x in expected_output]


def test_fast_heuristic() -> None:
    """
    Solve the same problem as before with the heuristic fast of Antares
    """
    number_hours = 168
    scenario = 0
    week = 0

    for j, cluster in enumerate(["G" + str(i) for i in range(1, 7)]):
        nb_on_1 = np.loadtxt(
            f"tests/functional/data/thermal_heuristic_six_clusters/fast/itr1_fast_cluster{j+1}.txt"
        )

        # Solve heuristic problem
        mingen_heuristic = create_problem_fast_heuristic(
            nb_on_1,  # type:ignore
            number_hours,
            thermal_cluster=cluster,
            data_dir=Path(__file__).parent / "data/thermal_heuristic_six_clusters",
            week=week,
            scenario=scenario,
        )

        expected_output = np.loadtxt(
            f"tests/functional/data/thermal_heuristic_six_clusters/fast/itr2_fast_cluster{j+1}.txt"
        )
        assert mingen_heuristic.values[:, 0] == [
            pytest.approx(x) for x in expected_output
        ]
