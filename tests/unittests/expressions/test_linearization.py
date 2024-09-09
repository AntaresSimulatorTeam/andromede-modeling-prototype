import pytest

from andromede.expression import ExpressionNode, param, var
from andromede.expression.expression import comp_var
from andromede.simulation.linear_expression import (
    AllTimeExpansion,
    LinearExpression,
    Term,
)
from andromede.simulation.linearize import linearize_expression

from .test_expressions import ComponentEvaluationContext, StructureProvider


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


def test_time_sum_is_distributed_on_expression() -> None:
    x = comp_var("c", "x")
    y = comp_var("c", "y")
    expr = (x + y).time_sum()
    provider = StructureProvider()

    assert linearize_expression(expr, provider) == LinearExpression(
        [
            Term(1, "c", "x", time_expansion=AllTimeExpansion()),
            Term(1, "c", "y", time_expansion=AllTimeExpansion()),
        ],
        0,
    )


@pytest.mark.skip(reason="Not yet supported")
def test_time_sum_is_distributed_on_expression() -> None:
    x = comp_var("c", "x")
    y = comp_var("c", "y")
    expr = (x + y).time_sum()
    provider = StructureProvider()

    assert linearize_expression(expr, provider) == LinearExpression(
        [
            Term(1, "c", "x", time_expansion=AllTimeExpansion()),
            Term(1, "c", "y", time_expansion=AllTimeExpansion()),
        ],
        0,
    )


def test_linearize_time_sum_on_expression() -> None:
    x = comp_var("c", "x")
    y = comp_var("c", "y")
    expr = (x + y).time_sum()
    provider = StructureProvider()

    assert linearize_expression(expr, provider) == LinearExpression(
        [
            Term(1, "c", "x", time_expansion=AllTimeExpansion()),
            Term(1, "c", "y", time_expansion=AllTimeExpansion()),
        ],
        0,
    )


X = comp_var("c", "x")


@pytest.mark.parametrize(
    "expr",
    [(X + 2).time_sum(), (X + 2).time_sum(-1, 2)],
)
def test_sum_of_constant_not_supported(
    expr: ExpressionNode,
) -> None:
    structure_provider = StructureProvider()
    value_provider = ComponentEvaluationContext()
    with pytest.raises(ValueError):
        linearize_expression(expr, structure_provider, value_provider)


@pytest.mark.parametrize(
    "expr",
    [
        X.shift(-1).shift(+1),
        X.shift(-1).time_sum(),
        X.shift(-1).time_sum(-2, +2),
        X.time_sum().shift(-1),
        X.time_sum(-2, +2).shift(-1),
        X.eval(2).time_sum(),
    ],
)
def test_linearization_of_nested_time_operations_should_raise_value_error(
    expr: ExpressionNode,
) -> None:
    structure_provider = StructureProvider()
    value_provider = ComponentEvaluationContext()
    with pytest.raises(ValueError):
        linearize_expression(expr, structure_provider, value_provider)
