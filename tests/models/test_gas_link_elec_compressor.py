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


def test_gas_link_elec_compressor(data_dir: Path, lib: Path, lib_sc: Path):
    """
    Test of a pipeline with stock capacity

    for the following test we have two gaz production and two gaz demands,
    One of each on each sides of a pipeline that has a storage capacity
    gaz_prod_1 and gaz_demand_1 are on the input side of the pipeline
    gaz_prod_2 and gaz_demand_2 are on the output side of the pipeline
    we have the following values:
    electricity production:
        - p_max = 200
        - cost = 10
    gaz production:
        - p_max = 300
        - cost = 10
    gaz demand:
        - demand = 100
    electricity demand:
        - demand = 10
    pipeline:
        - f_from_max = 100
        - f_to_max = 50
        - capacity = 100
        - initial_level = 20
    electrolyzer:
        - alpha = 0.5
    compressor from:
        - alpha = 0.7
    compressor to:
        - alpha = 0.7
    """
    gen_model = lib.models["generator"]
    node_model = lib.models["node"]
    demand_model = lib.models["demand"]
    link_with_storage_model = lib_sc.models["link_with_storage"]
    convertor_model = lib_sc.models["convertor"]

    gaz_node_1 = Node(model=node_model, id="g1")
    gaz_node_2 = Node(model=node_model, id="g2")
    elec_node = Node(model=node_model, id="e")
    gaz_prod = create_component(model=gen_model, id="pg")
    elec_prod = create_component(model=gen_model, id="pe")
    gaz_demand = create_component(model=demand_model, id="dg")
    elec_demand = create_component(model=demand_model, id="de")
    pipeline = create_component(model=link_with_storage_model, id="pp")
    electrolyzer = create_component(model=convertor_model, id="ez")
    compressor_from = create_component(model=convertor_model, id="cpf")
    compressor_to = create_component(model=convertor_model, id="cpt")

    database = DataBase()
    database.add_data("dg", "demand", ConstantData(100))
    database.add_data("de", "demand", ConstantData(10))

    database.add_data("pg", "p_max", ConstantData(300))
    database.add_data("pg", "cost", ConstantData(10))
    database.add_data("pe", "p_max", ConstantData(200))
    database.add_data("pe", "cost", ConstantData(10))

    database.add_data("pp", "f_from_max", ConstantData(100))
    database.add_data("pp", "f_to_max", ConstantData(50))
    database.add_data("pp", "capacity", ConstantData(100))
    database.add_data("pp", "initial_level", ConstantData(20))

    database.add_data("ez", "alpha", ConstantData(0.5))

    database.add_data("cpf", "alpha", ConstantData(0.7))
    database.add_data("cpt", "alpha", ConstantData(0.7))

    network = Network("test")
    network.add_node(gaz_node_1)
    network.add_node(gaz_node_2)
    network.add_node(elec_node)
    network.add_component(gaz_prod)
    network.add_component(elec_prod)
    network.add_component(gaz_demand)
    network.add_component(elec_demand)
    network.add_component(pipeline)
    network.add_component(compressor_from)
    network.add_component(compressor_to)
    network.add_component(electrolyzer)

    network.connect(
        PortRef(gaz_node_2, "injection_port"), PortRef(gaz_prod, "injection_port")
    )
    network.connect(PortRef(gaz_node_2, "injection_port"), PortRef(pipeline, "flow_to"))
    network.connect(PortRef(gaz_node_2, "injection_port"), PortRef(pipeline, "flow_to"))

    network.connect(
        PortRef(gaz_node_1, "injection_port"), PortRef(gaz_demand, "injection_port")
    )
    network.connect(
        PortRef(gaz_node_1, "injection_port"), PortRef(pipeline, "flow_from")
    )
    network.connect(
        PortRef(gaz_node_1, "injection_port"), PortRef(electrolyzer, "output_port")
    )

    network.connect(
        PortRef(pipeline, "flow_from_pos"), PortRef(compressor_from, "output_port")
    )
    network.connect(
        PortRef(pipeline, "flow_to_pos"), PortRef(compressor_to, "output_port")
    )

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
        PortRef(elec_node, "injection_port"), PortRef(compressor_from, "input_port")
    )
    network.connect(
        PortRef(elec_node, "injection_port"), PortRef(compressor_to, "input_port")
    )

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    output = OutputValues(problem)
    r_value = output.component("pp").var("r").value
    generation1 = output.component("pg").var("generation").value
    generation2 = output.component("pe").var("generation").value
    print("generation")
    print(generation1)
    print(generation2)
    r = output.component("pp").var("r")
    print(r)
    assert status == problem.solver.OPTIMAL
    assert math.isclose(problem.solver.Objective().Value(), 2100)

    assert math.isclose(r_value, 20)
