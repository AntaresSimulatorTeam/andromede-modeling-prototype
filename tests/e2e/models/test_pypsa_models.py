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
import pandas as pd
import pytest
from pathlib import Path
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
    "system_file, systems_dir, series_dir,timespan, target_value, relative_accuracy",
    [
        (
            "pypsa_basic_system.yml",
            "tests/data/systems/",
            "tests/data/series/",
            2,
            7500,
            1e-6,
        ),
    ],
)
def test_model_behaviour(
    system_file: str,
    systems_dir: Path,
    series_dir: Path,
    timespan: float,
    target_value: float,
    relative_accuracy: float,
) -> None:
    scenarios = 1

    with open(systems_dir + system_file) as compo_file:
        with open("src/andromede/libs/pypsa_models/pypsa_models.yml") as lib_file1:
            input_libraries = [parse_yaml_library(lib_file1)]
            input_component = parse_yaml_components(compo_file)
            result_lib = resolve_library(input_libraries)
            components_input = resolve_system(input_component, result_lib)
            database = build_data_base(input_component, Path(series_dir))
            network = build_network(components_input)
            problem = build_problem(
                network,
                database,
                TimeBlock(1, [i for i in range(0, timespan)]),
                scenarios,
            )
            status = problem.solver.Solve()
            print(problem.solver.Objective().Value())
            assert status == problem.solver.OPTIMAL
            assert math.isclose(
                target_value,
                problem.solver.Objective().Value(),
                rel_tol=relative_accuracy,
            )
