from pathlib import Path

import pandas as pd
import pytest

from andromede.model.library import Library
from andromede.model.parsing import InputLibrary, parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import BlockBorderManagement, TimeBlock, build_problem
from andromede.simulation.output_values import OutputValues
from andromede.study import TimeScenarioIndex, TimeScenarioSeriesData
from andromede.study.data import DataBase
from andromede.study.parsing import InputComponents, parse_yaml_components
from andromede.study.resolve_components import (
    NetworkComponents,
    build_data_base,
    build_network,
    consistency_check,
    resolve_components_and_cnx,
)


def model_library(name: str) -> Library:
    library = Path(__file__).parent / "lib" / f"{name}.yml"

    with library.open() as lib:
        input_library = parse_yaml_library(lib)
    return resolve_library([input_library])


def input_components(study_name: str) -> InputComponents:
    study_file = Path(__file__).parent / "data" / f"{study_name}.yml"

    with study_file.open() as c:
        return parse_yaml_components(c)


def build_study(study_name: str, lib_name: Library) -> NetworkComponents:
    components_and_cnx = input_components(study_name)
    lib = model_library(lib_name)

    network_components = resolve_components_and_cnx(components_and_cnx, lib)
    consistency_check(network_components.components, lib.models)

    database = build_data_base(components_and_cnx, None)
    network = build_network(network_components)

    return network, database


def test_basic_balance() -> None:
    study, database = build_study("basic_balance_study", "basic_lib")

    scenarios = 1
    time_block = TimeBlock(1, [0])

    problem = build_problem(study, database, time_block, scenarios)
    status = problem.solver.Solve()

    output = OutputValues(problem)

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000

    assert output.component("G").var("generation").value == pytest.approx(100)
    assert output.component("N").var("spillage").value == pytest.approx(0)
    assert output.component("N").var("unsupplied_energy").value == pytest.approx(0)
