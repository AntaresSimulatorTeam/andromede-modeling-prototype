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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from andromede.expression import ValueProvider, resolve_parameters

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
    ProblemVariableNode,
    ScenarioOperatorNode,
    TimeEvalNode,
    TimeShiftNode,
    TimeSumNode,
    VariableNode,
    TimeIndex,
    TimeShift,
    ScenarioIndex,
    TimeStep,
    OneScenarioIndex,
    NoScenarioIndex,
    NoTimeIndex,
)
from andromede.expression.visitor import ExpressionVisitorOperations, visit
from andromede.simulation.linear_expression import LinearExpression, Term


class ParameterGetter(ABC):
    @abstractmethod
    def get_parameter_value(
        self, component_id: str, parameter_name: str, timestep: int, scenario: int
    ) -> float:
        pass


@dataclass(frozen=True)
class LinearExpressionBuilder(ExpressionVisitorOperations[LinearExpression]):
    """
    Reduces a generic expression to a linear expression.

    Parameters should have been evaluated first.
    """

    # TODO: linear expressions should be re-usable for different timesteps and scenarios
    timestep: int
    scenario: int
    value_provider: Optional[ParameterGetter] = None

    def _get_timestep(self, time_index: TimeIndex) -> int:
        if isinstance(time_index, TimeShift):
            return self.timestep + time_index.timeshift
        if isinstance(time_index, TimeStep):
            return time_index.timestep
        if isinstance(time_index, NoTimeIndex):
            return self.timestep

    def _get_scenario(self, scenario_index: ScenarioIndex) -> int:
        if isinstance(scenario_index, OneScenarioIndex):
            return scenario_index.scenario
        if isinstance(scenario_index, NoScenarioIndex):
            return self.scenario

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
        raise ValueError(
            "Variables need to be associated with their timestep/scenario before linearization."
        )

    def pb_variable(self, node: ProblemVariableNode) -> LinearExpression:
        return LinearExpression(
            [
                Term(
                    1,
                    node.component_id,
                    node.name,
                    time_index=self._get_timestep(node.time_index),
                    scenario_index=self._get_scenario(node.scenario_index),
                )
            ],
            0,
        )

    def comp_parameter(self, node: ComponentParameterNode) -> LinearExpression:
        raise ValueError(
            "Parameters need to be associated with their timestep/scenario before linearization."
        )

    def pb_parameter(self, node: ProblemVariableNode) -> LinearExpression:
        # TODO SL: not the best place to do this.
        # in the future, we should evaluate coefficients of variables as time vectors once for all timesteps
        time_index = self._get_timestep(node.time_index)
        scenario_index = self._get_scenario(node.scenario_index)
        return LinearExpression(
            [],
            self._value_provider().get_parameter_value(
                node.component_id, node.name, time_index, scenario_index
            ),
        )

    def time_eval(self, node: TimeEvalNode) -> LinearExpression:
        raise ValueError("Time operators need to be expanded before linearization.")

    def time_shift(self, node: TimeShiftNode) -> LinearExpression:
        raise ValueError("Time operators need to be expanded before linearization.")

    def time_sum(self, node: TimeSumNode) -> LinearExpression:
        raise ValueError("Time operators need to be expanded before linearization.")

    def all_time_sum(self, node: AllTimeSumNode) -> LinearExpression:
        raise ValueError("Time operators need to be expanded before linearization.")

    def _value_provider(self) -> ParameterGetter:
        if self.value_provider is None:
            raise ValueError(
                "A value provider must be specified to linearize a time operator node."
                " This is required in order to evaluate the value of potential parameters"
                " used to specified the time ids on which the time operator applies."
            )
        return self.value_provider

    def scenario_operator(self, node: ScenarioOperatorNode) -> LinearExpression:
        raise ValueError("Scenario operators need to be expanded before linearization.")

    def port_field(self, node: PortFieldNode) -> LinearExpression:
        raise ValueError("Port fields must be replaced before linearization.")

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> LinearExpression:
        raise ValueError(
            "Port fields aggregators must be replaced before linearization."
        )


def linearize_expression(
    expression: ExpressionNode,
    timestep: int,
    scenario: int,
    value_provider: Optional[ParameterGetter] = None,
) -> LinearExpression:
    return visit(
        expression,
        LinearExpressionBuilder(
            value_provider=value_provider, timestep=timestep, scenario=scenario
        ),
    )
