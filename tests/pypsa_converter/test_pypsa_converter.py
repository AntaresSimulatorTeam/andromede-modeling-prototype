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
import pypsa
import pytest


from andromede.input_converter.src.pypsa_converter import PyPSAStudyConverter

from andromede.input_converter.src.logger import Logger
from andromede.input_converter.src.utils import transform_to_yaml
from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation.optimization import build_problem
from andromede.simulation.time_block import TimeBlock
from andromede.study.parsing import (
    parse_yaml_components,
)
from andromede.study.resolve_components import (
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
    conversion_testing(n1, n1.objective, "test1.yml", systems_dir, series_dir)


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
        efficiency = 0.9,
        marginal_cost = 0.5,
        p_nom=50,
        p_min_pu=-1,
        p_max_pu=[i / T for i in range(T)],
    )
    n1.optimize()

    # Testing the PyPSA_to_Andromede converter
    conversion_testing(n1, n1.objective, "test2.yml", systems_dir, series_dir)


def conversion_testing(
    pypsa_network: pypsa.Network,
    target_value: float,
    filename: str,
    systems_dir: Path,
    series_dir: Path,
):
    # Conversion to Andromede System
    logger = Logger(__name__, Path(""))
    converter = PyPSAStudyConverter(pypsa_network, logger, systems_dir, series_dir)
    T = len(pypsa_network.timesteps)
    input_component = converter.to_andromede_study()

    # Comparing PyPSA result with Andromede result - direct approach using the input_component object
    with open("src/andromede/libs/pypsa_models/pypsa_models.yml") as lib_file:
        input_libraries = [parse_yaml_library(lib_file)]
    result_lib = resolve_library(input_libraries)
    resolved_system = resolve_system(input_component, result_lib)
    database = build_data_base(input_component, Path(series_dir))
    network = build_network(resolved_system)
    problem = build_problem(
        network,
        database,
        TimeBlock(1, [i for i in range(T)]),
        1,
    )
    status = problem.solver.Solve()
    print(problem.solver.Objective().Value())
    assert status == problem.solver.OPTIMAL
    assert math.isclose(problem.solver.Objective().Value(), target_value, rel_tol=1e-6)

    # Test through saving to yaml, and then reading the yaml
    transform_to_yaml(model=input_component, output_path=systems_dir / filename)

    with open(systems_dir / filename) as compo_file:
        input_component2 = parse_yaml_components(compo_file)
    resolved_system2 = resolve_system(input_component2, result_lib)
    database2 = build_data_base(input_component2, Path(series_dir))
    network2 = build_network(resolved_system2)
    problem2 = build_problem(
        network2,
        database2,
        TimeBlock(1, [i for i in range(T)]),
        1,
    )

    status2 = problem2.solver.Solve()
    print(problem2.solver.Objective().Value())
    assert status2 == problem2.solver.OPTIMAL
    assert math.isclose(problem2.solver.Objective().Value(), target_value, rel_tol=1e-6)
