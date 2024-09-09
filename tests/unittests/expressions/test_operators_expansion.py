import pytest

from andromede.expression import ExpressionNode, LiteralNode
from andromede.expression.equality import expressions_equal
from andromede.expression.expression import (
    comp_param,
    comp_var,
    problem_param,
    problem_var,
    TimeStep,
    TimeShift,
    NoScenarioIndex,
)
from andromede.expression.operators_expansion import (
    expand_operators,
    ProblemDimensions,
)

P = comp_param("c", "p")
X = comp_var("c", "x")


def shifted_P(t: int = 0):
    return problem_param("c", "p", TimeShift(t), NoScenarioIndex())


def P_at(t: int = 0):
    return problem_param("c", "p", TimeStep(t), NoScenarioIndex())


def X_at(t: int = 0):
    return problem_var("c", "x", TimeStep(t), NoScenarioIndex())


def shifted_X(t: int = 0):
    return problem_var("c", "x", TimeShift(t), NoScenarioIndex())


def evaluate_literal(node: ExpressionNode) -> int:
    if isinstance(node, LiteralNode):
        return int(node.value)
    raise NotImplementedError("Can only evaluate literal nodes.")


@pytest.mark.parametrize(
    "expr,expected",
    [
        (X.time_sum(), X_at(0) + X_at(1)),
        (X.shift(-1), shifted_X(-1)),
        (X.time_sum(-2, 0), shifted_X(-2) + (shifted_X(-1) + shifted_X(0))),
        ((P * X).shift(-1), shifted_P(-1) * shifted_X(-1)),
        (X.shift(-1).shift(+1), shifted_X(0)),
        (
            P * (P * X).time_sum(0, 1),
            shifted_P(0) * (shifted_P(0) * shifted_X(0) + shifted_P(1) * shifted_X(1)),
        ),
        (X.eval(2).time_sum(), X_at(2) + X_at(2)),
    ],
)
def test_operators_expansion(expr: ExpressionNode, expected: ExpressionNode) -> None:
    expanded = expand_operators(
        expr, ProblemDimensions(2, 1), evaluate_literal
    )
    assert expressions_equal(expanded, expected)
