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

from andromede.expression.linear_expression_efficient import (
    LinearExpressionEfficient,
    TermEfficient,
)
from andromede.expression.scenario_operator import Expectation
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
    "coeff, var_name, constant, expec_str",
    [
        (0, "x", 0, "0"),
        (1, "x", 0, "+x"),
        (1, "x", 1, "+x+1"),
        (3.7, "x", 1, "+3.7x+1"),
        (0, "x", 1, "+1"),
    ],
)
def test_affine_expression_printing_should_reflect_required_formatting(
    coeff: float, var_name: str, constant: float, expec_str: str
) -> None:
    expr = LinearExpressionEfficient([TermEfficient(coeff, "c", var_name)], constant)
    assert str(expr) == expec_str


@pytest.mark.parametrize(
    "lhs, rhs",
    [
        (
            LinearExpressionEfficient([], 1) + LinearExpressionEfficient([], 3),
            LinearExpressionEfficient([], 4),
        ),
        (
            LinearExpressionEfficient([], 4) / LinearExpressionEfficient([], 2),
            LinearExpressionEfficient([], 2),
        ),
        (
            LinearExpressionEfficient([], 4) * LinearExpressionEfficient([], 2),
            LinearExpressionEfficient([], 8),
        ),
        (
            LinearExpressionEfficient([], 4) - LinearExpressionEfficient([], 2),
            LinearExpressionEfficient([], 2),
        ),
    ],
)
def test_constant_expressions(
    lhs: LinearExpressionEfficient, rhs: LinearExpressionEfficient
) -> None:
    assert lhs == rhs


@pytest.mark.parametrize(
    "terms_dict, constant, exp_terms, exp_constant",
    [
        ({"x": TermEfficient(0, "c", "x")}, 1, {}, 1),
        ({"x": TermEfficient(1, "c", "x")}, 1, {"x": TermEfficient(1, "c", "x")}, 1),
    ],
)
def test_instantiate_linear_expression_from_dict(
    terms_dict: Dict[str, TermEfficient],
    constant: float,
    exp_terms: Dict[str, TermEfficient],
    exp_constant: float,
) -> None:
    expr = LinearExpressionEfficient(terms_dict, constant)
    assert expr.terms == exp_terms
    assert expr.constant == exp_constant


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 1),
            LinearExpressionEfficient([TermEfficient(5, "c", "x")], 2),
            LinearExpressionEfficient([TermEfficient(15, "c", "x")], 3),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c1", "x")], 1),
            LinearExpressionEfficient([TermEfficient(5, "c2", "x")], 2),
            LinearExpressionEfficient(
                [TermEfficient(10, "c1", "x"), TermEfficient(5, "c2", "x")], 3
            ),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 0),
            LinearExpressionEfficient([TermEfficient(5, "c", "y")], 0),
            LinearExpressionEfficient(
                [TermEfficient(10, "c", "x"), TermEfficient(5, "c", "y")], 0
            ),
        ),
        (
            LinearExpressionEfficient(),
            LinearExpressionEfficient([TermEfficient(10, "c", "x", TimeShift(-1))]),
            LinearExpressionEfficient([TermEfficient(10, "c", "x", TimeShift(-1))]),
        ),
        (
            LinearExpressionEfficient(),
            LinearExpressionEfficient(
                [TermEfficient(10, "c", "x", time_aggregator=TimeSum(stay_roll=True))]
            ),
            LinearExpressionEfficient(
                [TermEfficient(10, "c", "x", time_aggregator=TimeSum(stay_roll=True))]
            ),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")]),
            LinearExpressionEfficient(
                [TermEfficient(10, "c", "x", time_operator=TimeShift(-1))]
            ),
            LinearExpressionEfficient(
                [
                    TermEfficient(10, "c", "x"),
                    TermEfficient(10, "c", "x", time_operator=TimeShift(-1)),
                ]
            ),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")]),
            LinearExpressionEfficient(
                [
                    TermEfficient(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        scenario_operator=Expectation(),
                    )
                ]
            ),
            LinearExpressionEfficient(
                [
                    TermEfficient(10, "c", "x"),
                    TermEfficient(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        scenario_operator=Expectation(),
                    ),
                ]
            ),
        ),
    ],
)
def test_addition(
    e1: LinearExpressionEfficient,
    e2: LinearExpressionEfficient,
    expected: LinearExpressionEfficient,
) -> None:
    assert e1 + e2 == expected


def test_addition_of_linear_expressions_with_different_number_of_instances_should_raise_value_error() -> (
    None
):
    pass


def test_operation_that_leads_to_term_with_zero_coefficient_should_be_removed_from_terms() -> (
    None
):
    e1 = LinearExpressionEfficient([TermEfficient(10, "c", "x")], 1)
    e2 = LinearExpressionEfficient([TermEfficient(10, "c", "x")], 2)
    e3 = e2 - e1
    assert e3.terms == {}


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 3),
            LinearExpressionEfficient([], 2),
            LinearExpressionEfficient([TermEfficient(20, "c", "x")], 6),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 3),
            LinearExpressionEfficient([], 1),
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 3),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 3),
            LinearExpressionEfficient(),
            LinearExpressionEfficient(),
        ),
        (
            LinearExpressionEfficient(
                [
                    TermEfficient(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        scenario_operator=Expectation(),
                    )
                ],
                3,
            ),
            LinearExpressionEfficient([], 2),
            LinearExpressionEfficient(
                [
                    TermEfficient(
                        20,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        scenario_operator=Expectation(),
                    )
                ],
                6,
            ),
        ),
    ],
)
def test_multiplication(
    e1: LinearExpressionEfficient,
    e2: LinearExpressionEfficient,
    expected: LinearExpressionEfficient,
) -> None:
    assert e1 * e2 == expected
    assert e2 * e1 == expected


def test_multiplication_of_two_non_constant_terms_should_raise_value_error() -> None:
    e1 = LinearExpressionEfficient([TermEfficient(10, "c", "x")], 0)
    e2 = LinearExpressionEfficient([TermEfficient(5, "c", "x")], 0)
    with pytest.raises(ValueError) as exc:
        _ = e1 * e2
    assert str(exc.value) == "Cannot multiply two non constant expression"


@pytest.mark.parametrize(
    "e1, expected",
    [
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 5),
            LinearExpressionEfficient([TermEfficient(-10, "c", "x")], -5),
        ),
        (
            LinearExpressionEfficient(
                [
                    TermEfficient(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_operator=Expectation(),
                    )
                ],
                5,
            ),
            LinearExpressionEfficient(
                [
                    TermEfficient(
                        -10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_operator=Expectation(),
                    )
                ],
                -5,
            ),
        ),
    ],
)
def test_negation(
    e1: LinearExpressionEfficient, expected: LinearExpressionEfficient
) -> None:
    assert -e1 == expected


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 1),
            LinearExpressionEfficient([TermEfficient(5, "c", "x")], 2),
            LinearExpressionEfficient([TermEfficient(5, "c", "x")], -1),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c1", "x")], 1),
            LinearExpressionEfficient([TermEfficient(5, "c2", "x")], 2),
            LinearExpressionEfficient(
                [TermEfficient(10, "c1", "x"), TermEfficient(-5, "c2", "x")], -1
            ),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 0),
            LinearExpressionEfficient([TermEfficient(5, "c", "y")], 0),
            LinearExpressionEfficient(
                [TermEfficient(10, "c", "x"), TermEfficient(-5, "c", "y")], 0
            ),
        ),
        (
            LinearExpressionEfficient(),
            LinearExpressionEfficient(
                [TermEfficient(10, "c", "x", time_operator=TimeShift(-1))]
            ),
            LinearExpressionEfficient(
                [TermEfficient(-10, "c", "x", time_operator=TimeShift(-1))]
            ),
        ),
        (
            LinearExpressionEfficient(),
            LinearExpressionEfficient(
                [TermEfficient(10, "c", "x", time_aggregator=TimeSum(stay_roll=True))]
            ),
            LinearExpressionEfficient(
                [TermEfficient(-10, "c", "x", time_aggregator=TimeSum(stay_roll=True))]
            ),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")]),
            LinearExpressionEfficient(
                [TermEfficient(10, "c", "x", time_operator=TimeShift(-1))]
            ),
            LinearExpressionEfficient(
                [
                    TermEfficient(10, "c", "x"),
                    TermEfficient(-10, "c", "x", time_operator=TimeShift(-1)),
                ]
            ),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")]),
            LinearExpressionEfficient(
                [
                    TermEfficient(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_operator=Expectation(),
                    )
                ]
            ),
            LinearExpressionEfficient(
                [
                    TermEfficient(10, "c", "x"),
                    TermEfficient(
                        -10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_operator=Expectation(),
                    ),
                ]
            ),
        ),
    ],
)
def test_substraction(
    e1: LinearExpressionEfficient,
    e2: LinearExpressionEfficient,
    expected: LinearExpressionEfficient,
) -> None:
    assert e1 - e2 == expected


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 15),
            LinearExpressionEfficient([], 5),
            LinearExpressionEfficient([TermEfficient(2, "c", "x")], 3),
        ),
        (
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 15),
            LinearExpressionEfficient([], 1),
            LinearExpressionEfficient([TermEfficient(10, "c", "x")], 15),
        ),
        (
            LinearExpressionEfficient(
                [
                    TermEfficient(
                        10,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_operator=Expectation(),
                    )
                ],
                15,
            ),
            LinearExpressionEfficient([], 5),
            LinearExpressionEfficient(
                [
                    TermEfficient(
                        2,
                        "c",
                        "x",
                        time_operator=TimeShift(-1),
                        time_aggregator=TimeSum(False),
                        scenario_operator=Expectation(),
                    )
                ],
                3,
            ),
        ),
    ],
)
def test_division(
    e1: LinearExpressionEfficient,
    e2: LinearExpressionEfficient,
    expected: LinearExpressionEfficient,
) -> None:
    assert e1 / e2 == expected


def test_division_by_zero_sould_raise_zero_division_error() -> None:
    e1 = LinearExpressionEfficient([TermEfficient(10, "c", "x")], 15)
    e2 = LinearExpressionEfficient()
    with pytest.raises(ZeroDivisionError) as exc:
        _ = e1 / e2
    assert str(exc.value) == "Cannot divide expression by zero"


def test_division_by_non_constant_expr_sould_raise_value_error() -> None:
    e1 = LinearExpressionEfficient([TermEfficient(10, "c", "x")], 15)
    e2 = LinearExpressionEfficient()
    with pytest.raises(ValueError) as exc:
        _ = e2 / e1
    assert str(exc.value) == "Cannot divide by a non constant expression"


def test_imul_preserve_identity() -> None:
    # technical test to check the behaviour of reassigning "self" in imul operator:
    # it did not preserve identity, which could lead to weird behaviour
    e1 = LinearExpressionEfficient([], 15)
    e2 = e1
    e1 *= LinearExpressionEfficient([], 2)
    assert e1 == LinearExpressionEfficient([], 30)
    assert e2 == e1
    assert e2 is e1
