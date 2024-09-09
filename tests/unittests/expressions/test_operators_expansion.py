from andromede.expression import ExpressionNode, LiteralNode
from andromede.expression.equality import expressions_equal
from andromede.expression.expression import (
    comp_param,
    comp_var,
    problem_param,
    problem_var,
)
from andromede.expression.operators_expansion import expand_operators

P = comp_param("c", "p")
X = comp_var("c", "x")


def P_at(timestep: int = 1, scenario: int = 1):
    return problem_param("c", "p", timestep, scenario)


def X_at(timestep: int = 1, scenario: int = 1):
    return problem_var("c", "x", timestep, scenario)


def evaluate_literal(node: ExpressionNode) -> int:
    if isinstance(node, LiteralNode):
        return int(node.value)
    raise NotImplementedError("Can only evaluate literal nodes.")


def test_all_time_sum_expansion():
    expr = X.time_sum()

    expanded = expand_operators(expr, 1, 1, 2, 1, evaluate_literal)
    assert expressions_equal(expanded, X_at(timestep=1) + X_at(timestep=2))


def test_shift_expansion():
    expr = X.shift(-1)

    expanded = expand_operators(expr, 1, 1, 2, 1, evaluate_literal)
    expected = X_at(timestep=0)
    assert expressions_equal(expanded, expected)


def test_time_sum_expansion():
    expr = X.time_sum(-2, 0)

    expanded = expand_operators(expr, 3, 1, 2, 1, evaluate_literal)
    expected = X_at(timestep=1) + (X_at(timestep=2) + X_at(timestep=3))
    assert expressions_equal(expanded, expected)


def test_shift_expansion_on_expression():
    expr = (P * X).shift(-1)

    expanded = expand_operators(expr, 1, 1, 2, 1, evaluate_literal)
    expected = P_at(timestep=0) * X_at(timestep=0)
    assert expressions_equal(expanded, expected)


def test_sum_expansion_on_complex_expression():
    expr = P * (P * X).time_sum(-1, 0)

    expanded = expand_operators(expr, 1, 1, 2, 1, evaluate_literal)
    expected = P_at(timestep=1) * (
        P_at(timestep=0) * X_at(timestep=0) + P_at(timestep=1) * X_at(timestep=1)
    )
    assert expressions_equal(expanded, expected)


def test_expansion_on_nested_operators():
    expr = X.shift(-1).shift(+1)

    expanded = expand_operators(expr, 1, 1, 2, 1, evaluate_literal)
    expected = X_at(1)
    assert expressions_equal(expanded, expected)
