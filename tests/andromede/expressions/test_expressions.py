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

from dataclasses import dataclass, field
from typing import Dict

import pytest

from andromede.expression import (
    AdditionNode,
    DivisionNode,
    EvaluationContext,
    EvaluationVisitor,
    ExpressionDegreeVisitor,
    ExpressionNode,
    LiteralNode,
    ParameterNode,
    ParameterValueProvider,
    PrinterVisitor,
    ValueProvider,
    VariableNode,
    literal,
    param,
    resolve_parameters,
    sum_expressions,
    var,
    visit,
)
from andromede.expression.equality import expressions_equal
from andromede.expression.expression import (
    ComponentParameterNode,
    ComponentVariableNode,
    ExpressionRange,
    Instances,
    comp_param,
    comp_var,
    port_field,
)
from andromede.expression.indexing import IndexingStructureProvider, compute_indexation
from andromede.expression.indexing_structure import IndexingStructure
from andromede.model.model import PortFieldId
from andromede.simulation.linear_expression import LinearExpression, Term
from andromede.simulation.linearize import linearize_expression


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

    def get_variable_value(self, name: str) -> float:
        raise NotImplementedError()

    def get_parameter_value(self, name: str) -> float:
        raise NotImplementedError()

    def get_component_variable_value(self, component_id: str, name: str) -> float:
        return self.variables[comp_key(component_id, name)]

    def get_component_parameter_value(self, component_id: str, name: str) -> float:
        return self.parameters[comp_key(component_id, name)]

    def parameter_is_constant_over_time(self, name: str) -> bool:
        raise NotImplementedError()


def test_comp_parameter() -> None:
    add_node = AdditionNode(LiteralNode(1), ComponentVariableNode("comp1", "x"))
    expr = DivisionNode(add_node, ComponentParameterNode("comp1", "p"))

    assert visit(expr, PrinterVisitor()) == "((1 + comp1.x) / comp1.p)"

    context = ComponentEvaluationContext(
        variables={comp_key("comp1", "x"): 3}, parameters={comp_key("comp1", "p"): 4}
    )
    assert visit(expr, EvaluationVisitor(context)) == 1


def test_ast() -> None:
    add_node = AdditionNode(LiteralNode(1), VariableNode("x"))
    expr = DivisionNode(add_node, ParameterNode("p"))

    assert visit(expr, PrinterVisitor()) == "((1 + x) / p)"

    context = EvaluationContext(variables={"x": 3}, parameters={"p": 4})
    assert visit(expr, EvaluationVisitor(context)) == 1


def test_operators() -> None:
    x = var("x")
    p = param("p")
    expr: ExpressionNode = (5 * x + 3) / p - 2

    assert visit(expr, PrinterVisitor()) == "((((5.0 * x) + 3.0) / p) - 2.0)"

    context = EvaluationContext(variables={"x": 3}, parameters={"p": 4})
    assert visit(expr, EvaluationVisitor(context)) == pytest.approx(2.5, 1e-16)

    assert visit(-expr, EvaluationVisitor(context)) == pytest.approx(-2.5, 1e-16)


def test_degree() -> None:
    x = var("x")
    p = param("p")
    expr = (5 * x + 3) / p

    assert visit(expr, ExpressionDegreeVisitor()) == 1

    expr = x * expr
    assert visit(expr, ExpressionDegreeVisitor()) == 2


@pytest.mark.xfail(reason="Degree simplification not implemented")
def test_degree_computation_should_take_into_account_simplifications() -> None:
    x = var("x")
    expr = x - x
    assert visit(expr, ExpressionDegreeVisitor()) == 0

    expr = LiteralNode(0) * x
    assert visit(expr, ExpressionDegreeVisitor()) == 0


def test_parameters_resolution() -> None:
    class TestParamProvider(ParameterValueProvider):
        def get_component_parameter_value(self, component_id: str, name: str) -> float:
            raise NotImplementedError()

        def get_parameter_value(self, name: str) -> float:
            return 2

    x = var("x")
    p = param("p")
    expr = (5 * x + 3) / p
    assert resolve_parameters(expr, TestParamProvider()) == (5 * x + 3) / 2


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


def test_comparison() -> None:
    x = var("x")
    p = param("p")
    expr: ExpressionNode = (5 * x + 3) >= p - 2

    assert visit(expr, PrinterVisitor()) == "((5.0 * x) + 3.0) >= (p - 2.0)"


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


def test_shift() -> None:
    x = var("x")
    expr = x.shift(ExpressionRange(1, 4))

    provider = StructureProvider()

    assert compute_indexation(expr, provider) == IndexingStructure(True, True)
    assert expr.instances == Instances.MULTIPLE


def test_shifting_sum() -> None:
    x = var("x")
    expr = x.shift(ExpressionRange(1, 4)).sum()
    provider = StructureProvider()

    assert compute_indexation(expr, provider) == IndexingStructure(True, True)
    assert expr.instances == Instances.SIMPLE


def test_eval() -> None:
    x = var("x")
    expr = x.eval(ExpressionRange(1, 4))
    provider = StructureProvider()

    assert compute_indexation(expr, provider) == IndexingStructure(False, True)
    assert expr.instances == Instances.MULTIPLE


def test_eval_sum() -> None:
    x = var("x")
    expr = x.eval(ExpressionRange(1, 4)).sum()
    provider = StructureProvider()

    assert compute_indexation(expr, provider) == IndexingStructure(False, True)
    assert expr.instances == Instances.SIMPLE


def test_sum_over_whole_block() -> None:
    x = var("x")
    expr = x.sum()
    provider = StructureProvider()

    assert compute_indexation(expr, provider) == IndexingStructure(False, True)
    assert expr.instances == Instances.SIMPLE


def test_forbidden_composition_should_raise_value_error() -> None:
    x = var("x")
    with pytest.raises(ValueError):
        _ = x.shift(ExpressionRange(1, 4)) + var("y")


def test_expectation() -> None:
    x = var("x")
    expr = x.expec()
    provider = StructureProvider()

    assert compute_indexation(expr, provider) == IndexingStructure(True, False)
    assert expr.instances == Instances.SIMPLE


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

    assert compute_indexation(expr, provider) == IndexingStructure(True, True)


def test_sum_expressions() -> None:
    assert expressions_equal(sum_expressions([]), literal(0))
    assert expressions_equal(sum_expressions([literal(1)]), literal(1))
    assert expressions_equal(sum_expressions([literal(1), var("x")]), 1 + var("x"))
    assert expressions_equal(
        sum_expressions([literal(1), var("x"), param("p")]), 1 + (var("x") + param("p"))
    )
