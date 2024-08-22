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

import pytest

from andromede.expression.expression_efficient import literal
from andromede.expression.linear_expression_efficient import port_field
from andromede.libs.standard import DEMAND_MODEL
from andromede.model import Constraint, ModelPort, PortType, model
from andromede.model.constraint import Constraint
from andromede.model.model import ModelPort, model
from andromede.model.port import PortType
from andromede.study import Node, PortRef, PortsConnection, create_component


def test_port_type_compatibility_ko() -> None:
    NODE_BALANCE_MODEL_FAKE = model(
        id="NODE_BALANCE_MODEL",
        ports=[
            ModelPort(port_type=PortType("balance_fake", []), port_name="balance_port")
        ],
        constraints=[
            Constraint(
                name="Balance",
                expression_init=port_field("balance_port", "flow").sum_connections()
                == literal(0),
            )
        ],
    )
    node = Node(id="N", model=NODE_BALANCE_MODEL_FAKE)
    demand = create_component(
        model=DEMAND_MODEL,
        id="D",
    )

    port_1 = PortRef(demand, "balance_port")
    port_2 = PortRef(node, "balance_port")

    with pytest.raises(ValueError):
        PortsConnection(port_1, port_2)
