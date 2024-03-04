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

from andromede.expression import literal, param, var
from andromede.expression.expression import port_field
from andromede.libs.standard import BALANCE_PORT_TYPE, CONSTANT, TIME_AND_SCENARIO_FREE
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
    ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowP")],
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
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDI"),
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDO"),
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
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDI1"),
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDI2"),
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDO"),
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
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDI1"),
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDI2"),
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDO"),
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
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDI"),
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowDO"),
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

"""
CO² emmission port
"""
EMISSION_PORT = PortType(id="emission_port", fields=[PortField("Q")])

"""
Model of a simple power generator that takes account of CO² emissions related to the production.
The power production p is bounded between p_min and p_max.
An emission factor is used to determine the CO² emission according to the production.
"""
C02_POWER_MODEL = model(
    id="CO2 power",
    parameters=[
        float_parameter("p_min", CONSTANT),
        float_parameter("p_max", CONSTANT),
        float_parameter("cost", CONSTANT),
        float_parameter("emission_rate", CONSTANT),
    ],
    variables=[
        float_variable("p", lower_bound=param("p_min"), upper_bound=param("p_max"))
    ],
    ports=[
        ModelPort(port_type=BALANCE_PORT_TYPE, port_name="FlowP"),
        ModelPort(port_type=EMISSION_PORT, port_name="OutCO2"),
    ],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("FlowP", "flow"),
            definition=var("p"),
        ),
        PortFieldDefinition(
            port_field=PortFieldId("OutCO2", "Q"),
            definition=var("p") * param("emission_rate"),
        ),
    ],
    objective_operational_contribution=(param("cost") * var("p")).sum().expec(),
)

"""
Model of the CO² quota. 
It takes a set a CO² emissions as input. It forces the sum of those emissions to be smaller than a predefined quota. 
"""
QUOTA_CO2_MODEL = model(
    id="QuotaCO2",
    parameters=[float_parameter("quota", CONSTANT)],
    ports=[ModelPort(port_type=EMISSION_PORT, port_name="emissionCO2")],
    binding_constraints=[
        Constraint(
            name="Bound CO2",
            expression=port_field("emissionCO2", "Q").sum_connections()
            <= param("quota"),
        )
    ],
)
