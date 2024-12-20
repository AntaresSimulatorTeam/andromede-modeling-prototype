from pathlib import Path

import pandas as pd
import pytest

from andromede.model.parsing import InputLibrary, parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import BlockBorderManagement, TimeBlock, build_problem
from andromede.study import TimeScenarioIndex, TimeScenarioSeriesData
from andromede.study.parsing import InputStudy, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    consistency_check,
    resolve_components_and_cnx,
)


@pytest.fixture
def input_component(
    data_dir: Path,
) -> InputStudy:
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
    input_component: InputStudy, input_library: InputLibrary
) -> None:
    assert len(input_component.components) == 2
    assert len(input_component.nodes) == 1
    assert len(input_component.connections) == 2
    lib = resolve_library([input_library])
    result = resolve_components_and_cnx(input_component, lib)

    assert len(result.components) == 2
    assert len(result.nodes) == 1
    assert len(result.connections) == 2


def test_consistency_check_ok(
    input_component: InputStudy, input_library: InputLibrary
) -> None:
    result_lib = resolve_library([input_library])
    result_comp = resolve_components_and_cnx(input_component, result_lib)
    consistency_check(result_comp.components, result_lib.models)


def test_consistency_check_ko(
    input_component: InputStudy, input_library: InputLibrary
) -> None:
    result_lib = resolve_library([input_library])
    result_comp = resolve_components_and_cnx(input_component, result_lib)
    result_lib.models.pop("generator")
    with pytest.raises(
        ValueError,
        match=r"Error: Component G has invalid model ID: generator",
    ):
        consistency_check(result_comp.components, result_lib.models)


def test_basic_balance_using_yaml(
    input_component: InputStudy, input_library: InputLibrary
) -> None:
    result_lib = resolve_library([input_library])
    components_input = resolve_components_and_cnx(input_component, result_lib)
    consistency_check(components_input.components, result_lib.models)

    database = build_data_base(input_component, None)
    network = build_network(components_input)

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000


def generate_data_for_short_term_storage_test(scenarios: int) -> TimeScenarioSeriesData:
    data = {}
    horizon = 10
    efficiency = 0.8
    for scenario in range(scenarios):
        for absolute_timestep in range(10):
            if absolute_timestep == 0:
                data[TimeScenarioIndex(absolute_timestep, scenario)] = -18.0
            else:
                data[TimeScenarioIndex(absolute_timestep, scenario)] = 2 * efficiency

    values = [value for value in data.values()]
    data_df = pd.DataFrame(values, columns=["Value"])
    return TimeScenarioSeriesData(data_df)


def test_short_term_storage_base_with_yaml(data_dir: Path) -> None:
    compo_file = data_dir / "components_for_short_term_storage.yml"
    lib_file = data_dir / "lib.yml"
    with lib_file.open() as lib:
        input_library = parse_yaml_library(lib)

    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    library = resolve_library([input_library])
    components_input = resolve_components_and_cnx(components_file, library)
    # 18 produced in the 1st time-step, then consumed 2 * efficiency in the rest
    scenarios = 1
    horizon = 10
    time_blocks = [TimeBlock(0, list(range(horizon)))]

    database = build_data_base(components_file, data_dir)
    network = build_network(components_input)

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
