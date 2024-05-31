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

import pytest

from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library
from andromede.simulation import OutputValues, TimeBlock, build_problem
from andromede.study.parsing import InputComponents, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    consistency_check,
    resolve_components_and_cnx,
)


@pytest.fixture(scope="session")
def lib_models():
    libs_path = Path(__file__).parent
    lib_sc_file = libs_path / "models_for_test_stock_hydro_2_input.yml"

    with lib_sc_file.open() as f:
        input_lib_sc = parse_yaml_library(f)

    lib_sc = resolve_library(input_lib_sc)
    return lib_sc


def test_stock_hydro_2_input(data_dir: Path, lib_models: Path):
    """
    Test of a hydro stock connected to 2 nodes with a electrical production and demand each
    """
    components_path = Path(__file__)
    compo_file = components_path.parent / "components_for_test_stock_hydro_2_input.yml"
    input_component = parse_yaml_components(compo_file.open())

    components_input = resolve_components_and_cnx(input_component, lib_models)
    consistency_check(components_input.components, lib_models.models)

    database = build_data_base(input_component, None)
    network = build_network(components_input)

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    output = OutputValues(problem)
    r_value = output.component("HS").var("r").value
    generation1 = output.component("PE1").var("generation").value
    generation2 = output.component("PE2").var("generation").value
    print("generation")
    print(generation1)
    print(generation2)
    print(r_value)
    assert status == problem.solver.OPTIMAL
    assert math.isclose(problem.solver.Objective().Value(), 1500)
