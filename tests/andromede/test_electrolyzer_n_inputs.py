from andromede.expression import literal, param, var
from andromede.expression.expression import port_field
from andromede.libs.standard_sc import (
    CONVERTOR_MODEL,
    CONVERTOR_MODEL_MOD,
    DECOMPOSE_1_FLOW_INTO_2_FLOW,
    DEMAND_MODEL,
    FLOW_PORT,
    NODE_MODEL,
    PROD_MODEL,
    TWO_INPUTS_CONVERTOR_MODEL,
)
from andromede.model import (
    Constraint,
    ModelPort,
    PortField,
    PortType,
    float_parameter,
    float_variable,
    model,
)
from andromede.model.model import PortFieldDefinition, PortFieldId
from andromede.simulation import TimeBlock, build_problem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    create_component,
)


def test_electrolyzer_n_inputs_1():
    elec_node_1 = Node(model=NODE_MODEL, id="e1")
    electric_prod_1 = create_component(model=PROD_MODEL, id="ep1")
    electrolyzer1 = create_component(model=CONVERTOR_MODEL, id="ez1")

    elec_node_2 = Node(model=NODE_MODEL, id="e2")
    electric_prod_2 = create_component(model=PROD_MODEL, id="ep2")
    electrolyzer2 = create_component(model=CONVERTOR_MODEL, id="ez2")

    gaz_node = Node(model=NODE_MODEL, id="g")
    gaz_prod = create_component(model=PROD_MODEL, id="gp")
    gaz_demand = create_component(model=DEMAND_MODEL, id="gd")

    database = DataBase()

    database.add_data("ep1", "p_max", ConstantData(100))
    database.add_data("ep1", "cost", ConstantData(30))
    database.add_data("ez1", "alpha", ConstantData(0.7))

    database.add_data("ep2", "p_max", ConstantData(100))
    database.add_data("ep2", "cost", ConstantData(30))
    database.add_data("ez2", "alpha", ConstantData(0.7))

    database.add_data("gd", "demand", ConstantData(70))
    database.add_data("gp", "p_max", ConstantData(10))
    database.add_data("gp", "cost", ConstantData(40))

    network = Network("test")
    network.add_node(elec_node_1)
    network.add_component(electric_prod_1)
    network.add_component(electrolyzer1)
    network.add_node(elec_node_2)
    network.add_component(electric_prod_2)
    network.add_component(electrolyzer2)
    network.add_node(gaz_node)
    network.add_component(gaz_prod)
    network.add_component(gaz_demand)

    network.connect(PortRef(electric_prod_1, "FlowP"), PortRef(elec_node_1, "FlowN"))
    network.connect(PortRef(elec_node_1, "FlowN"), PortRef(electrolyzer1, "FlowDI"))
    network.connect(PortRef(electrolyzer1, "FlowDO"), PortRef(gaz_node, "FlowN"))
    network.connect(PortRef(electric_prod_2, "FlowP"), PortRef(elec_node_2, "FlowN"))
    network.connect(PortRef(elec_node_2, "FlowN"), PortRef(electrolyzer2, "FlowDI"))
    network.connect(PortRef(electrolyzer2, "FlowDO"), PortRef(gaz_node, "FlowN"))
    network.connect(PortRef(gaz_node, "FlowN"), PortRef(gaz_demand, "FlowD"))
    network.connect(PortRef(gaz_prod, "FlowP"), PortRef(gaz_node, "FlowN"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 2971.4285714285716


def test_electrolyzer_n_inputs_2():
    """
    Test avec un electrolyzer qui prend 2 input
    """

    elec_node_1 = Node(model=NODE_MODEL, id="e1")
    elec_node_2 = Node(model=NODE_MODEL, id="e2")
    gaz_node = Node(model=NODE_MODEL, id="g")

    electric_prod_1 = create_component(model=PROD_MODEL, id="ep1")
    electric_prod_2 = create_component(model=PROD_MODEL, id="ep2")

    gaz_prod = create_component(model=PROD_MODEL, id="gp")
    gaz_demand = create_component(model=DEMAND_MODEL, id="gd")

    electrolyzer = create_component(model=TWO_INPUTS_CONVERTOR_MODEL, id="ez")

    database = DataBase()
    database.add_data("gd", "demand", ConstantData(70))
    database.add_data("ep1", "p_max", ConstantData(100))
    database.add_data("ep2", "p_max", ConstantData(100))
    database.add_data("ep1", "cost", ConstantData(30))
    database.add_data("ep2", "cost", ConstantData(30))
    database.add_data("ez", "alpha1", ConstantData(0.7))
    database.add_data("ez", "alpha2", ConstantData(0.5))
    database.add_data("gp", "p_max", ConstantData(10))
    database.add_data("gp", "cost", ConstantData(40))

    network = Network("test")
    network.add_node(elec_node_1)
    network.add_node(elec_node_2)
    network.add_node(gaz_node)
    network.add_component(electric_prod_1)
    network.add_component(electric_prod_2)
    network.add_component(gaz_prod)
    network.add_component(gaz_demand)
    network.add_component(electrolyzer)

    network.connect(PortRef(electric_prod_1, "FlowP"), PortRef(elec_node_1, "FlowN"))
    network.connect(PortRef(elec_node_1, "FlowN"), PortRef(electrolyzer, "FlowDI1"))
    network.connect(PortRef(electric_prod_2, "FlowP"), PortRef(elec_node_2, "FlowN"))
    network.connect(PortRef(elec_node_2, "FlowN"), PortRef(electrolyzer, "FlowDI2"))
    network.connect(PortRef(electrolyzer, "FlowDO"), PortRef(gaz_node, "FlowN"))
    network.connect(PortRef(gaz_node, "FlowN"), PortRef(gaz_demand, "FlowD"))
    network.connect(PortRef(gaz_prod, "FlowP"), PortRef(gaz_node, "FlowN"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 2971.4285714285716


def test_electrolyzer_n_inputs_3():

    elec_node_1 = Node(model=NODE_MODEL, id="e1")
    elec_node_2 = Node(model=NODE_MODEL, id="e2")
    gaz_node = Node(model=NODE_MODEL, id="g")

    electric_prod_1 = create_component(model=PROD_MODEL, id="ep1")
    electric_prod_2 = create_component(model=PROD_MODEL, id="ep2")

    gaz_prod = create_component(model=PROD_MODEL, id="gp")
    gaz_demand = create_component(model=DEMAND_MODEL, id="gd")

    electrolyzer = create_component(model=CONVERTOR_MODEL_MOD, id="ez")
    consumption_electrolyzer = create_component(
        model=DECOMPOSE_1_FLOW_INTO_2_FLOW, id="ce"
    )

    database = DataBase()
    database.add_data("gd", "demand", ConstantData(70))
    database.add_data("ep1", "p_max", ConstantData(100))
    database.add_data("ep2", "p_max", ConstantData(100))
    database.add_data("ep1", "cost", ConstantData(30))
    database.add_data("ep2", "cost", ConstantData(30))
    database.add_data("ez", "alpha", ConstantData(0.7))
    database.add_data("gp", "p_max", ConstantData(10))
    database.add_data("gp", "cost", ConstantData(40))

    network = Network("test")
    network.add_node(elec_node_1)
    network.add_node(elec_node_2)
    network.add_node(gaz_node)
    network.add_component(electric_prod_1)
    network.add_component(electric_prod_2)
    network.add_component(gaz_prod)
    network.add_component(gaz_demand)
    network.add_component(electrolyzer)
    network.add_component(consumption_electrolyzer)

    network.connect(PortRef(electric_prod_1, "FlowP"), PortRef(elec_node_1, "FlowN"))
    network.connect(
        PortRef(elec_node_1, "FlowN"), PortRef(consumption_electrolyzer, "FlowDI1")
    )
    network.connect(PortRef(electric_prod_2, "FlowP"), PortRef(elec_node_2, "FlowN"))
    network.connect(
        PortRef(elec_node_2, "FlowN"), PortRef(consumption_electrolyzer, "FlowDI2")
    )
    network.connect(
        PortRef(consumption_electrolyzer, "FlowDO"), PortRef(electrolyzer, "FlowDI")
    )
    network.connect(PortRef(electrolyzer, "FlowDO"), PortRef(gaz_node, "FlowN"))
    network.connect(PortRef(gaz_node, "FlowN"), PortRef(gaz_demand, "FlowD"))
    network.connect(PortRef(gaz_prod, "FlowP"), PortRef(gaz_node, "FlowN"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 2971.4285714285716


def test_electrolyzer_n_inputs_4():
    elec_node_1 = Node(model=NODE_MODEL, id="e1")
    elec_node_2 = Node(model=NODE_MODEL, id="e2")
    gaz_node = Node(model=NODE_MODEL, id="g")

    electric_prod_1 = create_component(model=PROD_MODEL, id="ep1")
    electric_prod_2 = create_component(model=PROD_MODEL, id="ep2")

    gaz_prod = create_component(model=PROD_MODEL, id="gp")
    gaz_demand = create_component(model=DEMAND_MODEL, id="gd")

    electrolyzer = create_component(model=CONVERTOR_MODEL, id="ez")

    database = DataBase()
    database.add_data("gd", "demand", ConstantData(70))
    database.add_data("ep1", "p_max", ConstantData(100))
    database.add_data("ep2", "p_max", ConstantData(100))
    database.add_data("ep1", "cost", ConstantData(30))
    database.add_data("ep2", "cost", ConstantData(30))
    database.add_data("ez", "alpha", ConstantData(0.7))
    database.add_data("gp", "p_max", ConstantData(10))
    database.add_data("gp", "cost", ConstantData(40))

    network = Network("test")
    network.add_node(elec_node_1)
    network.add_node(elec_node_2)
    network.add_node(gaz_node)
    network.add_component(electric_prod_1)
    network.add_component(electric_prod_2)
    network.add_component(gaz_prod)
    network.add_component(gaz_demand)
    network.add_component(electrolyzer)

    network.connect(PortRef(electric_prod_1, "FlowP"), PortRef(elec_node_1, "FlowN"))
    network.connect(PortRef(elec_node_1, "FlowN"), PortRef(electrolyzer, "FlowDI"))
    network.connect(PortRef(electric_prod_2, "FlowP"), PortRef(elec_node_2, "FlowN"))
    network.connect(PortRef(elec_node_2, "FlowN"), PortRef(electrolyzer, "FlowDI"))
    network.connect(PortRef(electrolyzer, "FlowDO"), PortRef(gaz_node, "FlowN"))
    network.connect(PortRef(gaz_node, "FlowN"), PortRef(gaz_demand, "FlowD"))
    network.connect(PortRef(gaz_prod, "FlowP"), PortRef(gaz_node, "FlowN"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 2971.4285714285716
