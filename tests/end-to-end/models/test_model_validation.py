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
    "system_file, optim_result_file, timespan, batch, relative_accuracy",
    [
        ("dsr_validation.yml", "dsr_case_results.csv", 168, 20, 1e-6),
        ("base_validation.yml", "base_case_results.csv", 168, 20, 1e-6),
        ("electrolyser_validation.yml", "electrolyser_case_results.csv", 168, 20, 1e-6),
        ("storage_validation.yml", "storage_case_results.csv", 168, 20, 1e-6),
        ("bde_system.yml", "bde_case_results.csv", 168, 20, 1e-6),
    ],
)
def test_model_behaviour(
    system_file: str,
    optim_result_file: str,
    timespan: int,
    batch: int,
    relative_accuracy: float,
) -> None:
    scenarios = 1
    syspath = "tests/data/systems/"
    tspath = "tests/data/series/"
    respath = "tests/data/results/"
    libpaths = [
        "src/andromede/libs/antares_historic/antares_historic.yml",
        "src/andromede/libs/reference_models/andromede_v1_models.yml",
    ]
    compo_file = open(syspath + system_file)
    input_libraries = [parse_yaml_library(open(libfile)) for libfile in libpaths]
    input_component = parse_yaml_components(compo_file)
    result_lib = resolve_library(input_libraries)
    components_input = resolve_system(input_component, result_lib)
    database = build_data_base(input_component, Path(tspath))
    network = build_network(components_input)
    reference_values = (pd.read_csv(respath + optim_result_file, header=None)).values
    for k in range(batch):
        problem = build_problem(
            network,
            database,
            TimeBlock(1, [i for i in range(k * timespan, (k + 1) * timespan)]),
            scenarios,
        )
        status = problem.solver.Solve()
        assert status == problem.solver.OPTIMAL
        assert (
            relative_accuracy
            > abs(reference_values[k, 0] - problem.solver.Objective().Value())
            / reference_values[k, 0]
        )
