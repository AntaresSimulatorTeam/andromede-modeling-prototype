from pathlib import Path

import pytest

from andromede.model.parsing import InputLibrary, parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import TimeBlock, build_problem
from andromede.study import ConstantData, DataBase, Network, Node
from andromede.study.parsing import (
    InputComponent,
    InputComponents,
    parse_yaml_components,
)
from andromede.study.resolve_components import (
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

    result = resolve_components_and_cnx(input_component, input_library)

    assert len(result.components) == 3
    assert len(result.connections) == 2


def test_consistency_check_ok(input_component, input_library):
    result_comp = resolve_components_and_cnx(input_component, input_library)
    result_lib = resolve_library(input_library)
    consistency_check(result_comp.components, result_lib.models)


def test_consistency_check_ko(input_component, input_library):
    result_comp = resolve_components_and_cnx(input_component, input_library)
    result_lib = resolve_library(input_library)
    result_lib.models.pop("generator")
    with pytest.raises(
        ValueError,
        match=r"Error: Component G has invalid model ID: generator",
    ):
        consistency_check(result_comp.components, result_lib.models)


# def test_basic_balance_using_yaml(input_component, input_library) -> None:
#     database = DataBase()
#
#     components_input = resolve_components_and_cnx(input_component, input_library)
#     result_lib = resolve_library(input_library)
#     consistency_check(components_input.components, result_lib.models)
#
#     database.add_data("D", "demand", ConstantData(100))
#
#     database.add_data("G", "p_max", ConstantData(100))
#     database.add_data("G", "cost", ConstantData(30))
#
#     node = Node(model=components_input.components.get("N").model, id="1")
#
#     network = Network("test")
#     network.add_node(node)
#     network.add_component(components_input.components.get("demand"))
#     network.add_component(components_input.components.get("generator"))
#     network.connect(
#         components_input.connections.get("cnx1")[0],
#         components_input.connections.get("cnx1")[1],
#     )
#     network.connect(
#         components_input.connections.get("cnx2")[0],
#         components_input.connections.get("cnx2")[1],
#     )
#
#     scenarios = 1
#     problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
#     status = problem.solver.Solve()
#     assert status == problem.solver.OPTIMAL
#     assert problem.solver.Objective().Value() == 3000
