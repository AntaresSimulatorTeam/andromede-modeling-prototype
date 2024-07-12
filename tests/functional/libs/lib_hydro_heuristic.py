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
from andromede.expression.indexing_structure import IndexingStructure
from andromede.model import float_parameter, float_variable, model
from andromede.model.constraint import Constraint
from andromede.model.model import ModelPort, PortFieldDefinition, PortFieldId
from andromede.model.parameter import float_parameter
from andromede.model.port import PortField, PortType
from andromede.model.variable import float_variable

BALANCE_PORT_TYPE = PortType(id="balance", fields=[PortField("flow")])

CONSTANT = IndexingStructure(False, False)
TIME_AND_SCENARIO_FREE = IndexingStructure(True, True)
ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, True)
NON_ANTICIPATIVE_TIME_VARYING = IndexingStructure(True, False)
CONSTANT_PER_SCENARIO = IndexingStructure(False, True)


HYDRO_MODEL = model(
    id="H",
    parameters=[
        float_parameter("max_generating", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("min_generating", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("capacity", CONSTANT),
        float_parameter("initial_level", CONSTANT_PER_SCENARIO),
        float_parameter("inflow", TIME_AND_SCENARIO_FREE),
        float_parameter(
            "max_epsilon", NON_ANTICIPATIVE_TIME_VARYING
        ),  # not really a parameter, it is just to implement correctly one constraint
        float_parameter("lower_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("upper_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
    ],
    variables=[
        float_variable(
            "generating",
            lower_bound=param("min_generating"),
            upper_bound=param("max_generating"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "level",
            lower_bound=literal(0),
            upper_bound=param("capacity"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "overflow",
            lower_bound=literal(0),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "epsilon",
            lower_bound=-param("max_epsilon"),
            upper_bound=param("max_epsilon"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
    ],
    constraints=[
        Constraint(
            "Level balance",
            var("level")
            == var("level").shift(-1)
            - var("generating")
            - var("overflow")
            + param("inflow")
            + var("epsilon"),
        ),
        Constraint(
            "Initial level",
            var("level").eval(literal(0))
            == param("initial_level")
            - var("generating").eval(literal(0))
            - var("overflow").eval(literal(0))
            + param("inflow").eval(literal(0)),
        ),
    ],
    ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("balance_port", "flow"),
            definition=var("generating"),
        )
    ],
)

HYDRO_MODEL_RULE_CURVES = model(
    id="H",
    parameters=[
        float_parameter("max_generating", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("min_generating", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("capacity", CONSTANT),
        float_parameter("initial_level", CONSTANT_PER_SCENARIO),
        float_parameter("inflow", TIME_AND_SCENARIO_FREE),
        float_parameter(
            "max_epsilon", NON_ANTICIPATIVE_TIME_VARYING
        ),  # not really a parameter, it is just to implement correctly one constraint
        float_parameter("lower_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("upper_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
    ],
    variables=[
        float_variable(
            "generating",
            lower_bound=param("min_generating"),
            upper_bound=param("max_generating"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "level",
            lower_bound=param("lower_rule_curve"),
            upper_bound=param("capacity"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "overflow",
            lower_bound=literal(0),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "epsilon",
            lower_bound=-param("max_epsilon"),
            upper_bound=param("max_epsilon"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
    ],
    constraints=[
        Constraint(
            "Level balance",
            var("level")
            == var("level").shift(-1)
            - var("generating")
            - var("overflow")
            + param("inflow")
            + var("epsilon"),
        ),
        Constraint(
            "Initial level",
            var("level").eval(literal(0))
            == param("initial_level")
            - var("generating").eval(literal(0))
            - var("overflow").eval(literal(0))
            + param("inflow").eval(literal(0)),
        ),
    ],
    ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("balance_port", "flow"),
            definition=var("generating"),
        )
    ],
)

HYDRO_MODEL_WITH_TARGET = model(
    id="H",
    parameters=[
        float_parameter("max_generating", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("min_generating", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("capacity", CONSTANT),
        float_parameter("initial_level", CONSTANT_PER_SCENARIO),
        float_parameter("inflow", TIME_AND_SCENARIO_FREE),
        float_parameter(
            "max_epsilon", NON_ANTICIPATIVE_TIME_VARYING
        ),  # not really a parameter, it is just to implement correctly one constraint
        float_parameter("lower_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("upper_rule_curve", NON_ANTICIPATIVE_TIME_VARYING),
        float_parameter("overall_target", CONSTANT_PER_SCENARIO),
    ],
    variables=[
        float_variable(
            "generating",
            lower_bound=param("min_generating"),
            upper_bound=param("max_generating"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "level",
            lower_bound=literal(0),
            upper_bound=param("capacity"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "overflow",
            lower_bound=literal(0),
            structure=TIME_AND_SCENARIO_FREE,
        ),
        float_variable(
            "epsilon",
            lower_bound=-param("max_epsilon"),
            upper_bound=param("max_epsilon"),
            structure=TIME_AND_SCENARIO_FREE,
        ),
    ],
    constraints=[
        Constraint(
            "Level balance",
            var("level")
            == var("level").shift(-1)
            - var("generating")
            - var("overflow")
            + param("inflow")
            + var("epsilon"),
        ),
        Constraint(
            "Initial level",
            var("level").eval(literal(0))
            == param("initial_level")
            - var("generating").eval(literal(0))
            - var("overflow").eval(literal(0))
            + param("inflow").eval(literal(0)),
        ),
        Constraint(
            "Respect generating target",
            var("generating").sum() + var("overflow").sum() == param("overall_target"),
        ),
    ],
    ports=[ModelPort(port_type=BALANCE_PORT_TYPE, port_name="balance_port")],
    port_fields_definitions=[
        PortFieldDefinition(
            port_field=PortFieldId("balance_port", "flow"),
            definition=var("generating"),
        )
    ],
)
