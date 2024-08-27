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

from andromede.expression.expression import LiteralNode
from andromede.expression.linear_expression import Term
from andromede.expression.scenario_operator import Expectation, Variance
from andromede.expression.time_operator import TimeShift, TimeSum


@pytest.mark.parametrize(
    "term, expected",
    [
        (Term(1, "c", "x"), "+x"),
        (Term(-1, "c", "x"), "-x"),
        (Term(2.50, "c", "x"), "2.5x"),
        (Term(-3, "c", "x"), "-3.0x"),
        (Term(-3, "c", "x", time_operator=TimeShift(-1)), "-3.0x.shift(-1)"),
        (Term(-3, "c", "x", time_aggregator=TimeSum(True)), "-3.0x.sum(True)"),
        (
            Term(
                -3,
                "c",
                "x",
                time_operator=TimeShift([2, 3]),
                time_aggregator=TimeSum(False),
            ),
            "-3.0x.shift([2, 3]).sum(False)",
        ),
        (
            Term(-3, "c", "x", scenario_aggregator=Expectation()),
            "-3.0x.expec()",
        ),
        (
            Term(
                -3,
                "c",
                "x",
                time_aggregator=TimeSum(True),
                scenario_aggregator=Expectation(),
            ),
            "-3.0x.sum(True).expec()",
        ),
    ],
)
def test_printing_term(term: Term, expected: str) -> None:
    assert str(term) == expected


@pytest.mark.parametrize(
    "lhs, rhs, expected",
    [
        (Term(1, "c", "x"), Term(1, "c", "x"), True),
        (Term(1, "c", "x"), Term(2, "c", "x"), False),
        (
            Term(LiteralNode(1), "c", "x"),
            Term(LiteralNode(2), "c", "x"),
            False,
        ),
        (Term(-1, "c", "x"), Term(-1, "", "x"), False),
        (Term(2.50, "c", "x"), Term(2.50, "c", ""), False),
        (Term(-3, "c", "x"), Term(-3, "c", "y"), False),
        (
            Term(-3, "c", "x", time_operator=TimeShift(-1)),
            Term(-3, "c", "x", time_operator=TimeShift(-1)),
            True,
        ),
        (
            Term(-3, "c", "x", time_operator=TimeShift(-1)),
            Term(-3, "c", "x"),
            False,
        ),
        (
            Term(-3, "c", "x", time_aggregator=TimeSum(True)),
            Term(-3, "c", "x", time_aggregator=TimeSum(True)),
            True,
        ),
        (
            Term(-3, "c", "x", time_aggregator=TimeSum(True)),
            Term(-3, "c", "x", time_operator=TimeShift(-1)),
            False,
        ),
        (
            Term(
                -3,
                "c",
                "x",
                time_operator=TimeShift([2, 3]),
                time_aggregator=TimeSum(False),
            ),
            Term(
                -3,
                "c",
                "x",
                time_operator=TimeShift([1, 3]),
                time_aggregator=TimeSum(False),
            ),
            False,
        ),
        (
            Term(-3, "c", "x", scenario_aggregator=Expectation()),
            Term(-3, "c", "x", scenario_aggregator=Expectation()),
            True,
        ),
        (
            Term(-3, "c", "x", scenario_aggregator=Expectation()),
            Term(-3, "c", "x", scenario_aggregator=Variance()),
            False,
        ),
        (
            Term(
                -3,
                "c",
                "x",
                time_aggregator=TimeSum(True),
                scenario_aggregator=Expectation(),
            ),
            Term(
                -3,
                "c",
                "x",
                time_aggregator=TimeSum(False),
                scenario_aggregator=Expectation(),
            ),
            False,
        ),
    ],
)
def test_term_equality(lhs: Term, rhs: Term, expected: bool) -> None:
    assert (lhs == rhs) == expected
