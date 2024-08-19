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

from andromede.expression.evaluate import EvaluationContext
from andromede.expression.expression_efficient import param
from andromede.expression.indexing_structure import RowIndex
from andromede.expression.linear_expression_efficient import (
    literal,
    var,
    wrap_in_linear_expr,
)


def test_large_number_of_parameters_sum() -> None:
    """
    Test performance when the problem involves an expression with a high number of terms.

    This test pass with 476 terms but fails with 477 locally due to recursion depth, and even less terms are possible with Jenkins...
    """
    nb_terms = 500

    parameters_value = {}
    for i in range(1, nb_terms):
        parameters_value[f"cost_{i}"] = 1 / i

    # Still the recursion depth error with parameters
    with pytest.raises(RecursionError, match="maximum recursion depth exceeded"):
        expr = sum(wrap_in_linear_expr(param(f"cost_{i}")) for i in range(1, nb_terms))
        expr.evaluate(EvaluationContext(parameters=parameters_value), RowIndex(0, 0))


def test_large_number_of_identical_parameters_sum() -> None:
    """
    With identical parameters sum, a simplification is performed online to avoid the recursivity.
    """
    nb_terms = 500

    parameters_value = {"cost": 1.0}

    # Still the recursion depth error with parameters
    # with pytest.raises(RecursionError, match="maximum recursion depth exceeded"):
    expr = sum(wrap_in_linear_expr(param("cost")) for _ in range(nb_terms))
    assert (
        expr.evaluate(EvaluationContext(parameters=parameters_value), RowIndex(0, 0))
        == nb_terms
    )


def test_large_number_of_literal_sum() -> None:
    """
    Literal sums are computed online to avoid recursivity
    """
    nb_terms = 500

    # # Still the recursion depth error with parameters
    # with pytest.raises(RecursionError, match="maximum recursion depth exceeded"):
    expr = sum(wrap_in_linear_expr(literal(1)) for _ in range(nb_terms))
    assert expr.evaluate(EvaluationContext(), RowIndex(0, 0)) == nb_terms


def test_large_number_of_variables_sum() -> None:
    """
    Test performance when the problem involves an expression with a high number of terms. No problem when there is a large number of variables as this is derecusified.
    """
    nb_terms = 500

    variables_value = {}
    for i in range(1, nb_terms):
        variables_value[f"cost_{i}"] = 1 / i

    expr = sum(var(f"cost_{i}") for i in range(1, nb_terms))
    assert expr.evaluate(
        EvaluationContext(variables=variables_value), RowIndex(0, 0)
    ) == sum(1 / i for i in range(1, nb_terms))
