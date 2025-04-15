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

import math
from pathlib import Path

import pandas as pd
import pytest

from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation.optimization import build_problem
from andromede.simulation.time_block import TimeBlock
from andromede.study.parsing import parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    resolve_system,
)


@pytest.mark.parametrize(
    "system_file, optim_result_file, timespan, batch, relative_accuracy, results_dir, systems_dir, series_dir",
    [
        (
            "dsr_validation.yml",
            "dsr_case_results.csv",
            168,
            20,
            1e-6,
            "tests/e2e/models/results/",
            "tests/e2e/models/systems/",
            "tests/e2e/models/series/",
        ),
        (
            "base_validation.yml",
            "base_case_results.csv",
            168,
            20,
            1e-6,
            "tests/e2e/models/results/",
            "tests/e2e/models/systems/",
            "tests/e2e/models/series/",
        ),
        (
            "electrolyser_validation.yml",
            "electrolyser_case_results.csv",
            168,
            20,
            1e-6,
            "tests/e2e/models/results/",
            "tests/e2e/models/systems/",
            "tests/e2e/models/series/",
        ),
        (
            "storage_validation.yml",
            "storage_case_results.csv",
            168,
            20,
            1e-6,
            "tests/e2e/models/results/",
            "tests/e2e/models/systems/",
            "tests/e2e/models/series/",
        ),
        (
            "bde_system.yml",
            "bde_case_results.csv",
            168,
            20,
            1e-6,
            "tests/e2e/models/results/",
            "tests/e2e/models/systems/",
            "tests/e2e/models/series/",
        ),
        (
            "cluster_validation_1.yml",
            "cluster_testing1_results.csv",
            168,
            20,
            1e-6,
            "tests/e2e/models/results/",
            "tests/e2e/models/systems/",
            "tests/e2e/models/series/",
        ),
        (
            "cluster_validation_2.yml",
            "cluster_testing2_results.csv",
            168,
            20,
            1e-4,  # Default Fico XPRESS Tolerance
            "tests/e2e/models/results/",
            "tests/e2e/models/systems/",
            "tests/e2e/models/series/",
        ),
    ],
)
def test_model_behaviour(
    system_file: str,
    optim_result_file: str,
    timespan: int,
    batch: int,
    relative_accuracy: float,
    results_dir: Path,
    systems_dir: Path,
    series_dir: Path,
) -> None:
    scenarios = 1

    with open(systems_dir + system_file) as compo_file:
        with open(
            "src/andromede/libs/antares_historic/antares_historic.yml"
        ) as lib_file1:
            with open(
                "src/andromede/libs/reference_models/andromede_v1_models.yml"
            ) as lib_file2:
                input_libraries = [
                    parse_yaml_library(lib_file1),
                    parse_yaml_library(lib_file2),
                ]
                input_component = parse_yaml_components(compo_file)
                result_lib = resolve_library(input_libraries)
                components_input = resolve_system(input_component, result_lib)
                database = build_data_base(input_component, Path(series_dir))
                network = build_network(components_input)

                reference_values = pd.read_csv(
                    results_dir + optim_result_file, header=None
                ).values
                for k in range(batch):
                    problem = build_problem(
                        network,
                        database,
                        TimeBlock(
                            1, [i for i in range(k * timespan, (k + 1) * timespan)]
                        ),
                        scenarios,
                    )
                    status = problem.solver.Solve()
                    assert status == problem.solver.OPTIMAL
                    assert math.isclose(
                        reference_values[k, 0],
                        problem.solver.Objective().Value(),
                        rel_tol=relative_accuracy,
                    )
