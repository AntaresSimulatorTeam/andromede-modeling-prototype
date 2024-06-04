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
    TimeIndex,
    TimeSeriesData,
    create_component,
)


def test_stock_pipeline_as_link(data_dir: Path, lib: Path, lib_sc: Path):
    """
    Test of the stock pipeline without using the stock to see if it work as a simple link

    The pipeline is between two nodes with a gaz production on a node and a demand on the other
    we have the following values:
    gaz production:
        - p_max = 100
        - cost = 10
    gaz demand:
        - demand = 50
    pipeline:
        - f_from_max = 100
        - f_to_max = 100
        - capacity = 0
        - initial_level = 0
    """
    gen_model = lib.models["generator"]
    node_model = lib.models["node"]
    demand_model = lib.models["demand"]
    link_with_storage_model = lib_sc.models["link_with_storage_2"]

    gaz_node_1 = Node(model=node_model, id="g1")
    gaz_node_2 = Node(model=node_model, id="g2")
    gaz_prod = create_component(model=gen_model, id="pg")
    gaz_demand = create_component(model=demand_model, id="dg")
    pipeline = create_component(model=link_with_storage_model, id="pipeline")

    database = DataBase()

    database.add_data("pg", "p_max", ConstantData(100))
    database.add_data("pg", "cost", ConstantData(10))
    database.add_data("dg", "demand", ConstantData(50))
    database.add_data("pipeline", "f_from_max", ConstantData(100))
    database.add_data("pipeline", "f_to_max", ConstantData(100))
    database.add_data("pipeline", "capacity", ConstantData(0))
    database.add_data("pipeline", "initial_level", ConstantData(0))

    network = Network("test")
    network.add_node(gaz_node_1)
    network.add_node(gaz_node_2)
    network.add_component(gaz_prod)
    network.add_component(gaz_demand)
    network.add_component(pipeline)

    network.connect(
        PortRef(gaz_prod, "injection_port"), PortRef(gaz_node_1, "injection_port")
    )
    network.connect(PortRef(gaz_node_1, "injection_port"), PortRef(pipeline, "flow_to"))
    network.connect(
        PortRef(gaz_node_2, "injection_port"), PortRef(gaz_demand, "injection_port")
    )
    network.connect(
        PortRef(gaz_node_2, "injection_port"), PortRef(pipeline, "flow_from")
    )

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    output = OutputValues(problem)
    generation1 = output.component("pg").var("generation").value
    print("generation")
    print(generation1)

    assert status == problem.solver.OPTIMAL
    assert math.isclose(problem.solver.Objective().Value(), 500)


def test_stock_pipeline(data_dir: Path, lib: Path, lib_sc: Path):
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
        - demand = 50
    gaz demand 2:
        - demand = 50
    pipeline:
        - f_from_max = 100
        - f_to_max = 100
        - capacity = 100
        - initial_level = 50
    """

    gen_model = lib.models["generator"]
    node_model = lib.models["node"]
    demand_model = lib.models["demand"]
    link_with_storage_model = lib_sc.models["link_with_storage_2"]

    gaz_node_1 = Node(model=node_model, id="g1")
    gaz_node_2 = Node(model=node_model, id="g2")
    gaz_prod_1 = create_component(model=gen_model, id="prodg1")
    gaz_prod_2 = create_component(model=gen_model, id="prodg2")
    gaz_demand_1 = create_component(model=demand_model, id="demandg1")
    gaz_demand_2 = create_component(model=demand_model, id="demandg2")
    pipeline = create_component(model=link_with_storage_model, id="pipeline")

    database = DataBase()

    database.add_data("prodg1", "p_max", ConstantData(200))
    database.add_data("prodg1", "cost", ConstantData(30))
    database.add_data("prodg2", "p_max", ConstantData(50))
    database.add_data("prodg2", "cost", ConstantData(10))
    database.add_data("demandg1", "demand", ConstantData(100))
    database.add_data("demandg2", "demand", ConstantData(100))
    database.add_data("pipeline", "f_from_max", ConstantData(100))
    database.add_data("pipeline", "f_to_max", ConstantData(100))
    database.add_data("pipeline", "capacity", ConstantData(100))
    database.add_data("pipeline", "initial_level", ConstantData(50))

    network = Network("test")
    network.add_node(gaz_node_1)
    network.add_node(gaz_node_2)
    network.add_component(gaz_prod_1)
    network.add_component(gaz_prod_2)
    network.add_component(gaz_demand_1)
    network.add_component(gaz_demand_2)
    network.add_component(pipeline)

    network.connect(
        PortRef(gaz_prod_1, "injection_port"), PortRef(gaz_node_1, "injection_port")
    )
    network.connect(
        PortRef(gaz_node_1, "injection_port"), PortRef(gaz_demand_1, "injection_port")
    )
    network.connect(
        PortRef(gaz_node_1, "injection_port"), PortRef(pipeline, "flow_from")
    )
    network.connect(
        PortRef(gaz_prod_2, "injection_port"), PortRef(gaz_node_2, "injection_port")
    )
    network.connect(
        PortRef(gaz_node_2, "injection_port"), PortRef(gaz_demand_2, "injection_port")
    )
    network.connect(PortRef(gaz_node_2, "injection_port"), PortRef(pipeline, "flow_to"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert math.isclose(problem.solver.Objective().Value(), 5000)

    output = OutputValues(problem)
    r_value = output.component("pipeline").var("r").value
    generation1 = output.component("prodg1").var("generation").value
    generation2 = output.component("prodg2").var("generation").value
    print("generation")
    print(generation1)
    print(generation2)

    assert math.isclose(r_value, 50)


def test_stock_pipeline_time(data_dir: Path, lib: Path, lib_sc: Path):
    """
    Test of a pipeline for 2 time unit

    The pipeline is between two nodes with a gaz production on a node and a demand on the other
    we have the following values:
        gaz production:
        - p_max = 50
        - cost = 10
    gaz demand:
        - demand = 0 then 100
    pipeline:
        - f_from_max = 100
        - f_to_max = 100
        - capacity = 100
        - initial_level = 50
    """
    gen_model = lib.models["generator"]
    node_model = lib.models["node"]
    demand_model = lib.models["demand"]
    link_with_storage_model = lib_sc.models["link_with_storage_2"]

    gaz_node_1 = Node(model=node_model, id="g1")
    gaz_node_2 = Node(model=node_model, id="g2")
    gaz_prod_1 = create_component(model=gen_model, id="prodg1")
    gaz_demand_2 = create_component(model=demand_model, id="demandg2")
    pipeline = create_component(model=link_with_storage_model, id="pipeline")

    database = DataBase()

    demand_data = TimeSeriesData({TimeIndex(0): 0, TimeIndex(1): 50})

    database.add_data("prodg1", "p_max", ConstantData(50))
    database.add_data("prodg1", "cost", ConstantData(10))
    database.add_data("demandg2", "demand", demand_data)
    database.add_data("pipeline", "f_from_max", ConstantData(100))
    database.add_data("pipeline", "f_to_max", ConstantData(100))
    database.add_data("pipeline", "capacity", ConstantData(100))
    database.add_data("pipeline", "initial_level", ConstantData(50))

    network = Network("test")
    network.add_node(gaz_node_1)
    network.add_node(gaz_node_2)
    network.add_component(gaz_prod_1)
    network.add_component(gaz_demand_2)
    network.add_component(pipeline)

    network.connect(
        PortRef(gaz_prod_1, "injection_port"), PortRef(gaz_node_1, "injection_port")
    )
    network.connect(
        PortRef(gaz_node_1, "injection_port"), PortRef(pipeline, "flow_from")
    )
    network.connect(
        PortRef(gaz_node_2, "injection_port"), PortRef(gaz_demand_2, "injection_port")
    )
    network.connect(PortRef(gaz_node_2, "injection_port"), PortRef(pipeline, "flow_to"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0, 1]), scenarios)
    status = problem.solver.Solve()

    output = OutputValues(problem)
    r_value = output.component("pipeline").var("r").value
    generation1 = output.component("prodg1").var("generation").value
    print("generation")
    print(generation1)
    print(r_value)

    assert status == problem.solver.OPTIMAL
    assert math.isclose(problem.solver.Objective().Value(), 500)
