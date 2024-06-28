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
from typing import List

import numpy as np
import pandas as pd
import pytest

from andromede.simulation import OutputValues
from andromede.simulation.optimization import OptimizationProblem
from andromede.study import ConstantData, TimeScenarioSeriesData


def get_max_unit_for_min_down_time(delta: int, max_units: pd.DataFrame) -> pd.DataFrame:
    nb_units_max_min_down_time = pd.DataFrame(
        np.roll(max_units.values, delta), index=max_units.index
    )
    end_failures = max_units - pd.DataFrame(
        np.roll(max_units.values, 1), index=max_units.index
    )
    end_failures.where(end_failures > 0, 0, inplace=True)
    for j in range(delta):
        nb_units_max_min_down_time += pd.DataFrame(
            np.roll(end_failures.values, j), index=end_failures.index
        )

    return nb_units_max_min_down_time


def get_max_failures(max_units: pd.DataFrame) -> pd.DataFrame:
    max_failures = (
        pd.DataFrame(np.roll(max_units.values, 1), index=max_units.index) - max_units
    )
    max_failures.where(max_failures > 0, 0, inplace=True)
    return max_failures


def get_max_unit(
    pmax: float, units: float, max_generating: pd.DataFrame
) -> pd.DataFrame:
    max_units = max_generating / pmax
    max_units.where(max_units < units, units, inplace=True)
    return max_units


def get_failures_for_cluster(
    week: int, scenario: int, cluster: str, number_hours: int, dir_path: str
) -> pd.DataFrame:
    input_file = np.loadtxt(
        "tests/functional/" + dir_path + f"/series_{cluster}.txt",
        delimiter="\t",
    )

    failures_data = pd.DataFrame(
        data=input_file[
            number_hours * week : number_hours * week + number_hours, scenario
        ],
        index=[i for i in range(number_hours)],
        columns=[0],
    )

    return failures_data


def check_output_values(
    problem: OptimizationProblem, mode: str, week: int, scenario: int, dir_path: str
) -> None:
    output = OutputValues(problem)

    expected_output_clusters_file = open(
        "tests/functional/"
        + dir_path
        + "/"
        + mode
        + "/"
        + str(scenario)
        + "/details-hourly.txt",
        "r",
    )
    expected_output_clusters = expected_output_clusters_file.readlines()

    expected_output_general_file = open(
        "tests/functional/"
        + dir_path
        + "/"
        + mode
        + "/"
        + str(scenario)
        + "/values-hourly.txt",
        "r",
    )
    expected_output_general = expected_output_general_file.readlines()

    assert output.component("G1").var("generation").value == [
        [
            pytest.approx(float(line.strip().split("\t")[4]))
            for line in expected_output_clusters[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]
    if mode != "fast":
        assert output.component("G1").var("nb_on").value == [
            [
                pytest.approx(float(line.strip().split("\t")[12]))
                for line in expected_output_clusters[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ]
        ]

    assert output.component("G2").var("generation").value == [
        [
            pytest.approx(float(line.strip().split("\t")[5]))
            for line in expected_output_clusters[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]
    if mode != "fast":
        assert output.component("G2").var("nb_on").value == [
            [
                pytest.approx(float(line.strip().split("\t")[13]))
                for line in expected_output_clusters[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ]
        ]

    assert output.component("G3").var("generation").value == [
        [
            pytest.approx(float(line.strip().split("\t")[6]))
            for line in expected_output_clusters[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]
    if mode != "fast":
        assert output.component("G3").var("nb_on").value == [
            [
                pytest.approx(float(line.strip().split("\t")[14]))
                for line in expected_output_clusters[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ]
        ]

    assert output.component("S").var("spillage").value == [
        [
            pytest.approx(float(line.strip().split("\t")[20 if mode == "milp" else 21]))
            for line in expected_output_general[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]

    assert output.component("U").var("unsupplied_energy").value == [
        [
            pytest.approx(float(line.strip().split("\t")[19 if mode == "milp" else 20]))
            for line in expected_output_general[168 * week + 7 : 168 * week + 7 + 168]
        ]
    ]
