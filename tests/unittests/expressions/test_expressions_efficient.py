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
from dataclasses import dataclass, field
from typing import Dict

import pytest

from andromede.expression.equality import expressions_equal
from andromede.expression.evaluate import EvaluationContext, ValueProvider
from andromede.expression.expression import (
    ComponentParameterNode,
    ExpressionNodeEfficient,
    ExpressionRange,
    InstancesTimeIndex,
    LiteralNode,
    ParameterNode,
    TimeAggregatorName,
    TimeAggregatorNode,
    TimeOperatorName,
    TimeOperatorNode,
    comp_param,
    literal,
    param,
)
from andromede.expression.indexing import IndexingStructureProvider
from andromede.expression.indexing_structure import IndexingStructure, RowIndex
from andromede.expression.linear_expression import (
    LinearExpressionEfficient,
    StandaloneConstraint,
    TermEfficient,
    TermKeyEfficient,
    comp_var,
    linear_expressions_equal,
    sum_expressions,
    var,
    wrap_in_linear_expr,
)
from andromede.expression.time_operator import TimeEvaluation, TimeShift, TimeSum
from andromede.expression.value_provider import TimeScenarioIndex, TimeScenarioIndices


@dataclass(frozen=True)
class ComponentValueKey:
    component_id: str
    variable_name: str


def comp_key(component_id: str, variable_name: str) -> ComponentValueKey:
    return ComponentValueKey(component_id, variable_name)


@dataclass(frozen=True)
class ComponentEvaluationContext(ValueProvider):
    """
    Simple value provider relying on dictionaries.
    Does not support component variables/parameters.
    """

    variables: Dict[ComponentValueKey, float] = field(default_factory=dict)
    parameters: Dict[ComponentValueKey, float] = field(default_factory=dict)

    def get_variable_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        raise NotImplementedError()

    def get_parameter_value(
        self, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        raise NotImplementedError()

    def get_component_variable_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        return {TimeScenarioIndex(0, 0): self.variables[comp_key(component_id, name)]}

    def get_component_parameter_value(
        self, component_id: str, name: str, time_scenarios_indices: TimeScenarioIndices
    ) -> Dict[TimeScenarioIndex, float]:
        return {TimeScenarioIndex(0, 0): self.parameters[comp_key(component_id, name)]}

    def parameter_is_constant_over_time(self, name: str) -> bool:
        raise NotImplementedError()

    @staticmethod
    def block_length() -> int:
        raise NotImplementedError()

    @staticmethod
    def scenarios() -> int:
        raise NotImplementedError()


# TODO: Redundant with add tests in test_linear_expressions_efficient ?
def test_comp_parameter() -> None:
    expr1 = LinearExpressionEfficient([], 1) + LinearExpressionEfficient(
        [TermEfficient(1, "comp1", "x")]
    )
    expr2 = expr1 / LinearExpressionEfficient(
        constant=ComponentParameterNode("comp1", "p")
    )

    assert str(expr2) == "(1.0 / comp1.p)x + (1.0 / comp1.p)"
    context = ComponentEvaluationContext(
        variables={comp_key("comp1", "x"): 3}, parameters={comp_key("comp1", "p"): 4}
    )
    # Need to specify at which (t, w) to evaluate as the information is not contained anymore within the value provider
    assert expr2.evaluate(context, RowIndex(0, 0)) == 1


# TODO: Find a better name
def test_ast() -> None:
    expr1 = LinearExpressionEfficient([], 1) + LinearExpressionEfficient(
        [TermEfficient(1, "", "x")]
    )
    expr2 = expr1 / LinearExpressionEfficient(constant=ParameterNode("p"))

    assert str(expr2) == "(1.0 / p)x + (1.0 / p)"

    context = EvaluationContext(variables={"x": 3}, parameters={"p": 4})
    assert expr2.evaluate(context, RowIndex(0, 0)) == 1


def test_operators() -> None:
    x = var("x")
    p = param("p")
    expr: LinearExpressionEfficient = (5 * x + 3) / p - 2

    assert str(expr) == "(5.0 / p)x + ((3.0 / p) - 2.0)"

    context = EvaluationContext(variables={"x": 3}, parameters={"p": 4})
    assert expr.evaluate(context, RowIndex(0, 0)) == pytest.approx(2.5, 1e-16)

    assert -expr.evaluate(context, RowIndex(0, 0)) == pytest.approx(-2.5, 1e-16)


# def test_degree() -> None:
#     x = var("x")
#     p = param("p")
#     expr = (5 * x + 3) / p

#     assert expr.compute_degree() == 1

#     # TODO: Should this be allowed ? If so, how should we represent is ?
#     expr = x * expr
#     assert expr.compute_degree() == 2


def test_degree_computation_should_take_into_account_simplifications() -> None:
    x = var("x")
    expr = x - x
    assert expr.is_constant()

    expr = 0 * x
    assert expr.is_constant()
    assert expr.is_zero()


# def test_parameters_resolution() -> None:
#     class TestParamProvider(ParameterValueProvider):
#         def get_component_parameter_value(self, component_id: str, name: str) -> float:
#             raise NotImplementedError()

#         def get_parameter_value(self, name: str) -> float:
#             return 2

#     x = var("x")
#     p = param("p")
#     expr = (5 * x + 3) / p
#     # TODO: We do not want this in the API, but rather expr.get(t, w)
#     assert expr.resolve_parameters(TestParamProvider()) == (5 * x + 3) / 2


# TODO: Write tests on ExpressionEfficientNodes for tree simplification, do the same for multiplication, substraction, etc
@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            var("x"),
            -var("x"),
            LinearExpressionEfficient(),
        ),
        (
            param("p"),
            -param("p"),
            LinearExpressionEfficient(),
        ),
        (
            var("x"),
            -var("y"),
            var("x") - var("y"),
        ),
        (
            comp_var("c1", "x"),
            var("x"),
            comp_var("c1", "x") + var("x"),
        ),
        (
            comp_var("c1", "x"),
            comp_var("c2", "x"),
            comp_var("c1", "x") + comp_var("c2", "x"),
        ),
        (
            comp_param("c1", "p"),
            comp_param("c2", "p"),
            comp_param("c1", "p") + comp_param("c2", "p"),
        ),
        (
            comp_var("c1", "x"),
            comp_param("c1", "p"),
            comp_var("c1", "x") + comp_param("c1", "p"),
        ),
        (
            param("p1"),
            param("p2"),
            param("p1") + param("p2"),
        ),
        (
            var("x"),
            var("x"),
            2 * var("x"),
        ),
        (
            param("p"),
            param("p"),
            2 * param("p"),
        ),
        (
            literal(4) * param("p"),
            param("p"),
            5 * param("p"),
        ),
        (
            param("p"),
            param("p") * param("q"),
            (1 + param("q"))
            * param("p"),  # Equality visitor not able to handle commutativity
        ),
    ],
)
def test_addition(
    e1: LinearExpressionEfficient,
    e2: LinearExpressionEfficient,
    expected: LinearExpressionEfficient,
) -> None:
    assert linear_expressions_equal(
        wrap_in_linear_expr(e1) + wrap_in_linear_expr(e2), wrap_in_linear_expr(expected)
    )


@pytest.mark.parametrize(
    "e1, e2, expected",
    [
        (
            var("x"),
            -var("x"),
            2 * var("x"),
        ),
        (
            param("p"),
            -param("p"),
            2 * param("p"),
        ),
        (
            var("x"),
            -var("y"),
            var("x") + var("y"),
        ),
        (
            comp_var("c1", "x"),
            var("x"),
            comp_var("c1", "x") - var("x"),
        ),
        (
            comp_var("c1", "x"),
            comp_var("c2", "x"),
            comp_var("c1", "x") - comp_var("c2", "x"),
        ),
        (
            comp_param("c1", "p"),
            comp_param("c2", "p"),
            comp_param("c1", "p") - comp_param("c2", "p"),
        ),
        (
            comp_var("c1", "x"),
            comp_param("c1", "p"),
            comp_var("c1", "x") - comp_param("c1", "p"),
        ),
        (
            param("p1"),
            param("p2"),
            param("p1") - param("p2"),
        ),
        (
            var("x"),
            var("x"),
            LinearExpressionEfficient(),
        ),
        (
            param("p"),
            param("p"),
            LinearExpressionEfficient(),
        ),
        (
            literal(4) * param("p"),
            param("p"),
            3 * param("p"),
        ),
        (
            param("p"),
            param("p") * param("q"),
            (1 - param("q"))
            * param("p"),  # Equality visitor not able to handle commutativity
        ),
    ],
)
def test_substraction(
    e1: LinearExpressionEfficient,
    e2: LinearExpressionEfficient,
    expected: LinearExpressionEfficient,
) -> None:
    assert linear_expressions_equal(
        wrap_in_linear_expr(e1) - wrap_in_linear_expr(e2), wrap_in_linear_expr(expected)
    )


@pytest.mark.parametrize(
    "lhs, rhs",
    [
        (
            (5 * comp_var("c", "x") + 3) / 2,
            LinearExpressionEfficient([TermEfficient(2.5, "c", "x")], 1.5),
        ),
        (
            param("p") * comp_var("c", "x"),
            LinearExpressionEfficient(
                [TermEfficient(ParameterNode("p"), "c", "x")],
            ),
        ),
        (
            param("p") * comp_var("c", "x"),
            LinearExpressionEfficient(
                [TermEfficient(ParameterNode("p"), "c", "x")],
            ),
        ),
    ],
)
def test_linear_expression_equality(
    lhs: LinearExpressionEfficient, rhs: LinearExpressionEfficient
) -> None:
    assert linear_expressions_equal(lhs, rhs)


# TODO: What is the equivalent of this test ?
# def test_linearization_of_non_linear_expressions_should_raise_value_error() -> None:
#     x = var("x")
#     expr = x.variance()

#     provider = StructureProvider()
#     with pytest.raises(ValueError) as exc:
#         linearize_expression(expr, provider)
#     assert (
#         str(exc.value)
#         == "Cannot linearize expression with a non-linear operator: Variance"
#     )


def test_standalone_constraint() -> None:
    cst = StandaloneConstraint(
        var("x"), wrap_in_linear_expr(literal(0)), wrap_in_linear_expr(literal(10))
    )

    assert str(cst) == "0 <= +x <=  + 10"


def test_comparison() -> None:
    x = var("x")
    p = param("p")

    expr_geq = (5 * x + 3) >= p - 2
    expr_leq = (5 * x + 3) <= p - 2
    expr_eq = (5 * x + 3) == p - 2

    assert str(expr_geq) == "0 <= 5.0x + (3.0 - (p - 2.0)) <=  + inf"
    assert str(expr_leq) == " + (-inf) <= 5.0x + (3.0 - (p - 2.0)) <= 0"
    assert str(expr_eq) == "0 <= 5.0x + (3.0 - (p - 2.0)) <= 0"


# TODO: Maybe imagine other use cases, that should be forbidden (composition of operators...)
@pytest.mark.parametrize(
    "expr, expec_terms, expec_constant",
    [
        (
            (var("x") + var("y") + literal(1)).shift(1),
            {
                TermKeyEfficient(
                    "",
                    "x",
                    TimeShift(InstancesTimeIndex(1)),
                    time_aggregator=TimeSum(
                        stay_roll=True
                    ),  # The internal representation of shift(1) is sum(shift=1)
                    scenario_aggregator=None,
                ): TermEfficient(
                    LiteralNode(1),
                    "",
                    "x",
                    time_operator=TimeShift(
                        InstancesTimeIndex(1),
                    ),
                    time_aggregator=TimeSum(stay_roll=True),
                ),
                TermKeyEfficient(
                    "",
                    "y",
                    TimeShift(
                        InstancesTimeIndex(1),
                    ),
                    time_aggregator=TimeSum(stay_roll=True),
                    scenario_aggregator=None,
                ): TermEfficient(
                    LiteralNode(1),
                    "",
                    "y",
                    time_operator=TimeShift(InstancesTimeIndex(1)),
                    time_aggregator=TimeSum(stay_roll=True),
                ),
            },
            TimeAggregatorNode(
                TimeOperatorNode(
                    LiteralNode(1), TimeOperatorName.SHIFT, InstancesTimeIndex(1)
                ),
                TimeAggregatorName.TIME_SUM,
                stay_roll=True,
            ),  # TODO: Could it be simplified online ?
        ),
        (
            (var("x") + var("y") + literal(1)).eval(1),
            {
                TermKeyEfficient(
                    "",
                    "x",
                    TimeEvaluation(InstancesTimeIndex(1)),
                    time_aggregator=TimeSum(
                        stay_roll=True
                    ),  # The internal representation of eval(1) is sum(eval=1)
                    scenario_aggregator=None,
                ): TermEfficient(
                    LiteralNode(1),
                    "",
                    "x",
                    time_operator=TimeEvaluation(
                        InstancesTimeIndex(1),
                    ),
                    time_aggregator=TimeSum(stay_roll=True),
                ),
                TermKeyEfficient(
                    "",
                    "y",
                    TimeEvaluation(
                        InstancesTimeIndex(1),
                    ),
                    time_aggregator=TimeSum(stay_roll=True),
                    scenario_aggregator=None,
                ): TermEfficient(
                    LiteralNode(1),
                    "",
                    "y",
                    time_operator=TimeEvaluation(InstancesTimeIndex(1)),
                    time_aggregator=TimeSum(stay_roll=True),
                ),
            },
            TimeAggregatorNode(
                TimeOperatorNode(
                    LiteralNode(1), TimeOperatorName.EVALUATION, InstancesTimeIndex(1)
                ),
                TimeAggregatorName.TIME_SUM,
                stay_roll=True,
            ),  # TODO: Could it be simplified online ?
        ),
        (
            (var("x") + var("y") + literal(1)).sum(),
            {
                TermKeyEfficient(
                    "",
                    "x",
                    time_operator=None,
                    time_aggregator=TimeSum(stay_roll=False),
                    scenario_aggregator=None,
                ): TermEfficient(
                    LiteralNode(1),  # Sum is not distributed to coeff
                    "",
                    "x",
                    time_operator=None,
                    time_aggregator=TimeSum(stay_roll=False),
                ),
                TermKeyEfficient(
                    "",
                    "y",
                    time_operator=None,
                    time_aggregator=TimeSum(stay_roll=False),
                    scenario_aggregator=None,
                ): TermEfficient(
                    LiteralNode(1),  # Sum is not distributed to coeff
                    "",
                    "y",
                    time_operator=None,
                    time_aggregator=TimeSum(stay_roll=False),
                ),
            },
            TimeAggregatorNode(
                LiteralNode(1), TimeAggregatorName.TIME_SUM, stay_roll=False
            ),  # TODO: Could it be simplified online ?
        ),
    ],
)
def test_operators_are_correctly_distributed_over_terms(
    expr: LinearExpressionEfficient,
    expec_terms: Dict[TermKeyEfficient, TermEfficient],
    expec_constant: ExpressionNodeEfficient,
) -> None:
    assert expr.terms == expec_terms
    assert expressions_equal(expr.constant, expec_constant)


class StructureProvider(IndexingStructureProvider):
    def get_component_variable_structure(
        self, component_id: str, name: str
    ) -> IndexingStructure:
        return IndexingStructure(True, True)

    def get_component_parameter_structure(
        self, component_id: str, name: str
    ) -> IndexingStructure:
        return IndexingStructure(True, True)

    def get_parameter_structure(self, name: str) -> IndexingStructure:
        return IndexingStructure(True, True)

    def get_variable_structure(self, name: str) -> IndexingStructure:
        return IndexingStructure(True, True)


def test_shift_on_time_step_list_raises_value_error() -> None:
    x = var("x")
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The shift operator can only be applied on expressions refering to a single time step. To apply a shifting sum on multiple time indices on an expression x, you should use x.sum(shift=...)"
        ),
    ):
        _ = x.shift(ExpressionRange(1, 4))


def test_eval_on_time_step_list_raises_value_error() -> None:
    x = var("x")
    with pytest.raises(
        ValueError,
        match=re.escape(
            "The eval operator can only be applied on expressions refering to a single time step. To apply a evaluation sum on multiple time indices on an expression x, you should use x.sum(eval=...)"
        ),
    ):
        _ = x.eval(ExpressionRange(1, 4))


# TODO: Shoudl be moved to test_linear_expression_efficient
@pytest.mark.parametrize(
    "linear_expr, expected_indexation",
    [
        (
            var("x").shift(1),
            IndexingStructure(True, True),
        ),
        (
            var("x").sum(shift=ExpressionRange(1, 4)),
            IndexingStructure(True, True),
        ),
        (
            var("x").eval(1),
            IndexingStructure(False, True),
        ),
        (
            var("x").sum(eval=ExpressionRange(1, 4)),
            IndexingStructure(False, True),
        ),
        (
            var("x").sum(),
            IndexingStructure(False, True),
        ),
        (
            var("x").expec(),
            IndexingStructure(True, False),
        ),
        (
            var("x").sum().expec(),
            IndexingStructure(False, False),
        ),
        (
            var("x").shift(1).expec(),
            IndexingStructure(True, False),
        ),
        (
            var("x").eval(1).expec(),
            IndexingStructure(False, False),
        ),
    ],
)
def test_compute_indexation(
    linear_expr: LinearExpressionEfficient, expected_indexation: IndexingStructure
) -> None:
    provider = StructureProvider()
    assert linear_expr.compute_indexation(provider) == expected_indexation


def test_forbidden_composition_should_raise_value_error() -> None:
    x = var("x")
    with pytest.raises(ValueError):
        _ = x.shift(ExpressionRange(1, 4)) + var("y")


def test_indexing_structure_comparison() -> None:
    free = IndexingStructure(True, True)
    constant = IndexingStructure(False, False)
    assert free | constant == IndexingStructure(True, True)


def test_multiplication_of_differently_indexed_terms() -> None:
    x = var("x")
    p = param("p")
    expr = p * x

    class CustomStructureProvider(IndexingStructureProvider):
        def get_component_variable_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            raise NotImplementedError()

        def get_component_parameter_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            raise NotImplementedError()

        def get_parameter_structure(self, name: str) -> IndexingStructure:
            return IndexingStructure(False, False)

        def get_variable_structure(self, name: str) -> IndexingStructure:
            return IndexingStructure(True, True)

    provider = CustomStructureProvider()

    assert expr.compute_indexation(provider) == IndexingStructure(True, True)


@pytest.mark.parametrize(
    "sum_expr, expected",
    [
        (sum_expressions([]), literal(0)),
        (sum_expressions([wrap_in_linear_expr(literal(1))]), literal(1)),
        (sum_expressions([wrap_in_linear_expr(literal(1)), var("x")]), 1 + var("x")),
        (
            sum_expressions(
                [
                    wrap_in_linear_expr(literal(1)),
                    var("x"),
                    wrap_in_linear_expr(param("p")),
                ]
            ),
            (1 + var("x")) + param("p"),
        ),
    ],
)
def test_sum_expressions(
    sum_expr: LinearExpressionEfficient, expected: LinearExpressionEfficient
) -> None:
    assert linear_expressions_equal(sum_expr, wrap_in_linear_expr(expected))


@pytest.mark.parametrize(
    "expr, unbound",
    [
        (literal(float("inf")), True),
        (literal(float("-inf")), True),
        (literal(-float("inf")), True),
        (var("x") + literal(float("-inf")), True),
        (var("x") + literal(4), False),
    ],
)
def test_is_unbound(expr: LinearExpressionEfficient, unbound: bool) -> None:
    assert wrap_in_linear_expr(expr).is_unbound() == unbound
