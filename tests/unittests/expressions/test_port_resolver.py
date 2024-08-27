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

from typing import Dict, List

import pytest

from andromede.expression.equality import expressions_equal
from andromede.expression.linear_expression import (
    LinearExpressionEfficient,
    PortFieldId,
    PortFieldKey,
    linear_expressions_equal,
    port_field,
    var,
)


@pytest.mark.parametrize(
    "port_expr, expected",
    [
        (port_field("port", "field") + 2, var("flow") + 2),
        (port_field("port", "field") - 2, var("flow") - 2),
        (port_field("port", "field") * 2, 2 * var("flow")),
        (port_field("port", "field") / 2, var("flow") / 2),
        (port_field("port", "field") * 0, LinearExpressionEfficient()),
    ],
)
def test_port_field_resolution(
    port_expr: LinearExpressionEfficient, expected: LinearExpressionEfficient
) -> None:
    ports_expressions: Dict[PortFieldKey, List[LinearExpressionEfficient]] = {}

    key = PortFieldKey("com_id", PortFieldId(field_name="field", port_name="port"))
    expression = var("flow")

    ports_expressions[key] = [expression]

    print()
    print(port_expr.resolve_port("com_id", ports_expressions))
    print(expected)

    assert linear_expressions_equal(
        port_expr.resolve_port("com_id", ports_expressions), expected
    )


def test_port_field_resolution_sum() -> None:
    ports_expressions: Dict[PortFieldKey, List[LinearExpressionEfficient]] = {}

    key = PortFieldKey("com_id", PortFieldId(field_name="field", port_name="port"))

    ports_expressions[key] = [var("flow1"), var("flow2")]

    expression_2 = port_field("port", "field").sum_connections()
    assert linear_expressions_equal(
        expression_2.resolve_port("com_id", ports_expressions),
        var("flow1") + var("flow2"),
    )
