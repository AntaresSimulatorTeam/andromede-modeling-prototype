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
from andromede.expression.expression_efficient import (
    ExpressionNodeEfficient,
    InstancesTimeIndex,
    TimeAggregatorNode,
    TimeOperatorNode,
    expression_range,
    literal,
    param,
)


def shifted_param() -> ExpressionNodeEfficient:
    return TimeOperatorNode(
        param("q"), "TimeShift", InstancesTimeIndex(expression_range(0, 2))
    )


@pytest.mark.parametrize(
    "expr",
    [
        param("q"),
        param("p"),
        param("q") + 1,
        param("q") - 1,
        param("q") / 2,
        param("q") * 3,
        TimeAggregatorNode(
            TimeOperatorNode(
                param("q"), "TimeShift", InstancesTimeIndex(expression_range(1, 10, 2))
            ),
            "TimeSum",
            stay_roll=True,
        ),
        TimeAggregatorNode(
            TimeOperatorNode(
                param("q"),
                "TimeShift",
                InstancesTimeIndex(expression_range(1, param("p"))),
            ),
            "TimeSum",
            stay_roll=True,
        ),
        TimeAggregatorNode(shifted_param(), name="TimeSum", stay_roll=True),
        TimeAggregatorNode(shifted_param(), name="TimeAggregator", stay_roll=True),
        param("q") + 5 <= 2,
        param("q").expec(),
    ],
)
def test_equals(expr: ExpressionNodeEfficient) -> None:
    copy = copy_expression(expr)
    assert expressions_equal(expr, copy)


@pytest.mark.parametrize(
    "rhs, lhs",
    [
        (param("q"), param("y")),
        (literal(1), literal(2)),
        (param("q") + 1, param("q")),
        (
            TimeAggregatorNode(
                TimeOperatorNode(
                    param("q"),
                    "TimeShift",
                    InstancesTimeIndex(expression_range(1, param("p"))),
                ),
                "TimeSum",
                stay_roll=True,
            ),
            TimeAggregatorNode(
                TimeOperatorNode(
                    param("q"),
                    "TimeShift",
                    InstancesTimeIndex(expression_range(1, param("q"))),
                ),
                "TimeSum",
                stay_roll=True,
            ),
        ),
        (
            TimeAggregatorNode(
                TimeOperatorNode(
                    param("q"),
                    "TimeShift",
                    InstancesTimeIndex(expression_range(1, 10, 2)),
                ),
                "TimeSum",
                stay_roll=True,
            ),
            TimeAggregatorNode(
                TimeOperatorNode(
                    param("q"),
                    "TimeShift",
                    InstancesTimeIndex(expression_range(1, 10, 3)),
                ),
                "TimeSum",
                stay_roll=True,
            ),
        ),
        (
            TimeAggregatorNode(shifted_param(), name="TimeSum", stay_roll=True),
            TimeAggregatorNode(shifted_param(), name="TimeSum", stay_roll=False),
        ),
        (
            TimeAggregatorNode(shifted_param(), name="TimeSum", stay_roll=True),
            TimeAggregatorNode(shifted_param(), name="TimeAggregator", stay_roll=True),
        ),
        (param("q").expec(), param("y").expec()),
    ],
)
def test_not_equals(
    lhs: ExpressionNodeEfficient, rhs: ExpressionNodeEfficient
) -> None:
    assert not expressions_equal(lhs, rhs)


def test_tolerance() -> None:
    assert expressions_equal(literal(10), literal(10.09), abs_tol=0.1)
    assert not expressions_equal(literal(10), literal(10.11), abs_tol=0.1)
    assert expressions_equal(literal(10), literal(10.9), rel_tol=0.1)
    assert not expressions_equal(literal(10), literal(11.2), rel_tol=0.1)
