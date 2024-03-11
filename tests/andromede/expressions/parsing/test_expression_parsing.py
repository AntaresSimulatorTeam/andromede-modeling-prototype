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
from antlr4 import CommonTokenStream, InputStream

from andromede.expression import ExpressionNode, literal, param, print_expr, var
from andromede.expression.equality import expressions_equal
from andromede.expression.expression import ExpressionRange, port_field
from andromede.expression.parsing.antlr.ExprLexer import ExprLexer
from andromede.expression.parsing.antlr.ExprParser import ExprParser
from andromede.expression.parsing.parse_expression import (
    ModelIdentifiers,
    parse_expression,
    AntaresParseException,
)


@pytest.mark.parametrize(
    "expression_str, expected",
    [
        ("1 + 2", literal(1) + 2),
        ("1 - 2", literal(1) - 2),
        ("1 - 3 + 4 - 2", literal(1) - 3 + 4 - 2),
        (
            "1 + 2 * x = p",
            literal(1) + 2 * var("x") == param("p"),
        ),
        (
            "port.f <= 0",
            port_field("port", "f") <= 0,
        ),
        ("sum(x)", var("x").sum()),
        ("x[-1]", var("x").eval(-literal(1))),
        ("x[-1..5]", var("x").eval(ExpressionRange(-literal(1), literal(5)))),
        ("x[1]", var("x").eval(1)),
        ("x[t-1]", var("x").shift(-literal(1))),
        (
            "x[t-1, t+4]",
            var("x").shift([-literal(1), literal(4)]),
        ),
        (
            "x[t-1, t, t+4]",
            var("x").shift([-literal(1), literal(0), literal(4)]),
        ),
        ("x[t-1..t+5]", var("x").shift(ExpressionRange(-literal(1), literal(5)))),
        ("x[t-1..t]", var("x").shift(ExpressionRange(-literal(1), literal(0)))),
        ("x[t..t+5]", var("x").shift(ExpressionRange(literal(0), literal(5)))),
        ("x[t]", var("x")),
        ("x[t+p]", var("x").shift(param("p"))),
        (
            "sum(x[-1..5])",
            var("x").eval(ExpressionRange(-literal(1), literal(5))).sum(),
        ),
        ("sum_connections(port.f)", port_field("port", "f").sum_connections()),
        (
            "level - level[-1] - efficiency * injection + withdrawal = inflows",
            var("level")
            - var("level").eval(-literal(1))
            - param("efficiency") * var("injection")
            + var("withdrawal")
            == param("inflows"),
        ),
        (
            "sum(nb_start[-d_min_up + 1 .. 0]) <= nb_on",
            var("nb_start")
            .eval(ExpressionRange(-param("d_min_up") + 1, literal(0)))
            .sum()
            <= var("nb_on"),
        ),
        (
            "expec(sum(cost * generation))",
            (param("cost") * var("generation")).sum().expec(),
        ),
    ],
)
def test_parsing_visitor(expression_str: str, expected: ExpressionNode):
    identifiers = ModelIdentifiers(
        variables={
            "x",
            "level",
            "injection",
            "withdrawal",
            "nb_start",
            "nb_on",
            "generation",
        },
        parameters={"p", "inflows", "efficiency", "d_min_up", "cost"},
    )

    expr = parse_expression(expression_str, identifiers)
    print()
    print(print_expr(expr))
    assert expressions_equal(expr, expected)


def test_parse_cancellation_err():
    # Console log error is displayed !
    identifiers = ModelIdentifiers(
        variables={
            "x",
            "level",
            "injection",
            "withdrawal",
            "nb_start",
            "nb_on",
            "generation",
        },
        parameters={
            "p",
            "inflows",
            "efficiency",
            "d_min_up",
            "cost",
        },
    )
    expression_str = "x[t+1-t]"

    with pytest.raises(
        AntaresParseException,
        match=r"An error occurred during parsing: ParseCancellationException",
    ):
        parse_expression(expression_str, identifiers)
