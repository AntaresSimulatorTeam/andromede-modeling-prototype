from pathlib import Path

import pytest

from andromede.model.parsing import InputLibrary, parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import TimeBlock, build_problem
from andromede.study import Node, TimeIndex, TimeScenarioIndex
from andromede.study.parsing import InputComponents, parse_yaml_components
from andromede.study.resolve_components import (
    _evaluate_time_series,
    build_data_base,
    build_network,
    consistency_check,
    resolve_components_and_cnx,
)


@pytest.fixture
def input_component(
    data_dir: Path,
) -> InputComponents:
    compo_file = data_dir / "components.yml"

    with compo_file.open() as c:
        return parse_yaml_components(c)


@pytest.fixture
def input_library(
    data_dir: Path,
) -> InputLibrary:
    library = data_dir / "lib.yml"

    with library.open() as lib:
        return parse_yaml_library(lib)


def test_parsing_components_ok(input_component, input_library):
    assert len(input_component.components) == 2
    assert len(input_component.nodes) == 1
    assert len(input_component.connections) == 2
    lib = resolve_library(input_library)
    result = resolve_components_and_cnx(input_component, lib)

    assert len(result.components) == 2
    assert len(result.nodes) == 1
    assert len(result.connections) == 2


def test_consistency_check_ok(input_component, input_library):
    result_lib = resolve_library(input_library)
    result_comp = resolve_components_and_cnx(input_component, result_lib)
    consistency_check(result_comp.components, result_lib.models)


def test_consistency_check_ko(input_component, input_library):
    result_lib = resolve_library(input_library)
    result_comp = resolve_components_and_cnx(input_component, result_lib)
    result_lib.models.pop("generator")
    with pytest.raises(
        ValueError,
        match=r"Error: Component G has invalid model ID: generator",
    ):
        consistency_check(result_comp.components, result_lib.models)


def test_basic_balance_using_yaml(input_component, input_library) -> None:
    result_lib = resolve_library(input_library)
    components_input = resolve_components_and_cnx(input_component, result_lib)
    consistency_check(components_input.components, result_lib.models)

    database = build_data_base(input_component)
    network = build_network(components_input)

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000


def test_evaluate_time_series(data_dir: Path):
    txt_file = data_dir / "gen-costs.txt"

    gen_costs = _evaluate_time_series(str(txt_file))
    expected_timeseries = {
        TimeScenarioIndex(0, 0): 100,
        TimeScenarioIndex(0, 1): 50,
        TimeScenarioIndex(1, 0): 200,
        TimeScenarioIndex(1, 1): 100,
    }
    assert gen_costs == expected_timeseries
