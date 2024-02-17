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
          lowed-bound: 0
          upper-bound: p_max
      ports:
        - name: injection_port
          type: flow
      port-field-definitions:
        - port: injection_port
          field: flow
          definition: generation
      objective: "cost * generation"

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
    """

    with io.StringIO(yaml_lib) as stream:
        input_lib = parse_yaml_library(stream)
    assert input_lib.id == "basic"
    assert len(input_lib.models) == 3
    assert len(input_lib.port_types) == 1
    lib = resolve_library(input_lib)
    assert len(lib.models) == 3
    assert len(lib.port_types) == 1
    print(lib)
