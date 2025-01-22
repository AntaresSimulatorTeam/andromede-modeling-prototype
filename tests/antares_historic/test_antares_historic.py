from pathlib import Path

import pandas as pd
import pytest

from andromede.model.parsing import InputLibrary, parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import TimeBlock, build_problem
from andromede.input_converter.src.logger import Logger
from andromede.input_converter.src.converter import AntaresStudyConverter
from andromede.study.parsing import InputStudy, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    consistency_check,
    resolve_components_and_cnx,
)


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return Path(__file__).parent.parent.parent

@pytest.fixture
def study_component(local_study_with_constraint
) -> InputStudy:
    logger = Logger(__name__, local_study_with_constraint.service.config.study_path)
    converter = AntaresStudyConverter(study_input=local_study_with_constraint, logger=logger)
    converter.process_all()
    compo_file = converter.output_path

    with compo_file.open() as c:
        return parse_yaml_components(c)


@pytest.fixture
def input_library(
    data_dir: Path,
) -> InputLibrary:
    library = data_dir / "src" / "andromede" / "libs" /  "antares_historic" / "antares_historic.yml"
    with library.open() as lib:
        return parse_yaml_library(lib)

@pytest.skip("Missing max operator in modeleur to read thermal model")
def test_basic_balance_using_yaml(
   study_component: InputStudy, input_library: InputLibrary
) -> None:

    result_lib = resolve_library([input_library])

    components_input = resolve_components_and_cnx(study_component, result_lib)
    consistency_check(components_input.components, result_lib.models)

    database = build_data_base(study_component, None)
    network = build_network(components_input)

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000
