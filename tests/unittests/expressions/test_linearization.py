import pytest
from unittests.expressions.test_expressions import (
    ComponentEvaluationContext,
    StructureProvider,
)

from andromede.expression import ExpressionNode, param, var
from andromede.expression.expression import comp_var
from andromede.simulation.linear_expression import LinearExpression, Term
from andromede.simulation.linearize import linearize_expression


def test_linearization() -> None:
    x = comp_var("c", "x")
    expr = (5 * x + 3) / 2
    provider = StructureProvider()

    assert linearize_expression(expr, provider) == LinearExpression(
        [Term(2.5, "c", "x")], 1.5
    )

    with pytest.raises(ValueError):
        linearize_expression(param("p") * x, provider)


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


@pytest.mark.parametrize(
    "expr",
    [
        (comp_var("c", "x").shift(-1).shift(+1),),
        (comp_var("c", "x").shift(-1).time_sum(),),
        (comp_var("c", "x").shift(-1).time_sum(-2, +2),),
        (comp_var("c", "x").time_sum().shift(-1),),
        (comp_var("c", "x").time_sum(-2, +2).shift(-1),),
        (comp_var("c", "x").eval(2).time_sum(),),
    ],
)
def test_linearization_of_nested_time_operations_should_raise_value_error(
    expr: ExpressionNode,
) -> None:
    x = comp_var("c", "x")

    structure_provider = StructureProvider()
    value_provider = ComponentEvaluationContext()
    with pytest.raises(ValueError, match="not supported"):
        linearize_expression(x.shift(-1).shift(+1), structure_provider, value_provider)
