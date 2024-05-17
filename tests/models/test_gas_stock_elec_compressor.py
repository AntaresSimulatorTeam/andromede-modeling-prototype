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

from andromede.simulation import OutputValues, TimeBlock, build_problem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    create_component,
)


def test_gas_stock_elec_compressor(data_dir: Path, lib: Path, lib_sc: Path):
    """
    Test of a pipeline with stock capacity

    for the following test we have two gaz production and two gaz demands,
    One of each on each sides of a pipeline that has a storage capacity
    gaz_prod_1 and gaz_demand_1 are on the input side of the pipeline
    gaz_prod_2 and gaz_demand_2 are on the output side of the pipeline
    we have the following values:
    gaz production 1:
        - p_max = 200
        - cost = 30
    gaz production 2:
        - p_max = 50
        - cost = 10
    gaz demand 1:
        - demand = 100
    gaz demand 2:
        - demand = 100
    pipeline:
        - f_from_max = 50
        - f_to_max = 50
        - capacity = 100
        - initial_level = 20
    """
    gen_model = lib.models["generator"]
    node_model = lib.models["node"]
    demand_model = lib.models["demand"]
    stock_final_model = lib_sc.models["stock_final_level"]
    convertor_model = lib_sc.models["convertor"]

    gaz_node = Node(model=node_model, id="g")
    elec_node = Node(model=node_model, id="e")
    gaz_prod = create_component(model=gen_model, id="pg")
    elec_prod = create_component(model=gen_model, id="pe")
    gaz_demand = create_component(model=demand_model, id="dg")
    elec_demand = create_component(model=demand_model, id="de")
    gas_stock = create_component(model=stock_final_model, id="sg")
    electrolyzer = create_component(model=convertor_model, id="ez")
    compressor = create_component(model=convertor_model, id="cp")

    database = DataBase()
    database.add_data("dg", "demand", ConstantData(100))
    database.add_data("de", "demand", ConstantData(10))

    database.add_data("pg", "p_max", ConstantData(300))
    database.add_data("pg", "cost", ConstantData(10))
    database.add_data("pe", "p_max", ConstantData(200))
    database.add_data("pe", "cost", ConstantData(10))

    database.add_data("sg", "p_max_in", ConstantData(100))
    database.add_data("sg", "p_max_out", ConstantData(50))
    database.add_data("sg", "capacity", ConstantData(100))
    database.add_data("sg", "initial_level", ConstantData(10))
    database.add_data("sg", "final_level", ConstantData(90))

    database.add_data("ez", "alpha", ConstantData(0.5))

    database.add_data("cp", "alpha", ConstantData(0.7))

    network = Network("test")
    network.add_node(gaz_node)
    network.add_node(elec_node)
    network.add_component(gaz_prod)
    network.add_component(elec_prod)
    network.add_component(gaz_demand)
    network.add_component(elec_demand)
    network.add_component(gas_stock)
    network.add_component(compressor)
    network.add_component(electrolyzer)

    network.connect(
        PortRef(gaz_node, "injection_port"), PortRef(gaz_demand, "injection_port")
    )
    network.connect(PortRef(gaz_node, "injection_port"), PortRef(gas_stock, "flow_s"))
    network.connect(
        PortRef(gaz_node, "injection_port"), PortRef(electrolyzer, "output_port")
    )
    network.connect(
        PortRef(gaz_node, "injection_port"), PortRef(gaz_prod, "injection_port")
    )

    network.connect(PortRef(gas_stock, "flow_c"), PortRef(compressor, "output_port"))

    network.connect(
        PortRef(elec_node, "injection_port"), PortRef(elec_demand, "injection_port")
    )
    network.connect(
        PortRef(elec_prod, "injection_port"), PortRef(elec_node, "injection_port")
    )
    network.connect(
        PortRef(elec_node, "injection_port"), PortRef(electrolyzer, "input_port")
    )
    network.connect(
        PortRef(elec_node, "injection_port"), PortRef(compressor, "input_port")
    )
    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    output = OutputValues(problem)
    r_value = output.component("sg").var("r").value
    generation1 = output.component("pg").var("generation").value
    generation2 = output.component("pe").var("generation").value
    print("generation")
    print(generation1)
    print(generation2)
    print(r_value)
    assert status == problem.solver.OPTIMAL
    assert math.isclose(problem.solver.Objective().Value(), 1100)

    assert math.isclose(r_value, 100)
