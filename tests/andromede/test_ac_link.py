"""
Basic link model using ports
"""
import pytest

from andromede.expression import param, var
from andromede.expression.expression import literal, port_field
from andromede.expression.indexing_structure import IndexingStructure
from andromede.libs.standard import BALANCE_PORT_TYPE, DEMAND_MODEL, GENERATOR_MODEL
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
from andromede.simulation import OutputValues, TimeBlock, build_problem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    create_component,
)

"""
Port transfers flow and voltage angle.
"""
AC_PORT = PortType(id="AC_LINK", fields=[PortField("angle"), PortField("flow")])

"""
Node has 2 ports: one for angle dependent connections,
one for power-only connections.
Should we relax constraints on ports compatibility to allow to have only one here?
"""
AC_NODE_MODEL = model(
    id="AC_NODE",
    variables=[float_variable("angle")],
    ports=[
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="injections"),
        ModelPort(port_type=AC_PORT, port_name="links"),
    ],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("links", "angle"), definition=var("angle")
        )
    ],
    binding_constraints=[
        Constraint(
            name="Balance",
            expression=port_field("injections", "flow").sum_connections()
            + port_field("links", "flow").sum_connections()
            == literal(0),
        )
    ],
)

"""
Flow on the line is proportional to angle difference between extremities,
and inverse of impedance.
"""
AC_LINK_MODEL = model(
    id="LINK",
    parameters=[float_parameter("reactance", IndexingStructure(False, False))],
    variables=[float_variable("flow")],
    ports=[
        ModelPort(port_type=AC_PORT, port_name="port1"),
        ModelPort(port_type=AC_PORT, port_name="port2"),
    ],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("port1", "flow"),
            definition=-var("flow"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("port2", "flow"),
            definition=var("flow"),
        ),
    ],
    binding_constraints=[
        Constraint(
            name="AC flow",
            expression=var("flow")
            == 1
            / param("reactance")
            * (port_field("port1", "angle") - port_field("port2", "angle")),
        )
    ],
)


def test_ac_network_no_links():
    database = DataBase()
    database.add_data("D", "demand", ConstantData(100))

    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(30))

    node = Node(model=AC_NODE_MODEL, id="N")
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    gen = create_component(
        model=GENERATOR_MODEL,
        id="G",
    )

    network = Network("test")
    network.add_node(node)
    network.add_component(demand)
    network.add_component(gen)
    network.connect(PortRef(demand, "balance_port"), PortRef(node, "injections"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node, "injections"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3000


def test_ac_network():
    database = DataBase()
    database.add_data("D", "demand", ConstantData(100))

    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(35))

    database.add_data("L", "reactance", ConstantData(1))

    node1 = Node(model=AC_NODE_MODEL, id="1")
    node2 = Node(model=AC_NODE_MODEL, id="2")
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    gen = create_component(
        model=GENERATOR_MODEL,
        id="G",
    )

    link = create_component(
        model=AC_LINK_MODEL,
        id="L",
    )

    network = Network("test")
    network.add_node(node1)
    network.add_node(node2)
    network.add_component(demand)
    network.add_component(gen)
    network.add_component(link)
    network.connect(PortRef(demand, "balance_port"), PortRef(node1, "injections"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node2, "injections"))
    network.connect(PortRef(link, "port1"), PortRef(node1, "links"))
    network.connect(PortRef(link, "port2"), PortRef(node2, "links"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3500

    for variable in problem.solver.variables():
        if "balance_port_from" in variable.name():
            assert variable.solution_value() == 100
        if "balance_port_to" in variable.name():
            assert variable.solution_value() == -100


def test_parallel_ac_links():
    database = DataBase()
    database.add_data("D", "demand", ConstantData(100))

    database.add_data("G", "p_max", ConstantData(100))
    database.add_data("G", "cost", ConstantData(35))

    database.add_data("L1", "reactance", ConstantData(1))
    database.add_data("L2", "reactance", ConstantData(2))

    node1 = Node(model=AC_NODE_MODEL, id="1")
    node2 = Node(model=AC_NODE_MODEL, id="2")
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )
    gen = create_component(
        model=GENERATOR_MODEL,
        id="G",
    )
    link1 = create_component(
        model=AC_LINK_MODEL,
        id="L1",
    )
    link2 = create_component(
        model=AC_LINK_MODEL,
        id="L2",
    )

    network = Network("test")
    network.add_node(node1)
    network.add_node(node2)
    network.add_component(demand)
    network.add_component(gen)
    network.add_component(link1)
    network.add_component(link2)
    network.connect(PortRef(demand, "balance_port"), PortRef(node1, "injections"))
    network.connect(PortRef(gen, "balance_port"), PortRef(node2, "injections"))
    network.connect(PortRef(link1, "port1"), PortRef(node1, "links"))
    network.connect(PortRef(link1, "port2"), PortRef(node2, "links"))
    network.connect(PortRef(link2, "port1"), PortRef(node1, "links"))
    network.connect(PortRef(link2, "port2"), PortRef(node2, "links"))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 3500

    assert OutputValues(problem).component("L1").var("flow").value == pytest.approx(
        -66.67, abs=0.01
    )
    assert OutputValues(problem).component("L2").var("flow").value == pytest.approx(
        -33.33, abs=0.01
    )
