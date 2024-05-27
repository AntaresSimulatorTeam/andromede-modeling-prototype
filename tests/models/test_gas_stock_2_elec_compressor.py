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
    lib_sc_file = libs_path / "models_for_test_gas_stock_2_elec_compressor.yml"

    with lib_sc_file.open() as f:
        input_lib_sc = parse_yaml_library(f)

    lib_sc = resolve_library(input_lib_sc)
    return lib_sc


def test_gas_stock_2_elec_compressor(data_dir: Path, lib_models: Path):
    """
    Test of a gas stock and a repartition compressor in a system with multiple set of electricity production and demand

    for the following test we have two electrical node, each connected to a demand, a production, an electrolyzer and a compressor
    each compressor are connected to a unique gas stock witch is connected to a gas node with a demand and a production
    each electrolyzer are also connected to the gas node
    each compressor are also connected to a unique repartition compressor

    we have the following values:
    gaz production:
        - p_max = 10
        - cost = 10
    elec production 1:
        - p_max = 100
        - cost = 10
    elec production 2:
        - p_max = 100
        - cost = 10
    gaz demand:
        - demand = 10
    elec demand 1:
        - demand = 50
    elec demand 2:
        - demand = 100
    gas stock:
        - p_max_in = 100
        - p_max_out = 50
        - capacity = 100
        - initial_level = 10
        - final_level = 90
    electrolyzer 1:
        - alpha 0.5
    electrolyzer 2:
        - alpha 0.5
    compressor 1:
        - alpha 0.5
    compressor 2:
        - alpha 0.5
    """
    components_path = Path(__file__)
    compo_file = (
        components_path.parent / "components_for_test_gas_stock_2_elec_compressor.yml"
    )
    input_component = parse_yaml_components(compo_file.open())

    components_input = resolve_components_and_cnx(input_component, lib_models)
    consistency_check(components_input.components, lib_models.models)

    database = build_data_base(input_component, None)
    network = build_network(components_input)

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    output = OutputValues(problem)
    r_value = output.component("GS").var("r").value
    generation1 = output.component("PE1").var("generation").value
    generation2 = output.component("PE2").var("generation").value
    generation3 = output.component("PG").var("generation").value
    print("generation")
    print(generation1)
    print(generation2)
    print(generation3)
    print(r_value)
    assert status == problem.solver.OPTIMAL
    assert math.isclose(problem.solver.Objective().Value(), 1600)
