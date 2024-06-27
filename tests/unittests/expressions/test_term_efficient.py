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

from andromede.expression.expression_efficient import LiteralNode
from andromede.expression.linear_expression_efficient import TermEfficient
from andromede.expression.scenario_operator import Expectation, Variance
from andromede.expression.time_operator import TimeShift, TimeSum


@pytest.mark.parametrize(
    "term, expected",
    [
        (TermEfficient(1, "c", "x"), "+x"),
        (TermEfficient(-1, "c", "x"), "-x"),
        (TermEfficient(2.50, "c", "x"), "+2.5x"),
        (TermEfficient(-3, "c", "x"), "-3x"),
        (TermEfficient(-3, "c", "x", time_operator=TimeShift(-1)), "-3x.shift([-1])"),
        (TermEfficient(-3, "c", "x", time_aggregator=TimeSum(True)), "-3x.sum(True)"),
        (
            TermEfficient(
                -3,
                "c",
                "x",
                time_operator=TimeShift([2, 3]),
                time_aggregator=TimeSum(False),
            ),
            "-3x.shift([2, 3]).sum(False)",
        ),
        (TermEfficient(-3, "c", "x", scenario_operator=Expectation()), "-3x.expec()"),
        (
            TermEfficient(
                -3,
                "c",
                "x",
                time_aggregator=TimeSum(True),
                scenario_operator=Expectation(),
            ),
            "-3x.sum(True).expec()",
        ),
    ],
)
def test_printing_term(term: TermEfficient, expected: str) -> None:
    assert str(term) == expected


@pytest.mark.parametrize(
    "lhs, rhs, expected",
    [
        (TermEfficient(1, "c", "x"), TermEfficient(1, "c", "x"), True),
        (TermEfficient(1, "c", "x"), TermEfficient(2, "c", "x"), False),
        (
            TermEfficient(LiteralNode(1), "c", "x"),
            TermEfficient(LiteralNode(2), "c", "x"),
            False,
        ),
        (TermEfficient(-1, "c", "x"), TermEfficient(-1, "", "x"), False),
        (TermEfficient(2.50, "c", "x"), TermEfficient(2.50, "c", ""), False),
        (TermEfficient(-3, "c", "x"), TermEfficient(-3, "c", "y"), False),
        (
            TermEfficient(-3, "c", "x", time_operator=TimeShift(-1)),
            TermEfficient(-3, "c", "x", time_operator=TimeShift(-1)),
            True,
        ),
        (
            TermEfficient(-3, "c", "x", time_operator=TimeShift(-1)),
            TermEfficient(-3, "c", "x"),
            False,
        ),
        (
            TermEfficient(-3, "c", "x", time_aggregator=TimeSum(True)),
            TermEfficient(-3, "c", "x", time_aggregator=TimeSum(True)),
            True,
        ),
        (
            TermEfficient(-3, "c", "x", time_aggregator=TimeSum(True)),
            TermEfficient(-3, "c", "x", time_operator=TimeShift(-1)),
            False,
        ),
        (
            TermEfficient(
                -3,
                "c",
                "x",
                time_operator=TimeShift([2, 3]),
                time_aggregator=TimeSum(False),
            ),
            TermEfficient(
                -3,
                "c",
                "x",
                time_operator=TimeShift([1, 3]),
                time_aggregator=TimeSum(False),
            ),
            False,
        ),
        (
            TermEfficient(-3, "c", "x", scenario_operator=Expectation()),
            TermEfficient(-3, "c", "x", scenario_operator=Expectation()),
            True,
        ),
        (
            TermEfficient(-3, "c", "x", scenario_operator=Expectation()),
            TermEfficient(-3, "c", "x", scenario_operator=Variance()),
            False,
        ),
        (
            TermEfficient(
                -3,
                "c",
                "x",
                time_aggregator=TimeSum(True),
                scenario_operator=Expectation(),
            ),
            TermEfficient(
                -3,
                "c",
                "x",
                time_aggregator=TimeSum(False),
                scenario_operator=Expectation(),
            ),
            False,
        ),
    ],
)
def test_term_equality(lhs: TermEfficient, rhs: TermEfficient, expected: bool) -> None:
    assert (lhs == rhs) == expected
