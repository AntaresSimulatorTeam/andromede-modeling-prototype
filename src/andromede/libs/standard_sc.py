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

"""
Flow port 
"""
FLOW_PORT = PortType(id="flow_port", fields=[PortField("flow")])

"""
Simple node that manage flow interconnections.
"""
NODE_MODEL = model(
    id="Noeud",
    ports=[ModelPort(port_type=FLOW_PORT, port_name="FlowN")],
    binding_constraints=[
        Constraint(
            name="Balance",
            expression=port_field("FlowN", "flow").sum_connections() == literal(0),
        )
    ],
)

"""
Basic consumption model.
It consume a fixed amount of energy "d" each hour.
"""
DEMAND_MODEL = model(
    id="Energy Demand model",
    parameters=[float_parameter("demand", CONSTANT)],
    ports=[ModelPort(port_type=FLOW_PORT, port_name="FlowD")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowD", "flow"),
            definition=-param("demand"),
        )
    ],
)

"""
Model of a power generator.
The power production p is bounded between p_min and p_max.
An emission factor is used to determine the CO² emission according to the production.
"""
PROD_MODEL = model(
    id="Production",
    parameters=[float_parameter("p_max", CONSTANT), float_parameter("cost", CONSTANT)],
    variables=[
        float_variable("prod", lower_bound=literal(0), upper_bound=param("p_max"))
    ],
    ports=[ModelPort(port_type=FLOW_PORT, port_name="FlowP")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowP", "flow"),
            definition=var("prod"),
        )
    ],
    objective_operational_contribution=(param("cost") * var("prod")).sum().expec(),
)

"""
Simple Convertor model.
"""
CONVERTOR_MODEL = model(
    id="Convertor model",
    parameters=[float_parameter("alpha")],
    variables=[
        float_variable("input", lower_bound=literal(0)),
        float_variable("output"),
    ],
    ports=[
        ModelPort(port_type=FLOW_PORT, port_name="FlowDI"),
        ModelPort(port_type=FLOW_PORT, port_name="FlowDO"),
    ],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowDI", "flow"),
            definition=-var("input"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("FlowDO", "flow"),
            definition=var("output"),
        ),
    ],
    constraints=[
        Constraint(
            name="Conversion",
            expression=var("output") == var("input") * param("alpha"),
        )
    ],
)

"""
Two inputs Convertor model.
"""
TWO_INPUTS_CONVERTOR_MODEL = model(
    id="Convertor model",
    parameters=[float_parameter("alpha1"), float_parameter("alpha2")],
    variables=[
        float_variable("input1", lower_bound=literal(0)),
        float_variable("input2", lower_bound=literal(0)),
        float_variable("output"),
    ],
    ports=[
        ModelPort(port_type=FLOW_PORT, port_name="FlowDI1"),
        ModelPort(port_type=FLOW_PORT, port_name="FlowDI2"),
        ModelPort(port_type=FLOW_PORT, port_name="FlowDO"),
    ],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowDI1", "flow"),
            definition=-var("input1"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("FlowDI2", "flow"),
            definition=-var("input2"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("FlowDO", "flow"),
            definition=var("output"),
        ),
    ],
    constraints=[
        Constraint(
            name="Conversion",
            expression=var("output")
            == var("input1") * param("alpha1") + var("input2") * param("alpha2"),
        )
    ],
)

DECOMPOSE_1_FLOW_INTO_2_FLOW = model(
    id="Consumption electrolyzer model",
    variables=[
        float_variable("input1", lower_bound=literal(0)),
        float_variable("input2", lower_bound=literal(0)),
        float_variable("output"),
    ],
    ports=[
        ModelPort(port_type=FLOW_PORT, port_name="FlowDI1"),
        ModelPort(port_type=FLOW_PORT, port_name="FlowDI2"),
        ModelPort(port_type=FLOW_PORT, port_name="FlowDO"),
    ],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowDI1", "flow"),
            definition=-var("input1"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("FlowDI2", "flow"),
            definition=-var("input2"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("FlowDO", "flow"), definition=var("output")
        ),
    ],
    constraints=[
        Constraint(
            name="output",
            expression=var("output") == var("input1") + var("input2"),
        ),
    ],
)

CONVERTOR_MODEL_MOD = model(
    id="Convertor model",
    parameters=[float_parameter("alpha")],
    variables=[
        float_variable("input", lower_bound=literal(0)),
    ],
    ports=[
        ModelPort(port_type=FLOW_PORT, port_name="FlowDI"),
        ModelPort(port_type=FLOW_PORT, port_name="FlowDO"),
    ],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowDO", "flow"),
            definition=var("input") * param("alpha"),
        ),
    ],
    constraints=[
        Constraint(
            name="Conversion",
            expression=var("input") == port_field("FlowDI", "flow").sum_connections(),
        )
    ],
)
