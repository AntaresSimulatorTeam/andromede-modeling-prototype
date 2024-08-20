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

import pytest

from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from dataclasses import dataclass

import pytest

from andromede.simulation import OutputValues
from andromede.thermal_heuristic.time_scenario_parameter import BlockScenarioIndex
from typing import List, Tuple


@pytest.fixture(scope="session")
def libs_dir() -> Path:
    return Path(__file__).parent / "libs"


@pytest.fixture(scope="session")
def lib(libs_dir: Path):
    lib_file = libs_dir / "lib.yml"

    with lib_file.open() as f:
        input_lib = parse_yaml_library(f)

    lib = resolve_library(input_lib)
    return lib


@dataclass(frozen=True)
class ExpectedOutputIndexes:
    idx_generation: int
    idx_nodu: int
    idx_spillage: int
    idx_unsupplied: int


class ExpectedOutput:
    def __init__(
        self,
        mode: str,
        index: BlockScenarioIndex,
        dir_path: str,
        list_cluster: List[str],
        output_idx: ExpectedOutputIndexes,
    ):
        self.mode = mode
        self.list_cluster = list_cluster
        self.output_idx = output_idx
        self.output_cluster, self.output_general = self.read_expected_output(
            dir_path, index
        )

    def check_output_values(self, output: OutputValues) -> None:
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
            [
                pytest.approx(float(line[idx_generation]), abs=1e-6)
                for line in self.output_cluster
            ]
        ]
        if self.mode != "fast":
            assert output.component(cluster_id).var("nb_on").value == [
                [pytest.approx(float(line[idx_nodu])) for line in self.output_cluster]
            ]

    def read_expected_output(
        self, dir_path: str, index: BlockScenarioIndex
    ) -> Tuple[List[List[str]], List[List[str]]]:
        folder_name = (
            "tests/functional/" + dir_path + "/" + self.mode + "/" + str(index.scenario)
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
                    168 * index.week + 7 : 168 * index.week + 7 + 168
                ]
            ],
            [
                line.strip().split("\t")
                for line in expected_output_general[
                    168 * index.week + 7 : 168 * index.week + 7 + 168
                ]
            ],
        )
