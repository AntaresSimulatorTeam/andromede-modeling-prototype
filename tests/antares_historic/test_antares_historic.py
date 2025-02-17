import random
from pathlib import Path

import pandas as pd
import pytest

from andromede.input_converter.src.converter import AntaresStudyConverter
from andromede.input_converter.src.logger import Logger
from andromede.model.parsing import InputLibrary, parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import TimeBlock, build_problem
from andromede.study.data import load_ts_from_txt
from andromede.study.parsing import InputStudy, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    consistency_check,
    resolve_components_and_cnx,
)


def create_file(path, filename: str, lines: int, columns: int = 1, value: float = 1):
    Path(path).mkdir(parents=True, exist_ok=True)
    path = path / filename
    data = {f"col_{i+1}": [value for _ in range(lines)] for i in range(columns)}
    df = pd.DataFrame(data)
    df.to_csv(
        path.with_suffix(".txt"),
        sep="\t",
        index=False,
        header=False,
        encoding="utf-8",
    )
    return path


def create_file_with_df(path, filename: str, df: pd.DataFrame = []):
    Path(path).mkdir(parents=True, exist_ok=True)
    path = path / filename
    df.to_csv(
        path.with_suffix(".txt"),
        sep="\t",
        index=False,
        header=False,
        encoding="utf-8",
    )
    return path


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return Path(__file__).parent.parent.parent


def fill_timeseries(study_path):
    load_timeseries = study_path / "input" / "load" / "series"
    demand_data = pd.DataFrame(
        [
            [100],
            [50],
        ],
        index=[0, 1],
        columns=[0],
    )
    create_file_with_df(load_timeseries, "load_fr", demand_data)
    series_path = study_path / "input" / "thermal" / "series" / "fr" / "gaz"
    prepro_path = study_path / "input" / "thermal" / "prepro" / "fr" / "gaz"
    create_file(prepro_path, "modulation", 3, 4)
    create_file(series_path, "series", 3, 1, 151)
    create_file(series_path, "p_min_cluster", 3)
    create_file(series_path, "nb_units_min", 3)
    create_file(series_path, "nb_units_max", 3)


@pytest.fixture
def study_component_basic(local_study_end_to_end_simple) -> InputStudy:
    logger = Logger(__name__, local_study_end_to_end_simple.service.config.study_path)
    study_path = local_study_end_to_end_simple.service.config.study_path
    fill_timeseries(study_path)

    area_fr = local_study_end_to_end_simple.get_areas()["fr"]
    path = study_path / "input" / "load" / "series"
    timeseries = load_ts_from_txt("load_fr", path)
    area_fr.create_load(pd.DataFrame(timeseries))

    converter = AntaresStudyConverter(
        study_input=local_study_end_to_end_simple, logger=logger
    )
    converter.process_all()
    compo_file = converter.output_path

    with compo_file.open() as c:
        return parse_yaml_components(c), study_path


@pytest.fixture
def study_component_thermal(local_study_end_to_end_w_thermal) -> InputStudy:
    logger = Logger(
        __name__, local_study_end_to_end_w_thermal.service.config.study_path
    )
    study_path = local_study_end_to_end_w_thermal.service.config.study_path
    fill_timeseries(study_path)

    area_fr = local_study_end_to_end_w_thermal.get_areas()["fr"]
    path = study_path / "input" / "load" / "series"
    timeseries = load_ts_from_txt("load_fr", path)
    area_fr.create_load(pd.DataFrame(timeseries))

    converter = AntaresStudyConverter(
        study_input=local_study_end_to_end_w_thermal, logger=logger, period=3
    )
    converter.process_all()
    compo_file = converter.output_path

    with compo_file.open() as c:
        return parse_yaml_components(c), study_path


@pytest.fixture
def input_library(
    data_dir: Path,
) -> InputLibrary:
    library = (
        data_dir
        / "src"
        / "andromede"
        / "libs"
        / "antares_historic"
        / "antares_historic.yml"
    )
    with library.open() as lib:
        return parse_yaml_library(lib)


def test_basic_balance_using_yaml(
    study_component_basic: InputStudy,
    input_library: InputLibrary,
) -> None:
    study_path = study_component_basic[1]
    study_component = study_component_basic[0]

    result_lib = resolve_library([input_library])

    components_input = resolve_components_and_cnx(study_component, result_lib)
    consistency_check(components_input.components, result_lib.models)
    database = build_data_base(study_component, study_path)
    network = build_network(components_input)

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0, 1]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 150


def test_thermal_balance_using_yaml(
    study_component_thermal: InputStudy,
    input_library: InputLibrary,
) -> None:
    study_path = study_component_thermal[1]
    study_component = study_component_thermal[0]

    result_lib = resolve_library([input_library])

    components_input = resolve_components_and_cnx(study_component, result_lib)
    consistency_check(components_input.components, result_lib.models)
    database = build_data_base(study_component, study_path)
    network = build_network(components_input)

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0, 1]), scenarios)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 330
