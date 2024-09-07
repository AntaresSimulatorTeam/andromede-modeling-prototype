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

import dataclasses
from dataclasses import dataclass
from typing import Optional

import andromede.expression.scenario_operator
from andromede.expression.evaluate import ValueProvider
from andromede.expression.evaluate_parameters import evaluate_time_id
from andromede.expression.expression import (
    AllTimeSumNode,
    ComparisonNode,
    ComponentParameterNode,
    ComponentVariableNode,
    ExpressionNode,
    LiteralNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    TimeEvalNode,
    TimeShiftNode,
    TimeSumNode,
    VariableNode,
)
from andromede.expression.indexing import IndexingStructureProvider
from andromede.expression.visitor import ExpressionVisitorOperations, T, visit
from andromede.simulation.linear_expression import (
    AllTimeExpansion,
    LinearExpression,
    Term,
    TimeEvalExpansion,
    TimeExpansion,
    TimeShiftExpansion,
    TimeSumExpansion,
    generate_key,
)


@dataclass(frozen=True)
class LinearExpressionBuilder(ExpressionVisitorOperations[LinearExpression]):
    """
    Reduces a generic expression to a linear expression.

    Parameters should have been evaluated first.
    """

    structure_provider: IndexingStructureProvider
    value_provider: Optional[ValueProvider] = None

    def literal(self, node: LiteralNode) -> LinearExpression:
        return LinearExpression([], node.value)

    def comparison(self, node: ComparisonNode) -> LinearExpression:
        raise ValueError("Linear expression cannot contain a comparison operator.")

    def variable(self, node: VariableNode) -> LinearExpression:
        raise ValueError(
            "Variables need to be associated with their component ID before linearization."
        )

    def parameter(self, node: ParameterNode) -> LinearExpression:
        raise ValueError("Parameters must be evaluated before linearization.")

    def comp_variable(self, node: ComponentVariableNode) -> LinearExpression:
        return LinearExpression(
            [
                Term(
                    1,
                    node.component_id,
                    node.name,
                    self.structure_provider.get_component_variable_structure(
                        node.component_id, node.name
                    ),
                )
            ],
            0,
        )

    def comp_parameter(self, node: ComponentParameterNode) -> LinearExpression:
        raise ValueError("Parameters must be evaluated before linearization.")

    def _update_time_expansion(
        self, input: LinearExpression, time_expansion: TimeExpansion
    ) -> LinearExpression:
        result_terms = {}
        for term in input.terms.values():
            term_with_operator = dataclasses.replace(
                term, time_expansion=time_expansion
            )
            result_terms[generate_key(term_with_operator)] = term_with_operator

        # TODO: How can we apply a shift on a parameter ? It seems impossible for now as parameters must already be evaluated...
        result_expr = LinearExpression(result_terms, input.constant)
        return result_expr

    def time_eval(self, node: TimeEvalNode) -> LinearExpression:
        operand_expr = visit(node.operand, self)
        eval_time = evaluate_time_id(node.eval_time, self._value_provider())
        time_expansion = TimeEvalExpansion(eval_time)
        return self._update_time_expansion(operand_expr, time_expansion)

    def time_shift(self, node: TimeShiftNode) -> LinearExpression:
        operand_expr = visit(node.operand, self)
        time_shift = evaluate_time_id(node.time_shift, self._value_provider())
        time_expansion = TimeShiftExpansion(time_shift)
        return self._update_time_expansion(operand_expr, time_expansion)

    def time_sum(self, node: TimeSumNode) -> LinearExpression:
        operand_expr = visit(node.operand, self)
        from_shift = evaluate_time_id(node.from_time, self._value_provider())
        to_shift = evaluate_time_id(node.to_time, self._value_provider())
        time_expansion = TimeSumExpansion(from_shift, to_shift)
        return self._update_time_expansion(operand_expr, time_expansion)

    def all_time_sum(self, node: AllTimeSumNode) -> LinearExpression:
        operand_expr = visit(node.operand, self)
        time_expansion = AllTimeExpansion()
        return self._update_time_expansion(operand_expr, time_expansion)

    def _value_provider(self) -> ValueProvider:
        if self.value_provider is None:
            raise ValueError(
                "A value provider must be specified to linearize a time operator node."
                " This is required in order to evaluate the value of potential parameters"
                " used to specified the time ids on which the time operator applies."
            )
        return self.value_provider

    def scenario_operator(self, node: ScenarioOperatorNode) -> LinearExpression:
        scenario_operator_cls = getattr(
            andromede.expression.scenario_operator, node.name
        )
        if scenario_operator_cls.degree() > 1:
            raise ValueError(
                f"Cannot linearize expression with a non-linear operator: {scenario_operator_cls.__name__}"
            )

        operand_expr = visit(node.operand, self)
        result_terms = {}
        for term in operand_expr.terms.values():
            term_with_operator = dataclasses.replace(
                term, scenario_operator=scenario_operator_cls()
            )
            result_terms[generate_key(term_with_operator)] = term_with_operator

        result_expr = LinearExpression(result_terms, operand_expr.constant)
        return result_expr

    def port_field(self, node: PortFieldNode) -> LinearExpression:
        raise ValueError("Port fields must be replaced before linearization.")

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> LinearExpression:
        raise ValueError(
            "Port fields aggregators must be replaced before linearization."
        )


def linearize_expression(
    expression: ExpressionNode,
    structure_provider: IndexingStructureProvider,
    value_provider: Optional[ValueProvider] = None,
) -> LinearExpression:
    return visit(
        expression, LinearExpressionBuilder(structure_provider, value_provider)
    )
