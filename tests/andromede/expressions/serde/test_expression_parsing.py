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

from andromede.expression import ExpressionNode, literal, param, var
from andromede.expression.equality import expressions_equal
from andromede.expression.expression import port_field
from andromede.expression.parsing.parse_expression import (
    ModelIdentifiers,
    parse_expression,
)


@pytest.mark.parametrize(
    "expression_str, expected",
    [
        (
            "1 + 2 * x = p",
            literal(1) + 2 * var("x") == param("p"),
        ),
        (
            "port.f <= 0",
            port_field("port", "f") <= 0,
        ),
        ("x.sum()", var("x").sum()),
        ("x.shift(-1)", var("x").shift(-literal(1))),
        ("port.f.sum_connections()", port_field("port", "f").sum_connections()),
    ],
)
def test_parsing_visitor(expression_str: str, expected: ExpressionNode):
    identifiers = ModelIdentifiers(variables={"x"}, parameters={"p"})

    expr = parse_expression(expression_str, identifiers)

    assert expressions_equal(expr, expected)
