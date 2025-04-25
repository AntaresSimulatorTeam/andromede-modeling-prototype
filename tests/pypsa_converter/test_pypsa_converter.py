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

import pypsa

from andromede.input_converter.src.logger import Logger
from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.pypsa_converter.pypsa_converter import PyPSAStudyConverter
from andromede.pypsa_converter.utils import transform_to_yaml
from andromede.simulation.optimization import OptimizationProblem, build_problem
from andromede.simulation.time_block import TimeBlock
from andromede.study.parsing import InputSystem, parse_yaml_components
from andromede.study.resolve_components import (
    System,
    build_data_base,
    build_network,
    resolve_system,
)


def test_load_gen(systems_dir: Path, series_dir: Path) -> None:
    # Building the PyPSA test problem
    T = 10
    n1 = pypsa.Network(name="Demo", snapshots=[i for i in range(T)])
    n1.add("Bus", "pypsatown", v_nom=1)
    n1.add(
        "Load", "pypsaload", bus="pypsatown", p_set=[i * 10 for i in range(T)], q_set=0
    )
    n1.add("Load", "pypsaload2", bus="pypsatown", p_set=100, qset=0)
    n1.add(
        "Generator",
        "pypsagenerator",
        bus="pypsatown",
        p_nom_extendable=False,
        marginal_cost=50,  # €/MWh
        p_nom=200,  # MW
    )
    n1.add(
        "Generator",
        "pypsagenerator2",
        bus="pypsatown",
        p_nom_extendable=False,
        marginal_cost=40,  # €/MWh
        p_nom=50,  # MW
    )
    n1.optimize()

    # Testing the PyPSA_to_Andromede converter
    run_conversion_test(n1, n1.objective, "test1.yml", systems_dir, series_dir)


def test_load_gen_link(systems_dir: Path, series_dir: Path) -> None:
    T = 10
    n1 = pypsa.Network(name="Demo2", snapshots=[i for i in range(T)])
    n1.add("Bus", "pypsatown", v_nom=1)
    n1.add(
        "Load", "pypsaload", bus="pypsatown", p_set=[i * 10 for i in range(T)], q_set=0
    )
    n1.add("Load", "pypsaload2", bus="pypsatown", p_set=100, qset=0)
    n1.add(
        "Generator",
        "pypsagenerator",
        bus="pypsatown",
        p_nom_extendable=False,
        marginal_cost=50,  # €/MWh
        p_nom=200,  # MW
    )
    n1.add(
        "Generator",
        "pypsagenerator2",
        bus="pypsatown",
        p_nom_extendable=False,
        marginal_cost=40,  # €/MWh
        p_nom=50,  # MW
    )
    n1.add("Bus", "paris", v_nom=1)
    n1.add("Load", "parisload", bus="paris", p_set=200, qset=0)
    n1.add(
        "Generator",
        "pypsagenerator3",
        bus="paris",
        p_nom_extendable=False,
        marginal_cost=200,  # €/MWh
        p_nom=200,  # MW
    )
    n1.add(
        "Link",
        "link-paris-pypsatown",
        bus0="pypsatown",
        bus1="paris",
        efficiency=0.9,
        marginal_cost=0.5,
        p_nom=50,
        p_min_pu=-1,
        p_max_pu=[i / T for i in range(T)],
    )
    n1.optimize()

    # Testing the PyPSA_to_Andromede converter
    run_conversion_test(n1, n1.objective, "test2.yml", systems_dir, series_dir)


def run_conversion_test(
    pypsa_network: pypsa.Network,
    target_value: float,
    system_filename: str,
    systems_dir: Path,
    series_dir: Path,
):
    T = len(pypsa_network.timesteps)

    # Conversion to Andromede System
    input_system_from_pypsa_converter = convert_pypsa_network(
        pypsa_network, systems_dir, series_dir
    )

    # Loading the model library
    with open("src/andromede/libs/pypsa_models/pypsa_models.yml") as lib_file:
        input_libraries = [parse_yaml_library(lib_file)]
    result_lib = resolve_library(input_libraries)

    # Approach 1 : Comparing PyPSA result with Andromede result using the InputSystem directly
    resolved_system_from_pypsa_converter = resolve_system(
        input_system_from_pypsa_converter, result_lib
    )

    # Approcach 2 : Saving the InputSystem to yaml, reading it the yaml and loading the InputSystem
    transform_to_yaml(
        model=input_system_from_pypsa_converter,
        output_path=systems_dir / system_filename,
    )
    with open(systems_dir / system_filename) as system_file:
        input_system_from_yaml = parse_yaml_components(system_file)
    resolved_system_from_yaml = resolve_system(input_system_from_yaml, result_lib)

    # Testing both InputSystem objects
    for resolved_system, input_system in [
        (resolved_system_from_pypsa_converter, input_system_from_pypsa_converter),
        (resolved_system_from_yaml, input_system_from_yaml),
    ]:
        problem = build_problem_from_system(
            resolved_system, input_system, series_dir, T
        )
        status = problem.solver.Solve()
        print(problem.solver.Objective().Value())
        assert status == problem.solver.OPTIMAL
        assert math.isclose(
            problem.solver.Objective().Value(), target_value, rel_tol=1e-6
        )


def convert_pypsa_network(
    pypsa_network: pypsa.Network,
    systems_dir: Path,
    series_dir: Path,
) -> InputSystem:
    logger = Logger(__name__, Path(""))
    converter = PyPSAStudyConverter(pypsa_network, logger, systems_dir, series_dir)
    input_system_from_pypsa_converter = converter.to_andromede_study()

    return input_system_from_pypsa_converter


def build_problem_from_system(
    resolved_system: System, input_system: InputSystem, series_dir: Path, timesteps: int
) -> OptimizationProblem:
    database = build_data_base(input_system, Path(series_dir))
    network = build_network(resolved_system)
    problem = build_problem(
        network,
        database,
        TimeBlock(1, [i for i in range(timesteps)]),
        1,
    )

    return problem
