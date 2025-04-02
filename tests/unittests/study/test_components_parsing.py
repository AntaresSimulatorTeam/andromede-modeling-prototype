from pathlib import Path
from typing import Callable, Tuple

import pytest

from andromede.model.parsing import InputLibrary, parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import BlockBorderManagement, TimeBlock, build_problem
from andromede.study.data import DataBase
from andromede.study.network import Network
from andromede.study.parsing import InputSystem, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    consistency_check,
    resolve_system,
)


@pytest.fixture
def input_system(
    data_dir: Path,
) -> InputSystem:
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


def test_parsing_components_ok(
    input_system: InputSystem, input_library: InputLibrary
) -> None:
    assert len(input_system.components) == 2
    assert len(input_system.nodes) == 1
    assert len(input_system.connections) == 2
    lib_dict = resolve_library([input_library])
    result = resolve_system(input_system, lib_dict)

    assert len(result.components) == 2
    assert len(result.nodes) == 1
    assert len(result.connections) == 2


def test_consistency_check_ok(
    input_system: InputSystem, input_library: InputLibrary
) -> None:
    result_lib = resolve_library([input_library])
    result_system = resolve_system(input_system, result_lib)
    consistency_check(result_system.components, result_lib["basic"].models)


def test_consistency_check_ko(
    input_system: InputSystem, input_library: InputLibrary
) -> None:
    result_lib = resolve_library([input_library])
    result_comp = resolve_system(input_system, result_lib)
    result_lib["basic"].models.pop("generator")
    with pytest.raises(
        ValueError,
        match=r"Error: Component G has invalid model ID: generator",
    ):
        consistency_check(result_comp.components, result_lib["basic"].models)


def test_basic_balance_using_yaml(
    input_system: InputSystem, input_library: InputLibrary
) -> None:
    result_lib = resolve_library([input_library])
    components_input = resolve_system(input_system, result_lib)
    consistency_check(components_input.components, result_lib["basic"].models)

    database = build_data_base(input_system, None)
    network = build_network(components_input)

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000


@pytest.fixture
def setup_test(data_dir: Path) -> Callable[[], Tuple[Network, DataBase]]:
    def _setup_test(study_file_name: str):
        study_file = data_dir / study_file_name
        lib_file = data_dir / "lib.yml"
        with lib_file.open() as lib:
            input_library = parse_yaml_library(lib)

        with study_file.open() as c:
            input_study = parse_yaml_components(c)
        lib_dict = resolve_library([input_library])
        network_components = resolve_system(input_study, lib_dict)
        consistency_check(network_components.components, lib_dict["basic"].models)

        database = build_data_base(input_study, data_dir)
        network = build_network(network_components)
        return network, database

    return _setup_test


def test_basic_balance_time_only_series(
    setup_test: Callable[[], Tuple[Network, DataBase]],
) -> None:
    network, database = setup_test("study_time_only_series.yml")
    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0, 1]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 10000


def test_basic_balance_scenario_only_series(
    setup_test: Callable[[], Tuple[Network, DataBase]],
) -> None:
    network, database = setup_test("study_scenario_only_series.yml")
    scenarios = 2
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 0.5 * 5000 + 0.5 * 10000


def test_short_term_storage_base_with_yaml(
    setup_test: Callable[[], Tuple[Network, DataBase]],
) -> None:
    network, database = setup_test("components_for_short_term_storage.yml")
    # 18 produced in the 1st time-step, then consumed 2 * efficiency in the rest
    scenarios = 1
    horizon = 10
    time_blocks = [TimeBlock(0, list(range(horizon)))]

    problem = build_problem(
        network,
        database,
        time_blocks[0],
        scenarios,
        border_management=BlockBorderManagement.CYCLE,
    )
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL

    # The short-term storage should satisfy the load
    # No spillage / unsupplied energy is expected
    assert problem.solver.Objective().Value() == 0

    count_variables = 0
    for variable in problem.solver.variables():
        if "injection" in variable.name():
            count_variables += 1
            assert 0 <= variable.solution_value() <= 100
        elif "withdrawal" in variable.name():
            count_variables += 1
            assert 0 <= variable.solution_value() <= 50
        elif "level" in variable.name():
            count_variables += 1
            assert 0 <= variable.solution_value() <= 1000
    assert count_variables == 3 * horizon
