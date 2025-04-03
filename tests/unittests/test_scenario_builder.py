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

from pathlib import Path

import pandas as pd
import pytest

from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import TimeBlock, build_problem
from andromede.study import DataBase
from andromede.study.data import ComponentParameterIndex
from andromede.study.parsing import parse_scenario_builder, parse_yaml_components
from andromede.study.resolve_components import (
    build_network,
    build_scenarized_data_base,
    consistency_check,
    resolve_system,
)


@pytest.fixture
def scenario_builder(data_dir: Path) -> pd.DataFrame:
    buider_path = data_dir / "scenario_builder.csv"
    return parse_scenario_builder(buider_path)


@pytest.fixture
def database(data_dir: Path, scenario_builder: pd.DataFrame) -> DataBase:
    components_path = data_dir / "components_for_scenarization_test.yml"
    ts_path = data_dir
    with components_path.open() as components:
        return build_scenarized_data_base(
            parse_yaml_components(components), scenario_builder, ts_path
        )


def test_parser(scenario_builder: pd.DataFrame) -> None:
    builder = pd.DataFrame(
        {
            "name": [
                "load",
                "load",
                "load",
                "load",
                "cost-group",
                "cost-group",
                "cost-group",
                "cost-group",
            ],
            "year": [0, 1, 2, 3, 0, 1, 2, 3],
            "scenario": [0, 1, 0, 1, 0, 0, 1, 1],
        }
    )

    assert builder.equals(scenario_builder)


# cost-group group isnt use in following test because sum can't take time dependant parameters
def test_scenarized_data_base(database: DataBase) -> None:
    load_index = ComponentParameterIndex("D", "demand")
    assert database.get_value(load_index, 0, 0) == 50
    assert database.get_value(load_index, 0, 1) == 100
    assert database.get_value(load_index, 0, 2) == 50
    assert database.get_value(load_index, 0, 3) == 100


def test_solving(data_dir: Path, database: DataBase) -> None:
    library_path = data_dir / "lib.yml"
    with library_path.open("r") as file:
        yaml_lib = parse_yaml_library(file)
        lib_dict = resolve_library([yaml_lib])

    components_path = data_dir / "components_for_scenarization_test.yml"
    with components_path.open("r") as file:
        yaml_comp = parse_yaml_components(file)
        components = resolve_system(yaml_comp, lib_dict)

    consistency_check(components.components, lib_dict["basic"].models)
    network = build_network(components)

    timeblock = TimeBlock(1, list(range(2)))
    problem = build_problem(network, database, timeblock, 3)

    status = problem.solver.Solve()
    cost = problem.solver.Objective().Value()

    assert status == 0
    assert cost == pytest.approx(40000 / 3, abs=0.001)
