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

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pytest

from andromede.simulation import OutputValues
from andromede.simulation.optimization import OptimizationProblem


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


@dataclass
class OutputIndexes:
    idx_generation: int
    idx_nodu: int
    idx_spillage: int
    idx_unsupplied: int


@dataclass
class OutputValuesParameters:
    mode: str
    week: int
    scenario: int
    dir_path: str
    list_cluster: list[str]
    output_idx: OutputIndexes


def check_output_values(
    problem: OptimizationProblem, parameters: OutputValuesParameters
) -> None:
    output = OutputValues(problem)

    expected_output_clusters, expected_output_general = read_expected_output(
        parameters.mode, parameters.scenario, parameters.dir_path, parameters.week
    )

    for i, cluster in enumerate(parameters.list_cluster):
        check_output_cluster(
            parameters.mode,
            output,
            expected_output_clusters,
            idx_generation=parameters.output_idx.idx_generation + i,
            idx_nodu=parameters.output_idx.idx_nodu + i,
            cluster_id=cluster,
        )

    assert output.component("S").var("spillage").value == [
        [
            pytest.approx(float(line[parameters.output_idx.idx_spillage]))
            for line in expected_output_general
        ]
    ]

    assert output.component("U").var("unsupplied_energy").value == [
        [
            pytest.approx(float(line[parameters.output_idx.idx_unsupplied]))
            for line in expected_output_general
        ]
    ]


def check_output_cluster(
    mode: str,
    output: OutputValues,
    expected_output_clusters: list[list[str]],
    idx_generation: int,
    idx_nodu: int,
    cluster_id: str,
) -> None:
    assert output.component(cluster_id).var("generation").value == [
        [
            pytest.approx(float(line[idx_generation]))
            for line in expected_output_clusters
        ]
    ]
    if mode != "fast":
        assert output.component(cluster_id).var("nb_on").value == [
            [pytest.approx(float(line[idx_nodu])) for line in expected_output_clusters]
        ]


def read_expected_output(
    mode: str, scenario: int, dir_path: str, week: int
) -> tuple[list[list[str]], list[list[str]]]:
    folder_name = "tests/functional/" + dir_path + "/" + mode + "/" + str(scenario)

    expected_output_clusters_file = open(
        folder_name + "/details-hourly.txt",
        "r",
    )
    expected_output_clusters = expected_output_clusters_file.readlines()

    expected_output_general_file = open(
        folder_name + "/values-hourly.txt",
        "r",
    )
    expected_output_general = expected_output_general_file.readlines()
    return (
        [
            line.strip().split("\t")
            for line in expected_output_clusters[168 * week + 7 : 168 * week + 7 + 168]
        ],
        [
            line.strip().split("\t")
            for line in expected_output_general[168 * week + 7 : 168 * week + 7 + 168]
        ],
    )
