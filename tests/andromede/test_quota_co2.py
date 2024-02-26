from andromede.expression import literal, param, var
from andromede.expression.expression import port_field
from andromede.libs.standard import CONSTANT, TIME_AND_SCENARIO_FREE
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
from andromede.simulation import TimeBlock, build_problem, OutputValues
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    create_component,
)

"""
Power flow port 
"""
FLOW_PORT = PortType(id="flow_port", fields=[PortField("F")])

"""
CO² emmission port
"""
EMISSION_PORT = PortType(id="emission_port", fields=[PortField("Q")])

"""
Simple node that manage flow interconnections.
"""
NODE_MODEL = model(
    id="Noeud",
    ports=[ModelPort(port_type=FLOW_PORT, port_name="FlowN")],
    binding_constraints=[
        Constraint(
            name="Balance",
            expression=port_field("FlowN", "F").sum_connections() == literal(0),
        )
    ],
)

"""
Model of a simple power generator that takes account of CO² emissions related to the production.
The power production p is bounded between p_min and p_max.
An emission factor is used to determine the CO² emission according to the production.
"""
C02_POWER_MODEL = model(
    id='CO2 power',
    parameters=[float_parameter("p_min", CONSTANT),
                float_parameter("p_max", CONSTANT),
                float_parameter("cost", CONSTANT),
                float_parameter("taux_emission", CONSTANT)],
    variables=[float_variable("p", lower_bound=param("p_min"), upper_bound=param("p_max"))],
    ports=[ModelPort(port_type=FLOW_PORT, port_name="FlowP"),
           ModelPort(port_type=EMISSION_PORT, port_name="OutCO2")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowP", "F"),
            definition=var("p"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("OutCO2", "Q"),
            definition=var("p") * param("taux_emission"),
        )
    ],
    objective_contribution=(param("cost") * var("p")).sum().expec(),
)


"""
Basic energy consumption model.
It consume a fixed amount of energy "d" each hour.
"""
DEMAND_MODEL = model(
    id='Demand model',
    parameters=[float_parameter("d", CONSTANT)],
    ports=[ModelPort(port_type=FLOW_PORT, port_name="FlowD")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowD", "F"),
            definition=-param("d"),
        )
    ]
)

"""
Model of the CO² quota. 
It takes a set a CO² emissions as input. It forces the sum of those emissions to be smaller than a predefined quota. 
"""
QUOTA_CO2_MODEL = model(
    id='QuotaCO2',
    parameters=[float_parameter("quota", CONSTANT)],
    ports=[ModelPort(port_type=EMISSION_PORT, port_name="emissionCO2")],
    constraints=[Constraint(name='Bound CO2', expression=port_field("emissionCO2", "Q").sum_connections() <= param("quota"))]
)

"""
Link model to interconnect nodes.
"""
LINK_MODEL = model(
    id="LINK",
    parameters=[float_parameter("f_max", TIME_AND_SCENARIO_FREE)],
    variables=[
        float_variable("flow", lower_bound=-param("f_max"), upper_bound=param("f_max"))
    ],
    ports=[
        ModelPort(port_type=FLOW_PORT, port_name="port_from"),
        ModelPort(port_type=FLOW_PORT, port_name="port_to"),
    ],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("port_from", "F"),
            definition=-var("flow"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("port_to", "F"),
            definition=var("flow"),
        )
    ]
)


"""
build the quota CO² test system.

    N1 -----N2----Demand         ^
    |       |
    Oil1    Coal1
    |       |
    ---------
        |
    MonQuotaCO2

"""
def test_quota_co2():
    n1 = Node(model=NODE_MODEL, id="N1")
    n2 = Node(model=NODE_MODEL, id="N2")
    oil1 = create_component(model=C02_POWER_MODEL, id="Oil1")
    coal1 = create_component(model=C02_POWER_MODEL, id="Coal1")
    l12 = create_component(model=LINK_MODEL, id='L12')
    demand = create_component(model=DEMAND_MODEL, id='Demand')
    monQuotaCO2 = create_component(model=QUOTA_CO2_MODEL, id='MonQuotaCO2')

    network = Network("test")
    network.add_node(n1)
    network.add_node(n2)
    network.add_component(oil1)
    network.add_component(coal1)
    network.add_component(l12)
    network.add_component(demand)
    network.add_component(monQuotaCO2)

    network.connect(PortRef(demand, "FlowD"), PortRef(n2, "FlowN"))
    network.connect(PortRef(n2, "FlowN"), PortRef(l12, "port_from"))
    network.connect(PortRef(l12, "port_to"), PortRef(n1, "FlowN"))
    network.connect(PortRef(n1, "FlowN"), PortRef(oil1, "FlowP"))
    network.connect(PortRef(n2, 'FlowN'), PortRef(coal1, "FlowP"))
    network.connect(PortRef(oil1, "OutCO2"), PortRef(monQuotaCO2, "emissionCO2"))
    network.connect(PortRef(coal1, "OutCO2"), PortRef(monQuotaCO2, "emissionCO2"))

    database = DataBase()
    database.add_data("Demand", "d", ConstantData(100))
    database.add_data("Coal1", "p_min", ConstantData(0))
    database.add_data("Oil1", "p_min", ConstantData(0))
    database.add_data("Coal1", "p_max", ConstantData(100))
    database.add_data("Oil1", "p_max", ConstantData(100))
    database.add_data("Coal1", "taux_emission", ConstantData(2))
    database.add_data("Oil1", "taux_emission", ConstantData(1))
    database.add_data("Coal1", "cost", ConstantData(10))
    database.add_data("Oil1", "cost", ConstantData(100))
    database.add_data("L12", "f_max", ConstantData(100))
    # when the bug in the port is fixed, the quota should be 150
    database.add_data("MonQuotaCO2", "quota", ConstantData(150))

    scenarios = 1
    problem = build_problem(network, database, TimeBlock(1, [0]), scenarios)
    status = problem.solver.Solve()

    output = OutputValues(problem)
    oil1_p = output.component('Oil1').var('p').value
    coal1_p = output.component('Coal1').var('p').value
    l12_flow = output.component('L12').var('flow').value

    assert status == problem.solver.OPTIMAL
    assert problem.solver.Objective().Value() == 5500
    assert oil1_p == 50
    assert coal1_p == 50
    assert l12_flow == -50