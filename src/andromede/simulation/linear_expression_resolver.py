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

from dataclasses import dataclass
from typing import Dict, List

import ortools.linear_solver.pywraplp as lp

from andromede.expression.evaluate_parameters_efficient import (
    get_time_ids_from_instances_index,
    resolve_coefficient,
)
from andromede.expression.indexing_structure import RowIndex
from andromede.expression.linear_expression_efficient import (
    LinearExpressionEfficient,
    TermEfficient,
)
from andromede.expression.resolved_linear_expression import (
    ResolvedLinearExpression,
    ResolvedTerm,
)
from andromede.expression.scenario_operator import Expectation
from andromede.expression.time_operator import TimeShift
from andromede.expression.value_provider import (
    TimeScenarioIndex,
    TimeScenarioIndices,
    ValueProvider,
)
from andromede.simulation.optimization_context import OptimizationContext


@dataclass
class LinearExpressionResolver:
    context: OptimizationContext
    value_provider: ValueProvider

    def resolve(
        self, expression: LinearExpressionEfficient, row_id: RowIndex
    ) -> ResolvedLinearExpression:
        resolved_terms = []
        for term in expression.terms.values():
            # Here, the value provide is used only to evaluate possible time operator args if the term has one
            resolved_variables = self.resolve_variables(term, row_id)

            # TODO: Contrary to the time aggregator that does a sum which is the default behaviour when append resolved terms, expectation performs an averaging, so weights must be included in coefficients. We feel here that we could generalize time and scenario aggregation over variables with more general operators, the following lines are very specific to expectation with same weights over all scenarios
            weight = 1
            if isinstance(term.scenario_aggregator, Expectation):
                weight = 1 / self.value_provider.scenarios()

            for ts_id, lp_variable in resolved_variables.items():
                # TODO: Could we check in which case coeff resolution leads to the same result for each element in the for loop ? When there is only a literal, etc, etc ?
                resolved_coeff = resolve_coefficient(
                    term.coefficient,
                    self.value_provider,
                    RowIndex(ts_id.time, ts_id.scenario),
                )
                resolved_terms.append(
                    ResolvedTerm(weight * resolved_coeff, lp_variable)
                )

        resolved_constant = resolve_coefficient(
            expression.constant, self.value_provider, row_id
        )
        return ResolvedLinearExpression(resolved_terms, resolved_constant)

    def resolve_constant_expr(
        self, expression: LinearExpressionEfficient, row_id: RowIndex
    ) -> float:
        if not expression.is_constant():
            raise ValueError(f"{str(self)} is not a constant expression")
        return resolve_coefficient(expression.constant, self.value_provider, row_id)

    def resolve_variables(
        self, term: TermEfficient, row_id: RowIndex
    ) -> Dict[TimeScenarioIndex, lp.Variable]:
        solver_vars = {}
        operator_ts_ids = self._row_id_to_term_time_scenario_id(term, row_id)
        for time in operator_ts_ids.time_indices:
            for scenario in operator_ts_ids.scenario_indices:
                solver_vars[
                    TimeScenarioIndex(time, scenario)
                ] = self.context.get_component_variable(
                    time,
                    scenario,
                    term.component_id,
                    term.variable_name,
                    # At term build time, no information on the variable structure is known, we use it now
                    self.context.network.get_component(term.component_id)
                    .model.variables[term.variable_name]
                    .structure,
                )
        return solver_vars

    def _row_id_to_term_time_scenario_id(
        self, term: TermEfficient, row_id: RowIndex
    ) -> TimeScenarioIndices:
        operator_time_ids = self._compute_operator_time_ids(term, row_id)

        operator_scenario_ids = self._compute_operator_scenario_ids(term, row_id)
        return TimeScenarioIndices(operator_time_ids, operator_scenario_ids)

    def _compute_operator_scenario_ids(
        self, term: TermEfficient, row_id: RowIndex
    ) -> List[int]:
        if term.scenario_aggregator:
            operator_scenario_ids = list(range(self.context.scenarios))
        else:
            operator_scenario_ids = [row_id.scenario]
        return operator_scenario_ids

    def _compute_operator_time_ids(
        self, term: TermEfficient, row_id: RowIndex
    ) -> List[int]:
        if not term.time_operator and not term.time_aggregator:
            operator_time_ids = [row_id.time]
        elif term.time_operator:
            operator_time_ids = get_time_ids_from_instances_index(
                term.time_operator.time_ids, self.value_provider, row_id
            )
            if isinstance(term.time_operator, TimeShift):
                operator_time_ids = [
                    row_id.time + time_id for time_id in operator_time_ids
                ]
        else:  # Case time_aggregator but no time_operator i.e. sum over whole block
            operator_time_ids = list(range(self.context.block_length()))
        return operator_time_ids
