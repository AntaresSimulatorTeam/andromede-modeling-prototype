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

import re
from typing import Optional, Type

import pytest

from andromede.expression.expression import ExpressionRange, comp_param, param
from andromede.expression.linear_expression import (
    LinearExpression,
    comp_var,
    linear_expressions_equal,
    literal,
    port_field,
    var,
    wrap_in_linear_expr,
)
from andromede.model import Constraint, float_variable, model
from andromede.model.model import port_field_def


@pytest.mark.parametrize(
    "name, expression, lb, ub, exp_name, exp_expr, exp_lb, exp_ub",
    [
        (
            "my_constraint",
            2 * var("my_var"),
            literal(5),
            literal(10),
            "my_constraint",
            2 * var("my_var"),
            wrap_in_linear_expr(literal(5)),
            wrap_in_linear_expr(literal(10)),
        ),
        (
            "my_constraint",
            2 * var("my_var"),
            None,
            literal(10),
            "my_constraint",
            2 * var("my_var"),
            wrap_in_linear_expr(literal(-float("inf"))),
            wrap_in_linear_expr(literal(10)),
        ),
        (
            "my_constraint",
            2 * var("my_var"),
            literal(5),
            None,
            "my_constraint",
            2 * var("my_var"),
            wrap_in_linear_expr(literal(5)),
            wrap_in_linear_expr(literal(float("inf"))),
        ),
        (
            "my_constraint",
            2 * var("my_var"),
            None,
            None,
            "my_constraint",
            2 * var("my_var"),
            wrap_in_linear_expr(literal(-float("inf"))),
            wrap_in_linear_expr(literal(float("inf"))),
        ),
        (
            "my_constraint",
            2 * var("my_var") <= param("p"),
            None,
            None,
            "my_constraint",
            2 * var("my_var") - param("p"),
            wrap_in_linear_expr(literal(-float("inf"))),
            wrap_in_linear_expr(literal(0)),
        ),
        (
            "my_constraint",
            2 * var("my_var") >= param("p"),
            None,
            None,
            "my_constraint",
            2 * var("my_var") - param("p"),
            wrap_in_linear_expr(literal(0)),
            wrap_in_linear_expr(literal(float("inf"))),
        ),
        (
            "my_constraint",
            2 * var("my_var") == param("p"),
            None,
            None,
            "my_constraint",
            2 * var("my_var") - param("p"),
            wrap_in_linear_expr(literal(0)),
            wrap_in_linear_expr(literal(0)),
        ),
        (
            "my_constraint",
            2 * var("my_var").expec() == param("p"),
            None,
            None,
            "my_constraint",
            2 * var("my_var").expec() - param("p"),
            wrap_in_linear_expr(literal(0)),
            wrap_in_linear_expr(literal(0)),
        ),
        (
            "my_constraint",
            2 * var("my_var").shift(-1) == param("p"),
            None,
            None,
            "my_constraint",
            2 * var("my_var").shift(-1) - param("p"),
            wrap_in_linear_expr(literal(0)),
            wrap_in_linear_expr(literal(0)),
        ),
    ],
)
def test_constraint_instantiation(
    name: str,
    expression: LinearExpression,
    lb: Optional[LinearExpression],
    ub: Optional[LinearExpression],
    exp_name: str,
    exp_expr: LinearExpression,
    exp_lb: LinearExpression,
    exp_ub: LinearExpression,
) -> None:
    if lb is None and ub is None:
        constraint = Constraint(name, expression)
    elif lb is None:
        constraint = Constraint(name, expression, upper_bound=ub)
    elif ub is None:
        constraint = Constraint(name, expression, lower_bound=lb)
    else:
        constraint = Constraint(name, expression, lower_bound=lb, upper_bound=ub)

    assert constraint.name == exp_name
    assert linear_expressions_equal(constraint.expression, exp_expr)
    assert linear_expressions_equal(constraint.lower_bound, exp_lb)
    assert linear_expressions_equal(constraint.upper_bound, exp_ub)


def test_if_both_comparison_expression_and_bound_given_for_constraint_init_then_it_should_raise_a_value_error() -> (
    None
):
    with pytest.raises(ValueError) as exc:
        Constraint("my_constraint", 2 * var("my_var") == param("my_param"), literal(2))
    assert (
        str(exc.value)
        == "Both comparison between two expressions and a bound are specfied, set either only a comparison between expressions or a single linear expression with bounds."
    )


def test_if_a_bound_is_not_constant_then_it_should_raise_a_value_error() -> None:
    with pytest.raises(ValueError) as exc:
        Constraint("my_constraint", 2 * var("my_var"), var("x"))
    assert (
        str(exc.value)
        == "The bounds of a constraint should not contain variables, +x was given."
    )


def test_writing_p_min_max_constraint_should_not_raise_exception() -> None:
    """
    Aim at representing the following mathematical constraints:
    For all t, p_min <= p[t] <= p_max * alpha[t] where p_min, p_max are literal paramters and alpha is an input timeseries
    """
    try:
        p_min = literal(5)
        p_max = literal(10)
        p = var("p")

        alpha = param("alpha")

        _ = Constraint("generation bounds", p, p_min, p_max * alpha)

    # Later on, the goal is to assert that when this constraint is sent to the solver, it correctly builds: for all t, p_min <= p[k,t,w] <= p_max * alpha[k,t,w]

    except Exception as exc:
        assert False, f"Writing p_min and p_max constraints raises an exception: {exc}"


def test_writing_min_up_constraint_should_not_raise_exception() -> None:
    """
    Aim at representing the following mathematical constraints:
    For all t, for all t' in [t+1, t+d_min_up], off_on[k,t,w] <= on[k,t',w]
    """
    try:
        d_min_up = 3
        off_on = var("off_on")
        on = var("on")

        _ = Constraint(
            "min_up_time",
            off_on <= on.sum(shift=ExpressionRange(1, d_min_up)),
        )

        # Later on, the goal is to assert that when this constraint is sent to the solver, it correctly builds: for all t, for all t' in [t+1, t+d_min_up], off_on[k,t,w] <= on[k,t',w]

    except Exception as exc:
        assert False, f"Writing min_up constraints raises an exception: {exc}"


@pytest.mark.skip(reason="Variance not implemented")
def test_instantiating_a_model_with_non_linear_scenario_operator_in_the_objective_should_raise_type_error() -> (
    None
):
    with pytest.raises(ValueError) as exc:
        _ = model(
            id="model_with_non_linear_op",
            variables=[float_variable("generation")],
            objective_operational_contribution=var("generation").variance(),
        )
    assert str(exc.value) == "Objective contribution must be a linear expression."


@pytest.mark.parametrize(
    "expression, error_type, error_msg",
    [
        (
            var("x") <= 0,
            TypeError,
            "Unable to wrap  + (-inf) <= +x <= 0 into a linear expression",
        ),
        (
            comp_var("c", "x"),
            ValueError,
            "Port definition must not contain a variable associated to a component.",
        ),
        (
            comp_param("c", "x"),
            ValueError,
            "Port definition must not contain a parameter associated to a component.",
        ),
        (
            port_field("p", "f"),
            ValueError,
            "Port definition cannot reference another port field.",
        ),
        (
            port_field("p", "f").sum_connections(),
            ValueError,
            "Port definition cannot reference another port field.",
        ),
    ],
)
def test_invalid_port_field_definition_should_raise(
    expression: LinearExpression, error_type: Type, error_msg: str
) -> None:
    with pytest.raises(error_type, match=re.escape(error_msg)):
        port_field_def(port_name="p", field_name="f", definition=expression)


def test_constraint_equals() -> None:
    # checks in particular that expressions are correctly compared
    assert Constraint(name="c", expression_init=var("x") <= param("p")) == Constraint(
        name="c", expression_init=var("x") <= param("p")
    )
    assert Constraint(name="c", expression_init=var("x") <= param("p")) != Constraint(
        name="c", expression_init=var("y") <= param("p")
    )
