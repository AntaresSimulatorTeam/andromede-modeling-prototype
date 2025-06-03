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
import pytest

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
    run_conversion_test(n1, n1.objective, "test_load_gen.yml", systems_dir, series_dir)


@pytest.mark.parametrize(
    "ratio, sense",
    [(0, "<="), (0.2, "<="), (0.5, "<="), (1.0, "<="), (0.5, "=="), (0.2, "==")],
)
def test_load_gen_emissions(
    systems_dir: Path, series_dir: Path, ratio: float, sense: str
) -> None:
    # Testing PyPSA Generators with CO2 constraints
    T, min_emissions, max_emissions = 10, 10, 20
    n1 = pypsa.Network(name="Demo", snapshots=[i for i in range(T)])
    n1.add("Carrier", "fictive_fuel_one", co2_emissions=min_emissions)
    n1.add("Carrier", "fictive_fuel_two", co2_emissions=max_emissions)
    n1.add("Bus", "pypsatown", v_nom=1)
    load1 = [i * 10 for i in range(T)]
    n1.add("Load", "pypsaload", bus="pypsatown", p_set=load1, q_set=0)
    load2 = [100 for i in range(T)]
    n1.add("Load", "pypsaload2", bus="pypsatown", p_set=load2, qset=0)
    n1.add(
        "Generator",
        "pypsagenerator",
        bus="pypsatown",
        carrier="fictive_fuel_one",
        p_nom_extendable=False,
        marginal_cost=50,  # €/MWh
        p_nom=200,  # MW
    )
    n1.add(
        "Generator",
        "pypsagenerator2",
        bus="pypsatown",
        carrier="fictive_fuel_two",
        p_nom_extendable=False,
        marginal_cost=40,  # €/MWh
        p_nom=200,  # MW
    )
    n1.add(
        "Generator",
        "pypsagenerator3_emissions_free",
        bus="pypsatown",
        p_nom_extendable=False,
        marginal_cost=50,  # €/MWh
        p_nom=10,  # MW
    )
    quota = (ratio * min_emissions + (1 - ratio) * max_emissions) * (
        sum(load1) + sum(load2)
    )
    n1.add("GlobalConstraint", name="co2_budget", sense="<=", constant=quota)
    n1.optimize()
    # Testing the PyPSA_to_Andromede converter
    run_conversion_test(
        n1, n1.objective, "test_load_gen_emissions.yml", systems_dir, series_dir
    )


def test_load_gen_pmin(systems_dir: Path, series_dir: Path) -> None:
    # Testing pmin_pu and pmax_pu parameters for Generator component

    # Building the PyPSA test problem
    T = 10
    n1 = pypsa.Network(name="Demo", snapshots=[i for i in range(T)])
    n1.add("Bus", "pypsatown", v_nom=1)

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
        pmin_pu=0.1,
        pmax_pu=[0.8 + 0.1 * i for i in range(T)],
        p_nom_extendable=False,
        marginal_cost=10,  # €/MWh
        p_nom=50,  # MW
    )
    n1.optimize()

    # Testing the PyPSA_to_Andromede converter
    run_conversion_test(
        n1, n1.objective, "test_load_gen_pmin.yml", systems_dir, series_dir
    )


def test_load_gen_sum(systems_dir: Path, series_dir: Path) -> None:
    # Testing e_sum parameters for Generator component

    # Building the PyPSA test problem
    T = 10
    n1 = pypsa.Network(name="Demo", snapshots=[i for i in range(T)])
    n1.add("Bus", "pypsatown", v_nom=1)

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
        e_sum_max=200,
        p_nom_extendable=False,
        marginal_cost=10,  # €/MWh
        p_nom=50,  # MW
    )
    n1.optimize()

    # Testing the PyPSA_to_Andromede converter
    run_conversion_test(
        n1, n1.objective, "test_load_gen_sum.yml", systems_dir, series_dir
    )


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
        p_max_pu=1,
    )
    n1.optimize()

    # Testing the PyPSA_to_Andromede converter
    run_conversion_test(
        n1, n1.objective, "test_load_gen_link.yml", systems_dir, series_dir
    )


@pytest.mark.parametrize(
    "state_of_charge_initial, standing_loss,efficiency_store,inflow_factor",
    [
        (100.0, 0.01, 0.99, 1),
        (0.0, 0.01, 0.98, 1),
        (0.0, 0.05, 0.9, 1),
        (0.0, 0.05, 0.9, 1000),
    ],
)
def test_storage_unit(
    systems_dir: Path,
    series_dir: Path,
    state_of_charge_initial: float,
    standing_loss: float,
    efficiency_store: float,
    inflow_factor: float,
) -> None:
    # Building the PyPSA test problem with a storage unit
    T = 20
    n1 = pypsa.Network(name="Demo3", snapshots=[i for i in range(T)])
    n1.add("Bus", "pypsatown", v_nom=1)
    n1.add(
        "Load",
        "pypsaload",
        bus="pypsatown",
        p_set=[
            100,
            160,
            100,
            70,
            90,
            30,
            0,
            150,
            200,
            10,
            0,
            0,
            200,
            240,
            0,
            0,
            20,
            50,
            60,
            50,
        ],
        q_set=0,
    )
    n1.add(
        "Generator",
        "pypsagenerator",
        bus="pypsatown",
        p_nom_extendable=False,
        marginal_cost=50,  # €/MWh
        p_nom=150.0,  # MW
    )
    n1.add(
        "StorageUnit",
        "pypsastorage",
        bus="pypsatown",
        p_nom=100,  # MW
        max_hours=10,  # Hours of storage at full output
        efficiency_store=efficiency_store,
        efficiency_dispatch=0.85,
        standing_loss=standing_loss,
        state_of_charge_initial=state_of_charge_initial,
        marginal_cost=10.0,  # €/MWh
        marginal_cost_storage=1.5,  # €/MWh
        spill_cost=100.0,  # €/MWh
        p_min_pu=-1,
        p_max_pu=1,
        inflow=[i * inflow_factor for i in range(T)],
        cyclic_state_of_charge=True,
        cyclic_state_of_charge_per_period=True,
    )
    n1.optimize()

    # Testing the PyPSA_to_Andromede converter
    run_conversion_test(
        n1, n1.objective, "test_storage_unit.yml", systems_dir, series_dir
    )


@pytest.mark.parametrize(
    "e_initial, standing_loss",
    [
        (50.0, 0.1),
        (0.0, 0.01),
        (0.0, 0.05),
    ],
)
def test_store(
    systems_dir: Path, series_dir: Path, e_initial: float, standing_loss: float
) -> None:
    # Building the PyPSA test problem with a store
    T = 20

    n1 = pypsa.Network(name="StoreDemo", snapshots=[i for i in range(T)])
    n1.add("Bus", "pypsatown", v_nom=1)
    n1.add(
        "Load",
        "pypsaload",
        bus="pypsatown",
        p_set=[
            100,
            160,
            100,
            70,
            90,
            30,
            0,
            150,
            200,
            10,
            0,
            0,
            200,
            240,
            0,
            0,
            20,
            50,
            60,
            50,
        ],
        q_set=0,
    )
    n1.add(
        "Generator",
        "pypsagenerator",
        bus="pypsatown",
        p_nom_extendable=False,
        marginal_cost=50,  # €/MWh
        p_nom=150.0,  # MW
    )
    n1.add(
        "Store",
        "pypsastore",
        bus="pypsatown",
        e_nom=200,  # MWh
        e_initial=e_initial,
        standing_loss=standing_loss,  # 1% loss per hour
        marginal_cost=10.0,  # €/MWh
        marginal_cost_storage=1.5,  # €/MWh
        e_cyclic=True,
    )
    n1.optimize()

    # Testing the PyPSA_to_Andromede converter
    run_conversion_test(n1, n1.objective, "test_store.yml", systems_dir, series_dir)


def run_conversion_test(
    pypsa_network: pypsa.Network,
    target_value: float,
    system_filename: str,
    systems_dir: Path,
    series_dir: Path,
) -> None:
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
    logger = Logger(__name__, "")
    converter = PyPSAStudyConverter(pypsa_network, logger, systems_dir, series_dir)
    input_system_from_pypsa_converter = converter.to_andromede_study()

    return input_system_from_pypsa_converter


def build_problem_from_system(
    resolved_system: System, input_system: InputSystem, series_dir: Path, timesteps: int
) -> OptimizationProblem:
    database = build_data_base(input_system, series_dir)
    network = build_network(resolved_system)
    problem = build_problem(
        network,
        database,
        TimeBlock(1, [i for i in range(timesteps)]),
        1,
    )

    return problem
