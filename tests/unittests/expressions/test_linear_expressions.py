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

from typing import Dict

import pytest

from andromede.expression.expression import TimeAggregatorNode, expression_range, param
from andromede.expression.linear_expression import (
    LinearExpression,
    PortFieldId,
    PortFieldTerm,
    Term,
    _copy_expression,
    linear_expressions_equal,
    var,
    wrap_in_linear_expr,
)
from andromede.expression.scenario_operator import Expectation
from andromede.expression.time_operator import TimeShift, TimeSum


@pytest.mark.parametrize(
    "coeff, var_name, constant, expec_str",
    [
        (0, "x", 0, "0"),
        (1, "x", 0, "+x"),
        (1, "x", 1, "+x + 1.0"),
        (3.7, "x", 1, "3.7x + 1.0"),
        (0, "x", 1, " + 1.0"),
    ],
)
def test_affine_expression_printing_should_reflect_required_formatting(
    coeff: float, var_name: str, constant: float, expec_str: str
) -> None:
    expr = LinearExpression([Term(coeff, "c", var_name)], constant)
    assert str(expr) == expec_str


@pytest.mark.parametrize(
    "expr",
    [
        var("x"),
        wrap_in_linear_expr(param("p")),
        var("x") + 1,
        var("x") - 1,
        var("x") / 2,
        var("x") * 3,
        var("x").sum(shift=expression_range(1, 10, 2)),
        var("x").sum(shift=expression_range(1, param("p"))),
        var("x").expec(),
    ],
)
def test_linear_expressions_equal(expr: LinearExpression) -> None:
    copy = LinearExpression()
    _copy_expression(expr, copy)
    assert linear_expressions_equal(expr, copy)


@pytest.mark.parametrize(
    "lhs, rhs",
    [
        (
            LinearExpression([], 1) + LinearExpression([], 3),
            LinearExpression([], 4),
        ),
        (
            LinearExpression([], 4) / LinearExpression([], 2),
            LinearExpression([], 2),
        ),
        (
            LinearExpression([], 4) * LinearExpression([], 2),
            LinearExpression([], 8),
        ),
        (
            LinearExpression([], 4) - LinearExpression([], 2),
            LinearExpression([], 2),
        ),
    ],
)
def test_constant_expressions(lhs: LinearExpression, rhs: LinearExpression) -> None:
    assert linear_expressions_equal(lhs, rhs)


@pytest.mark.parametrize(
    "terms_dict, constant, exp_terms, exp_constant",
    [
        ({"x": Term(0, "c", "x")}, 1, {}, 1),
        ({"x": Term(1, "c", "x")}, 1, {"x": Term(1, "c", "x")}, 1),
    ],
)
def test_instantiate_linear_expression_from_dict(
    terms_dict: Dict[str, Term],
    constant: float,
    exp_terms: Dict[str, Term],
    exp_constant: float,
) -> None:
    expr = LinearExpression(terms_dict, constant)
    assert expr.terms == exp_terms
    assert expr.constant == exp_constant


@pytest.mark.parametrize(
    "expr, expected",
    [
        (LinearExpression(), True),
        (LinearExpression([]), True),
        (LinearExpression([], 0, {}), True),
        (LinearExpression([Term(1, "c", "x")], 0, {}), False),
        (LinearExpression([], 1, {}), False),
        (
            LinearExpression(
                [], 1, {PortFieldId("p", "f"): PortFieldTerm(1, "p", "f")}
            ),
            False,
        ),
    ],
)
def test_is_zero(expr: LinearExpression, expected: bool) -> None:
    assert expr.is_zero() == expected


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            LinearExpression([Term(10, "c", "x")], 1),
            LinearExpression([Term(5, "c", "x")], 2),
            LinearExpression([Term(15, "c", "x")], 3),
        ),
        (
            LinearExpression([Term(10, "c1", "x")], 1),
            LinearExpression([Term(5, "c2", "x")], 2),
            LinearExpression([Term(10, "c1", "x"), Term(5, "c2", "x")], 3),
        ),
        (
            LinearExpression([Term(10, "c", "x")], 0),
            LinearExpression([Term(5, "c", "y")], 0),
            LinearExpression([Term(10, "c", "x"), Term(5, "c", "y")], 0),
        ),
        (
            LinearExpression(),
            LinearExpression([Term(10, "c", "x", TimeShift(-1))]),
            LinearExpression([Term(10, "c", "x", TimeShift(-1))]),
        ),
        (
            LinearExpression(),
            LinearExpression(
                [Term(10, "c", "x", time_aggregator=TimeSum(stay_roll=True))]
            ),
            LinearExpression(
                [Term(10, "c", "x", time_aggregator=TimeSum(stay_roll=True))]
            ),
        ),
        (
            LinearExpression([Term(10, "c", "x")]),
            LinearExpression([Term(10, "c", "x", time_operator=TimeShift(-1))]),
            LinearExpression(
                [
                    Term(10, "c", "x"),
                    Term(10, "c", "x", time_operator=TimeShift(-1)),
                ]
            ),
        ),
        (
            LinearExpression([Term(10, "c", "x")]),
            LinearExpression(
                [
                    Term(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        scenario_aggregator=Expectation(),
                    )
                ]
            ),
            LinearExpression(
                [
                    Term(10, "c", "x"),
                    Term(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        scenario_aggregator=Expectation(),
                    ),
                ]
            ),
        ),
    ],
)
def test_addition(
    e1: LinearExpression,
    e2: LinearExpression,
    expected: LinearExpression,
) -> None:
    assert linear_expressions_equal(e1 + e2, expected)


def test_operation_that_leads_to_term_with_zero_coefficient_should_be_removed_from_terms() -> (
    None
):
    e1 = LinearExpression([Term(10, "c", "x")], 1)
    e2 = LinearExpression([Term(10, "c", "x")], 2)
    e3 = e2 - e1
    assert e3.terms == {}


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            LinearExpression([Term(10, "c", "x")], 3),
            LinearExpression([], 2),
            LinearExpression([Term(20, "c", "x")], 6),
        ),
        (
            LinearExpression([Term(10, "c", "x")], 3),
            LinearExpression([], 1),
            LinearExpression([Term(10, "c", "x")], 3),
        ),
        (
            LinearExpression([Term(10, "c", "x")], 3),
            LinearExpression(),
            LinearExpression(),
        ),
        (
            LinearExpression(
                [
                    Term(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        scenario_aggregator=Expectation(),
                    )
                ],
                3,
            ),
            LinearExpression([], 2),
            LinearExpression(
                [
                    Term(
                        20,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        scenario_aggregator=Expectation(),
                    )
                ],
                6,
            ),
        ),
    ],
)
def test_multiplication(
    e1: LinearExpression,
    e2: LinearExpression,
    expected: LinearExpression,
) -> None:
    assert linear_expressions_equal(e1 * e2, expected)
    assert linear_expressions_equal(e2 * e1, expected)


def test_multiplication_of_two_non_constant_terms_should_raise_value_error() -> None:
    e1 = LinearExpression([Term(10, "c", "x")], 0)
    e2 = LinearExpression([Term(5, "c", "x")], 0)
    with pytest.raises(ValueError) as exc:
        _ = e1 * e2
    assert str(exc.value) == "Cannot multiply two non constant expression"


@pytest.mark.parametrize(
    "e1, expected",
    [
        (
            LinearExpression([Term(10, "c", "x")], 5),
            LinearExpression([Term(-10, "c", "x")], -5),
        ),
        (
            LinearExpression(
                [
                    Term(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_aggregator=Expectation(),
                    )
                ],
                5,
            ),
            LinearExpression(
                [
                    Term(
                        -10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_aggregator=Expectation(),
                    )
                ],
                -5,
            ),
        ),
    ],
)
def test_negation(e1: LinearExpression, expected: LinearExpression) -> None:
    assert linear_expressions_equal(-e1, expected)


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            LinearExpression([Term(10, "c", "x")], 1),
            LinearExpression([Term(5, "c", "x")], 2),
            LinearExpression([Term(5, "c", "x")], -1),
        ),
        (
            LinearExpression([Term(10, "c1", "x")], 1),
            LinearExpression([Term(5, "c2", "x")], 2),
            LinearExpression([Term(10, "c1", "x"), Term(-5, "c2", "x")], -1),
        ),
        (
            LinearExpression([Term(10, "c", "x")], 0),
            LinearExpression([Term(5, "c", "y")], 0),
            LinearExpression([Term(10, "c", "x"), Term(-5, "c", "y")], 0),
        ),
        (
            LinearExpression(),
            LinearExpression([Term(10, "c", "x", time_operator=TimeShift(-1))]),
            LinearExpression([Term(-10, "c", "x", time_operator=TimeShift(-1))]),
        ),
        (
            LinearExpression(),
            LinearExpression(
                [Term(10, "c", "x", time_aggregator=TimeSum(stay_roll=True))]
            ),
            LinearExpression(
                [Term(-10, "c", "x", time_aggregator=TimeSum(stay_roll=True))]
            ),
        ),
        (
            LinearExpression([Term(10, "c", "x")]),
            LinearExpression([Term(10, "c", "x", time_operator=TimeShift(-1))]),
            LinearExpression(
                [
                    Term(10, "c", "x"),
                    Term(-10, "c", "x", time_operator=TimeShift(-1)),
                ]
            ),
        ),
        (
            LinearExpression([Term(10, "c", "x")]),
            LinearExpression(
                [
                    Term(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_aggregator=Expectation(),
                    )
                ]
            ),
            LinearExpression(
                [
                    Term(10, "c", "x"),
                    Term(
                        -10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_aggregator=Expectation(),
                    ),
                ]
            ),
        ),
    ],
)
def test_substraction(
    e1: LinearExpression,
    e2: LinearExpression,
    expected: LinearExpression,
) -> None:
    assert linear_expressions_equal(e1 - e2, expected)


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            LinearExpression([Term(10, "c", "x")], 15),
            LinearExpression([], 5),
            LinearExpression([Term(2, "c", "x")], 3),
        ),
        (
            LinearExpression([Term(10, "c", "x")], 15),
            LinearExpression([], 1),
            LinearExpression([Term(10, "c", "x")], 15),
        ),
        (
            LinearExpression(
                [
                    Term(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_aggregator=Expectation(),
                    )
                ],
                15,
            ),
            LinearExpression([], 5),
            LinearExpression(
                [
                    Term(
                        2,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_aggregator=Expectation(),
                    )
                ],
                3,
            ),
        ),
    ],
)
def test_division(
    e1: LinearExpression,
    e2: LinearExpression,
    expected: LinearExpression,
) -> None:
    assert linear_expressions_equal(e1 / e2, expected)


def test_division_by_zero_sould_raise_zero_division_error() -> None:
    e1 = LinearExpression([Term(10, "c", "x")], 15)
    e2 = LinearExpression()
    with pytest.raises(ZeroDivisionError) as exc:
        _ = e1 / e2
    assert str(exc.value) == "Cannot divide expression by zero"


def test_division_by_non_constant_expr_sould_raise_value_error() -> None:
    e1 = LinearExpression([Term(10, "c", "x")], 15)
    e2 = LinearExpression()
    with pytest.raises(ValueError) as exc:
        _ = e2 / e1
    assert str(exc.value) == "Cannot divide by a non constant expression"


def test_imul_preserve_identity() -> None:
    # technical test to check the behaviour of reassigning "self" in imul operator:
    # it did not preserve identity, which could lead to weird behaviour
    e1 = LinearExpression([], 15)
    e2 = e1
    e1 *= LinearExpression([], 2)
    assert linear_expressions_equal(e1, LinearExpression([], 30))
    assert linear_expressions_equal(e2, e1)
    assert e2 is e1
