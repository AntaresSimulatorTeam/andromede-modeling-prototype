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


from andromede.expression.copy import copy_expression
from andromede.expression.equality import expressions_equal
from andromede.expression.expression import (
    TimeAggregatorNode,
    expression_range,
)
from andromede.expression.expression_efficient import literal, param
from andromede.expression.linear_expression_efficient import LinearExpressionEfficient, var


def shifted_x():
    return var("x").shift(expression_range(0, 2))


@pytest.mark.parametrize(
    "expr",
    [
        var("x"),
        param("p"),
        var("x") + 1,
        var("x") - 1,
        var("x") / 2,
        var("x") * 3,
        var("x").shift(expression_range(1, 10, 2)).sum(),
        var("x").shift(expression_range(1, param("p"))).sum(),
        TimeAggregatorNode(shifted_x(), name="TimeSum", stay_roll=True),
        TimeAggregatorNode(shifted_x(), name="TimeAggregator", stay_roll=True),
        var("x") + 5 <= 2,
        var("x").expec(),
    ],
)
def test_equals(expr: LinearExpressionEfficient) -> None:
    copy = copy_expression(expr)
    assert expressions_equal(expr, copy)


@pytest.mark.parametrize(
    "rhs, lhs",
    [
        (var("x"), var("y")),
        (literal(1), literal(2)),
        (var("x") + 1, var("x")),
        (
            var("x").shift(expression_range(1, param("p"))).sum(),
            var("x").shift(expression_range(1, param("q"))).sum(),
        ),
        (
            var("x").shift(expression_range(1, 10, 2)).sum(),
            var("x").shift(expression_range(1, 10, 3)).sum(),
        ),
        (
            TimeAggregatorNode(shifted_x(), name="TimeSum", stay_roll=True),
            TimeAggregatorNode(shifted_x(), name="TimeSum", stay_roll=False),
        ),
        (
            TimeAggregatorNode(shifted_x(), name="TimeSum", stay_roll=True),
            TimeAggregatorNode(shifted_x(), name="TimeAggregator", stay_roll=True),
        ),
        (var("x").expec(), var("y").expec()),
    ],
)
def test_not_equals(lhs: LinearExpressionEfficient, rhs: LinearExpressionEfficient) -> None:
    assert not expressions_equal(lhs, rhs)


def test_tolerance():
    assert expressions_equal(literal(10), literal(10.09), abs_tol=0.1)
    assert not expressions_equal(literal(10), literal(10.11), abs_tol=0.1)
    assert expressions_equal(literal(10), literal(10.9), rel_tol=0.1)
    assert not expressions_equal(literal(10), literal(11.2), rel_tol=0.1)
