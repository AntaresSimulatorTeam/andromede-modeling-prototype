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
from math import ceil

import numpy as np
import pandas as pd
import pytest

from andromede.simulation import OutputValues
from andromede.simulation.optimization import OptimizationProblem


def get_max_unit_for_min_down_time(delta: int, max_units: pd.DataFrame) -> pd.DataFrame:
    nb_units_max_min_down_time = pd.DataFrame(
        np.roll(max_units.values, delta, axis=0), index=max_units.index
    )
    end_failures = max_units - pd.DataFrame(
        np.roll(max_units.values, 1, axis=0), index=max_units.index
    )
    end_failures.where(end_failures > 0, 0, inplace=True)
    for j in range(delta):
        nb_units_max_min_down_time += pd.DataFrame(
            np.roll(end_failures.values, j, axis=0), index=end_failures.index
        )

    return nb_units_max_min_down_time


def get_max_failures(max_units: pd.DataFrame) -> pd.DataFrame:
    max_failures = (
        pd.DataFrame(np.roll(max_units.values, 1, axis=0), index=max_units.index)
        - max_units
    )
    max_failures.where(max_failures > 0, 0, inplace=True)
    return max_failures


def get_max_unit(
    pmax: float, units: float, max_generating: pd.DataFrame
) -> pd.DataFrame:
    max_units = max_generating / pmax
    max_units = max_units.applymap(ceil)
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
class ExpectedOutputIndexes:
    idx_generation: int
    idx_nodu: int
    idx_spillage: int
    idx_unsupplied: int


class ExpectedOutput:
    def __init__(
        self,
        mode: str,
        week: int,
        scenario: int,
        dir_path: str,
        list_cluster: list[str],
        output_idx: ExpectedOutputIndexes,
    ):
        self.mode = mode
        self.list_cluster = list_cluster
        self.output_idx = output_idx
        self.output_cluster, self.output_general = self.read_expected_output(
            scenario, dir_path, week
        )

    def check_output_values(self, problem: OptimizationProblem) -> None:
        output = OutputValues(problem)

        for i, cluster in enumerate(self.list_cluster):
            self.check_output_cluster(
                output,
                cluster_id=cluster,
                idx_generation=self.output_idx.idx_generation + i,
                idx_nodu=self.output_idx.idx_nodu + i,
            )

        assert output.component("S").var("spillage").value == [
            [
                pytest.approx(float(line[self.output_idx.idx_spillage]))
                for line in self.output_general
            ]
        ]

        assert output.component("U").var("unsupplied_energy").value == [
            [
                pytest.approx(float(line[self.output_idx.idx_unsupplied]))
                for line in self.output_general
            ]
        ]

    def check_output_cluster(
        self,
        output: OutputValues,
        idx_generation: int,
        idx_nodu: int,
        cluster_id: str,
    ) -> None:
        assert output.component(cluster_id).var("generation").value == [
            [pytest.approx(float(line[idx_generation])) for line in self.output_cluster]
        ]
        if self.mode != "fast":
            assert output.component(cluster_id).var("nb_on").value == [
                [pytest.approx(float(line[idx_nodu])) for line in self.output_cluster]
            ]

    def read_expected_output(
        self, scenario: int, dir_path: str, week: int
    ) -> tuple[list[list[str]], list[list[str]]]:
        folder_name = (
            "tests/functional/" + dir_path + "/" + self.mode + "/" + str(scenario)
        )

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
                for line in expected_output_clusters[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ],
            [
                line.strip().split("\t")
                for line in expected_output_general[
                    168 * week + 7 : 168 * week + 7 + 168
                ]
            ],
        )
