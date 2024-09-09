from unittest.mock import Mock

import pytest

from andromede.expression import ExpressionNode, var, LiteralNode
from andromede.expression.expression import (
    comp_var,
    comp_param,
    ComponentVariableNode,
)
from andromede.expression.operators_expansion import (
    expand_operators,
    ProblemDimensions,
    ProblemIndex,
)
from andromede.simulation.linear_expression import (
    LinearExpression,
    Term,
)
from andromede.simulation.linearize import linearize_expression, ParameterGetter
from unittests.expressions.test_expressions import (
    StructureProvider,
)

P = comp_param("c", "p")
X = comp_var("c", "x")
Y = comp_var("c", "y")


def var_at(var: ComponentVariableNode, timestep, scenario) -> LinearExpression:
    return LinearExpression(
        terms=[
            Term(
                1,
                var.component_id,
                var.name,
                time_index=timestep,
                scenario_index=scenario,
            )
        ],
        constant=0,
    )


def X_at(t: int = 0, s: int = 0) -> LinearExpression:
    return var_at(X, timestep=t, scenario=s)


def Y_at(t: int = 0, s: int = 0) -> LinearExpression:
    return var_at(Y, timestep=t, scenario=s)


def constant(c: float) -> LinearExpression:
    return LinearExpression([], c)


def evaluate_literal(node: ExpressionNode) -> int:
    if isinstance(node, LiteralNode):
        return int(node.value)
    raise NotImplementedError("Can only evaluate literal nodes.")


def test_linearization_of_non_linear_expressions_should_raise_value_error() -> None:
    x = var("x")
    expr = x.variance()

    provider = StructureProvider()
    with pytest.raises(ValueError) as exc:
        linearize_expression(expr, provider)
    assert (
        str(exc.value)
        == "Cannot linearize expression with a non-linear operator: Variance"
    )


def _expand_and_linearize(
    expr: ExpressionNode,
    dimensions: ProblemDimensions,
    index: ProblemIndex,
    parameter_value_provider: ParameterGetter,
) -> LinearExpression:
    expanded = expand_operators(expr, dimensions, evaluate_literal)
    return linearize_expression(
        expanded, index.timestep, index.scenario, parameter_value_provider
    )


@pytest.mark.parametrize(
    "expr,expected",
    [
        ((5 * X + 3) / 2, constant(2.5) * X_at(t=0) + constant(1.5)),
        ((X + Y).time_sum(), X_at(t=0) + Y_at(t=0) + X_at(t=1) + Y_at(t=1)),
        (X.shift(-1).shift(+1), X_at(t=0)),
        (X.shift(-1).time_sum(), X_at(t=-1) + X_at(t=0)),
        (X.shift(-1).time_sum(-1, +1), X_at(t=-2) + X_at(t=-1) + X_at(t=0)),
        (X.time_sum().shift(-1), X_at(t=-1) + X_at(t=0)),
        (X.time_sum(-1, +1).shift(-1), X_at(t=-2) + X_at(t=-1) + X_at(t=0)),
        (X.eval(2).time_sum(), X_at(t=2) + X_at(t=2)),
        ((X + 2).time_sum(), X_at(t=0) + X_at(t=1) + constant(4)),
        ((X + 2).time_sum(-1, 0), X_at(t=-1) + X_at(t=0) + constant(4)),
        ((X + 2).time_sum(-1, 0), X_at(t=-1) + X_at(t=0) + constant(4)),
    ],
)
def test_linearization_of_nested_time_operations(
    expr: ExpressionNode, expected: LinearExpression
) -> None:
    dimensions = ProblemDimensions(timesteps_count=2, scenarios_count=1)
    index = ProblemIndex(timestep=0, scenario=0)
    params = Mock(spec=ParameterGetter)

    assert _expand_and_linearize(expr, dimensions, index, params) == expected


# def test_expansion_and_linearization():
#     param_provider = ComponentEvaluationContext()
#     with pytest.raises(ValueError):
#         linearize_expression(expr, structure_provider, value_provider)
