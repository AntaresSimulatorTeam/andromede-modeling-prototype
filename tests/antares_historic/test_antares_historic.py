from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest

from andromede.input_converter.src.converter import AntaresStudyConverter
from andromede.input_converter.src.logger import Logger
from andromede.model.parsing import InputLibrary, parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import TimeBlock, build_problem
from andromede.simulation.optimization import OptimizationProblem
from andromede.study.data import load_ts_from_txt
from andromede.study.parsing import InputStudy, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    consistency_check,
    resolve_components_and_cnx,
)


@dataclass(frozen=True)
class ToolTestStudy:
    study_component_data: InputStudy
    study_path: Path


def create_csv_from_constant_value(
    path, filename: str, lines: int, columns: int = 1, value: float = 1
) -> None:
    """
    Creates a file with generated data.

    Args:
        path (Path): Path to the directory where the file will be created.
        filename (str): Name of the file to be created.
        lines (int): Number of lines in the file.
        columns (int): Number of columns in the file.
        value (float): Value to fill in the columns.

    Returns:
        Path: Path to the created file.
    """
    # Create the directory if it does not exist
    Path(path).mkdir(parents=True, exist_ok=True)
    path = path / filename

    # Generate the data
    data = {f"col_{i+1}": [value] * lines for i in range(columns)}
    df = pd.DataFrame(data)

    # Write the data to a file
    df.to_csv(
        path.with_suffix(".txt"),
        sep="\t",
        index=False,
        header=False,
        encoding="utf-8",
    )


def write_df_to_csv(path, filename: str, df: pd.DataFrame) -> None:
    """
    Creates a file from an existing DataFrame.

    Args:
        path (Path): Path to the directory where the file will be created.
        filename (str): Name of the file to be created.
        df (pd.DataFrame): DataFrame containing the data to be written.

    Returns:
        Path: Path to the created file.
    """
    # Create the directory if it does not exist
    Path(path).mkdir(parents=True, exist_ok=True)
    path = path / filename

    # Write the data to a file
    df.to_csv(
        path.with_suffix(".txt"),
        sep="\t",
        index=False,
        header=False,
        encoding="utf-8",
    )


@pytest.fixture(scope="session")
def data_dir() -> Path:
    """
    Pytest fixture to get the path to the data directory.

    Returns:
        Path: Path to the data directory.
    """
    return Path(__file__).parent.parent.parent


def fill_timeseries(study_path) -> None:
    """
    Fills the time series with generated data.

    Args:
        study_path (Path): Path to the study directory.
    """
    # Paths to directories and files
    load_timeseries = study_path / "input" / "load" / "series"
    series_path = study_path / "input" / "thermal" / "series" / "fr" / "gaz"
    prepro_path = study_path / "input" / "thermal" / "prepro" / "fr" / "gaz"

    # Demand data
    demand_data = pd.DataFrame(
        [
            [100],
            [50],
        ],
        index=[0, 1],
        columns=[0],
    )

    # Create the files with the data
    write_df_to_csv(path=load_timeseries, filename="load_fr", df=demand_data)
    create_csv_from_constant_value(
        path=prepro_path, filename="modulation", lines=3, columns=4, value=0
    )
    create_csv_from_constant_value(
        path=series_path, filename="series", lines=3, columns=1, value=151
    )
    create_csv_from_constant_value(path=series_path, filename="p_min_cluster", lines=3)
    create_csv_from_constant_value(path=series_path, filename="nb_units_min", lines=3)
    create_csv_from_constant_value(path=series_path, filename="nb_units_max", lines=3)


def _setup_study_component(study, period=None) -> ToolTestStudy:
    """
    Helper function to reduce redundancy in study component setup.
    """
    logger = Logger(__name__, study.service.config.study_path)
    study_path = study.service.config.study_path
    fill_timeseries(study_path)

    area_fr = study.get_areas()["fr"]
    path = study_path / "input" / "load" / "series"
    timeseries = load_ts_from_txt("load_fr", path)
    area_fr.set_load(pd.DataFrame(timeseries))

    converter = AntaresStudyConverter(study_input=study, logger=logger, period=period)
    converter.process_all()

    compo_file = converter.output_path
    with compo_file.open() as c:
        return ToolTestStudy(parse_yaml_components(c), study_path)


@pytest.fixture
def study_component_basic(local_study_end_to_end_simple) -> ToolTestStudy:
    return _setup_study_component(local_study_end_to_end_simple)


@pytest.fixture
def study_component_thermal(local_study_end_to_end_w_thermal) -> ToolTestStudy:
    return _setup_study_component(local_study_end_to_end_w_thermal, period=3)


@pytest.fixture
def study_component_st_storage(local_study_with_st_storage) -> ToolTestStudy:
    return _setup_study_component(local_study_with_st_storage, period=3)


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


def problem_builder(
    study_test_component: ToolTestStudy, input_library: InputLibrary
) -> OptimizationProblem:
    """
    - Resolves the input library.
    - Constructs components and connections.
    - Performs consistency checks.
    - Builds the database and network.
    - Solves the optimization problem and verifies results.
    """
    study_path = study_test_component.study_path
    study_component_data = study_test_component.study_component_data

    result_lib = resolve_library([input_library])
    components_input = resolve_components_and_cnx(study_component_data, result_lib)
    consistency_check(components_input.components, result_lib.models)

    database = build_data_base(study_component_data, study_path)
    network = build_network(components_input)

    scenarios = 1
    return build_problem(network, database, TimeBlock(1, [0, 1]), scenarios)


def test_basic_balance_using_converter(
    study_component_basic: InputStudy, input_library: InputLibrary
) -> None:
    """
    Test basic study balance using the converter.
    """
    problem = problem_builder(study_component_basic, input_library)
    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 150


def test_thermal_balance_using_converter(
    study_component_thermal: InputStudy, input_library: InputLibrary
) -> None:
    """
    Test thermal study balance using the converter.
    """
    problem = problem_builder(study_component_thermal, input_library)

    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 165


@pytest.mark.skip(reason="Test temporarily deactivated")
def test_storage_balance_using_converter(
    study_component_st_storage: InputStudy, input_library: InputLibrary
) -> None:
    """
    Test storage study balance using the converter.
    """
    # Wait for new version 0.92 of antares craft  which include efficiencywithdrawalparameter
    problem = problem_builder(study_component_st_storage, input_library)

    status = problem.solver.Solve()
    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 165
