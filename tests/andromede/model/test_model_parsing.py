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
import io

from andromede.expression import literal, param, var
from andromede.libs.standard import CONSTANT
from andromede.model import (
    ModelPort,
    PortField,
    PortType,
    float_parameter,
    float_variable,
    model,
)
from andromede.model.model import PortFieldDefinition, PortFieldId
from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library


def test_library_parsing():
    yaml_lib = """
library:
  id: basic
  description: Basic library

  port-types:
    - id: flow
      description: A port which transfers power flow
      fields:
        - name: flow

  models:

    - id: generator
      description: A basic generator model
      parameters:
        - name: cost
          time-dependent: false
          scenario-dependent: false
        - name: p_max
          time-dependent: false
          scenario-dependent: false
      variables:
        - name: generation
          lower-bound: 0
          upper-bound: p_max
      ports:
        - name: injection_port
          type: flow
      port-field-definitions:
        - port: injection_port
          field: flow
          definition: generation
      objective: expec(sum(cost * generation))

    - id: node
      description: A basic balancing node model
      ports:
        - name: injection_port
          type: flow
      binding-constraints:
        - name: balance
          expression:  sum_connections(injection_port.flow) = 0

    - id: demand
      description: A basic fixed demand model
      parameters:
        - name: demand
          time-dependent: true
          scenario-dependent: true
      ports:
        - name: injection_port
          type: flow
      port-field-definitions:
        - port: injection_port
          field: flow
          definition: "-demand"
          
    - id: short-term-storage
      description: A short term storage
      parameters:
        - name: efficiency
        - name: level_min
        - name: level_max
        - name: p_max_withdrawal
        - name: p_max_injection
        - name: inflows
      variables:
        - name: injection
          lower_bound: 0
          upper_bound: p_max_injection
        - name: withdrawal
          lower_bound: 0
          upper_bound: p_max_withdrawal
        - name: level
          lower_bound: level_min
          upper_bound: level_max
      ports:
        - name: injection_port
          type: flow
      port-field-definitions:
        - port: injection_port
          field: flow
          definition: "injection - withdrawal"
      constraints:
        - name: Level equation
          expression: "level - level[-1] - efficiency * injection + withdrawal = inflows"
          
    - id: thermal-cluster-dhd
      description: DHD model for thermal cluster
      parameters:
        - name: cost
        - name: p_min
        - name: p_max
        - name: d_min_up
        - name: d_min_down
        - name: nb_units_max
        - name: nb_failures
          time-dependent: true
          scenario-dependent: true
      variables:
        - name: generation
          lower_bound: 0
          upper_bound: nb_units_max * p_max
          time-dependent: true
          scenario-dependent: true
        - name: nb_on
          lower_bound: 0
          upper_bound: nb_units_max
          time-dependent: true
          scenario-dependent: false
        - name: nb_stop
          lower_bound: 0
          upper_bound: nb_units_max
          time-dependent: true
          scenario-dependent: false
        - name: nb_start
          lower_bound: 0
          upper_bound: nb_units_max
          time-dependent: true
          scenario-dependent: false
      ports:
        - name: injection_port
          type: flow
      port-field-definitions:
        - port: injection_port
          field: flow
          definition: generation
      constraints:
        - name: Max generation
          expression: generation <= nb_on * p_max
        - name: Min generation
          expression: generation >= nb_on * p_min
        - name: Number of units variation
          expression: nb_on = nb_on[-1] + nb_start - nb_stop
        - name: Min up time
          expression: sum(nb_start[-d_min_up + 1 .. 0]) <= nb_on
        - name: Min down time
          expression: sum(nb_stop[-d_min_down + 1 .. 0]) <= nb_units_max[-d_min_down] - nb_on
      objective: expec(sum(cost * generation))
    """

    with io.StringIO(yaml_lib) as stream:
        input_lib = parse_yaml_library(stream)
    assert input_lib.id == "basic"
    assert len(input_lib.models) == 5
    assert len(input_lib.port_types) == 1

    lib = resolve_library(input_lib)
    assert len(lib.models) == 5
    assert len(lib.port_types) == 1
    port_type = lib.port_types["flow"]
    assert port_type == PortType(id="flow", fields=[PortField(name="flow")])
    gen_model = lib.models["generator"]
    assert gen_model == model(
        id="generator",
        parameters=[
            float_parameter("cost", structure=CONSTANT),
            float_parameter("p_max", structure=CONSTANT),
        ],
        variables=[
            float_variable(
                "generation", lower_bound=literal(0), upper_bound=param("p_max")
            )
        ],
        ports=[ModelPort(port_type=port_type, port_name="injection_port")],
        port_fields_definitions=[
            PortFieldDefinition(
                port_field=PortFieldId(port_name="injection_port", field_name="flow"),
                definition=var("generation"),
            )
        ],
        objective_contribution=(param("cost") * var("generation")).sum().expec(),
    )
