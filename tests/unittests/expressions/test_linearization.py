import pytest
from unittests.expressions.test_expressions import StructureProvider

from andromede.expression import param, var
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
