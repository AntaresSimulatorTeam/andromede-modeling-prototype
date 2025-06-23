# Copyright (c) 2025, RTE (https://www.rte-france.com)
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

import sys
from pathlib import Path

path = Path(__file__).parents[3] / "src"
sys.path.append(str(path))

import pandas as pd

from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation.optimization import (
    BlockBorderManagement,
    OptimizationProblem,
    build_problem,
)
from andromede.simulation.output_values import OutputValues
from andromede.simulation.time_block import TimeBlock
from andromede.study.network import Network
from andromede.study.parsing import parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    consistency_check,
    resolve_system,
)

CURRENT_DIR = Path(__file__).parent
SYSTEM_FILE = CURRENT_DIR / "systems/system_demo.yml"
LIB_FILE = CURRENT_DIR / "libs/lib_demo.yml"
SERIES_DIR = CURRENT_DIR / "series"
OUTPUT_DIR = CURRENT_DIR / "output"

with LIB_FILE.open() as lib:
    input_library = parse_yaml_library(lib)

with SYSTEM_FILE.open() as c:
    input_system = parse_yaml_components(c)

lib_dict = resolve_library([input_library])
network_components = resolve_system(input_system, lib_dict)
consistency_check(network_components.components, lib_dict["lib_demo"].models)

database = build_data_base(input_system, SERIES_DIR)
network = build_network(network_components)

scenarios = 1
horizon_begin = 108
horizon_end = 132

time_steps = list(range(horizon_begin, horizon_end))
time_blocks = [TimeBlock(0, time_steps)]

problem = build_problem(
    network,
    database,
    time_blocks[0],
    scenarios,
    border_management=BlockBorderManagement.CYCLE,
)

status = problem.solver.Solve()
print(f"Problem objective: {problem.solver.Objective().Value()}")


def process_output(
    problem: OptimizationProblem,
    series_dir: Path,
    output_dir: Path,
    network: Network,
    time_steps: int,
):
    output = OutputValues(problem)

    df = pd.DataFrame()
    for component in network.components:
        for variable in component.model.variables:
            if variable in [
                "generation",
                "p_injection",
                "p_withdrawal",
                "spillage",
                "unsupplied_energy",
            ]:
                var_values = output.component(component.id).var(variable)._value
                if variable in ["spillage", "p_injection"]:
                    var_values = {key: value * -1 for key, value in var_values.items()}
                df[f"{component.id}_{variable}"] = var_values

    df.reset_index(inplace=True, drop=True)
    df["solar_generation"] = (
        pd.read_csv(series_dir / "solar_demo.txt", header=None)
        .iloc[time_steps]
        .reset_index(drop=True)
    )
    df["wind_generation"] = (
        pd.read_csv(series_dir / "wind_demo.txt", header=None)
        .iloc[time_steps]
        .reset_index(drop=True)
    )
    df["load"] = (
        pd.read_csv(series_dir / "load_demo.txt", header=None)
        .iloc[time_steps]
        .reset_index(drop=True)
    )

    for prod_type in ["Nuclear", "Gas", "Fioul", "Coal", "Peak"]:
        cols = [col for col in df.columns if prod_type in col]
        df[prod_type] = df[cols].sum(axis=1)
        df.drop(columns=cols, inplace=True)
    df = df[
        [
            "load",
            "Nuclear",
            "Coal",
            "Gas",
            "Fioul",
            "Peak",
            "wind_generation",
            "solar_generation",
            "Hydro_generation",
            "DE_unsupplied_energy",
            "DE_spillage",
            "Battery1_p_withdrawal",
            "Battery1_p_injection",
        ]
    ]

    df.to_csv(output_dir / "output.csv", sep=";")


process_output(problem, SERIES_DIR, OUTPUT_DIR, network, time_steps)
