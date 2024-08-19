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
from enum import Enum
from typing import Dict, Iterable, List, Optional

import ortools.linear_solver.pywraplp as lp

from andromede.expression import ParameterValueProvider, resolve_parameters
from andromede.expression.evaluate_parameters_efficient import ValueProvider
from andromede.expression.indexing import IndexingStructureProvider
from andromede.expression.indexing_structure import IndexingStructure
from andromede.expression.linear_expression_efficient import (
    LinearExpressionEfficient,
    PortFieldId,
    PortFieldKey,
)
from andromede.expression.value_provider import TimeScenarioIndex, TimeScenarioIndices
from andromede.simulation.linear_expression import LinearExpression
from andromede.simulation.linearize import linearize_expression
from andromede.simulation.time_block import TimeBlock
from andromede.study.data import DataBase
from andromede.study.network import Component, Network
from andromede.utils import get_or_add


@dataclass(eq=True, frozen=True)
class TimestepComponentVariableKey:
    """
    Identifies the solver variable for one timestep and one component variable.
    """

    component_id: str
    variable_name: str
    block_timestep: Optional[int] = None
    scenario: Optional[int] = None


@dataclass
class SolverVariableInfo:
    """
    Helper class for constructing the structure file
    for Benders solver. It keeps track of the corresponding
    column of the variable in the MPS format as well as if it is
    present in the objective function or not
    """

    name: str
    column_id: int
    is_in_objective: bool


class BlockBorderManagement(Enum):
    """
    Class to specify the way of handling the time horizon (or time block) border.
        - IGNORE_OUT_OF_FRAME: Ignore terms in constraints that lead to out of horizon data
        - CYCLE: Consider all timesteps to be specified modulo the horizon length, this is the actual functioning of Antares
    """

    IGNORE_OUT_OF_FRAME = "IGNORE"
    CYCLE = "CYCLE"


class OptimizationContext:
    """
    Helper class to build the optimization problem.
    Maintains some mappings between model and solver objects.
    Also provides navigation method in the model (components by node ...).
    """

    def __init__(
        self,
        network: Network,
        database: DataBase,
        block: TimeBlock,
        scenarios: int,
        border_management: BlockBorderManagement,
    ):
        self._network = network
        self._database = database
        self._block = block
        self._scenarios = scenarios
        self._border_management = border_management
        self._component_variables: Dict[TimestepComponentVariableKey, lp.Variable] = {}
        self._solver_variables: Dict[lp.Variable, SolverVariableInfo] = {}
        self._connection_fields_expressions: Dict[
            PortFieldKey, List[LinearExpressionEfficient]
        ] = {}

    @property
    def network(self) -> Network:
        return self._network

    @property
    def scenarios(self) -> int:
        return self._scenarios

    def block_length(self) -> int:
        return len(self._block.timesteps)

    @property
    def connection_fields_expressions(
        self,
    ) -> Dict[PortFieldKey, List[LinearExpressionEfficient]]:
        return self._connection_fields_expressions

    # TODO: Need to think about data processing when creating blocks with varying or inequal time steps length (aggregation, sum ?, mean of data ?)
    def block_timestep_to_absolute_timestep(self, block_timestep: int) -> int:
        return self._block.timesteps[block_timestep]

    @property
    def database(self) -> DataBase:
        return self._database

    def _manage_border_timesteps(self, timestep: int) -> int:
        if self._border_management == BlockBorderManagement.CYCLE:
            return timestep % self.block_length()
        else:
            raise NotImplementedError

    def get_time_indices(self, index_structure: IndexingStructure) -> Iterable[int]:
        return range(self.block_length()) if index_structure.time else range(1)

    def get_scenario_indices(self, index_structure: IndexingStructure) -> Iterable[int]:
        return range(self.scenarios) if index_structure.scenario else range(1)

    # TODO: API to improve, variable_structure guides which of the indices block_timestep and scenario should be used
    def get_component_variable(
        self,
        block_timestep: int,
        scenario: int,
        component_id: str,
        variable_name: str,
        variable_structure: IndexingStructure,
    ) -> lp.Variable:
        block_timestep = self._manage_border_timesteps(block_timestep)

        # TODO: Improve design, variable_structure defines indexing
        if variable_structure.time == False:
            block_timestep = 0
        if variable_structure.scenario == False:
            scenario = 0

        return self._component_variables[
            TimestepComponentVariableKey(
                component_id, variable_name, block_timestep, scenario
            )
        ]

    def get_all_component_variables(
        self,
    ) -> Dict[TimestepComponentVariableKey, lp.Variable]:
        return self._component_variables

    def register_component_variable(
        self,
        block_timestep: int,
        scenario: int,
        component_id: str,
        variable_name: str,
        variable: lp.Variable,
    ) -> None:
        key = TimestepComponentVariableKey(
            component_id, variable_name, block_timestep, scenario
        )
        if key not in self._component_variables:
            self._solver_variables[variable] = SolverVariableInfo(
                variable.name(), len(self._solver_variables), False
            )
        self._component_variables[key] = variable

    def get_component_context(self, component: Component) -> "ComponentContext":
        return ComponentContext(self, component)

    def register_connection_fields_expressions(
        self,
        component_id: str,
        port_name: str,
        field_name: str,
        expression: LinearExpressionEfficient,
    ) -> None:
        key = PortFieldKey(component_id, PortFieldId(port_name, field_name))
        get_or_add(self._connection_fields_expressions, key, lambda: []).append(
            expression
        )


class TimestepValueProvider(ABC):
    """
    Interface which provides numerical values for individual timesteps.
    """

    @abstractmethod
    def get_value(self, block_timestep: int, scenario: int) -> float:
        raise NotImplementedError()


def _get_parameter_value(
    context: OptimizationContext,
    block_timestep: int,
    scenario: int,
    component_id: str,
    name: str,
) -> float:
    data = context.database.get_data(component_id, name)
    absolute_timestep = context.block_timestep_to_absolute_timestep(block_timestep)
    return data.get_value(absolute_timestep, scenario)


def _make_value_provider(
    context: "OptimizationContext",
    component: Component,
) -> ValueProvider:
    """
    Create a value provider which takes its values from
    the parameter values as defined in the network data.

    Cannot evaluate expressions which contain variables.
    """

    class Provider(ValueProvider):
        def get_component_variable_value(
            self,
            component_id: str,
            name: str,
            time_scenarios_indices: TimeScenarioIndices,
        ) -> Dict[TimeScenarioIndex, float]:
            raise NotImplementedError(
                "Cannot provide variable value at problem build time."
            )

        def get_component_parameter_value(
            self,
            component_id: str,
            name: str,
            time_scenarios_indices: TimeScenarioIndices,
        ) -> Dict[TimeScenarioIndex, float]:
            result = {}
            param_index = (
                context.network.get_component(component_id)
                .model.parameters[name]
                .structure
            )
            for block_timestep in time_scenarios_indices.time_indices:
                for scenario in time_scenarios_indices.scenario_indices:
                    result[
                        TimeScenarioIndex(block_timestep, scenario)
                    ] = _get_parameter_value(
                        context,
                        _get_data_time_key(block_timestep, param_index),
                        _get_data_scenario_key(scenario, param_index),
                        component_id,
                        name,
                    )
            return result

        def get_variable_value(
            self,
            name: str,
            time_scenarios_indices: TimeScenarioIndices,
        ) -> Dict[TimeScenarioIndex, float]:
            raise NotImplementedError(
                "Cannot provide variable value at problem build time."
            )

        def get_parameter_value(
            self,
            name: str,
            time_scenarios_indices: TimeScenarioIndices,
        ) -> Dict[TimeScenarioIndex, float]:
            raise ValueError(
                "Parameter must be associated to its component before resolution."
            )

        def parameter_is_constant_over_time(self, name: str) -> bool:
            return not component.model.parameters[name].structure.time

        @staticmethod
        def block_length() -> int:
            return context.block_length()

        @staticmethod
        def scenarios() -> int:
            return context.scenarios

    return Provider()


@dataclass(frozen=True)
class ExpressionTimestepValueProvider(TimestepValueProvider):
    context: "OptimizationContext"
    component: Component
    expression: LinearExpressionEfficient

    # OptimizationContext has knowledge of the block, so that get_value only needs block_timestep and scenario to get the correct data value

    def get_value(self, block_timestep: int, scenario: int) -> float:
        param_value_provider = _make_value_provider(
            self.context, block_timestep, scenario, self.component
        )
        return self.expression.evaluate(param_value_provider)


def _make_parameter_value_provider(
    context: "OptimizationContext",
    block_timestep: int,
    scenario: int,
) -> ParameterValueProvider:
    """
    A value provider which takes its values from
    the parameter values as defined in the network data.

    Cannot evaluate expressions which contain variables.
    """

    class Provider(ParameterValueProvider):
        def get_component_parameter_value(self, component_id: str, name: str) -> float:
            return _get_parameter_value(
                context, block_timestep, scenario, component_id, name
            )

        def get_parameter_value(self, name: str) -> float:
            raise ValueError(
                "Parameters should have been associated with their component before resolution."
            )

    return Provider()


def _make_data_structure_provider(
    network: Network, component: Component
) -> IndexingStructureProvider:
    """
    Retrieve information in data structure (parameter and variable) from the model
    """

    class Provider(IndexingStructureProvider):
        def get_component_variable_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            return network.get_component(component_id).model.variables[name].structure

        def get_component_parameter_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            return network.get_component(component_id).model.parameters[name].structure

        def get_parameter_structure(self, name: str) -> IndexingStructure:
            return component.model.parameters[name].structure

        def get_variable_structure(self, name: str) -> IndexingStructure:
            return component.model.variables[name].structure

    return Provider()


@dataclass(frozen=True)
class ComponentContext:
    """
    Helper class to fill the optimization problem with component-related equations and variables.
    """

    opt_context: OptimizationContext
    component: Component

    def get_values(
        self, expression: LinearExpressionEfficient
    ) -> TimestepValueProvider:
        """
        The returned value provider will evaluate the provided expression.
        """
        return ExpressionTimestepValueProvider(
            self.opt_context, self.component, expression
        )

    def add_variable(
        self,
        block_timestep: int,
        scenario: int,
        model_var_name: str,
        variable: lp.Variable,
    ) -> None:
        self.opt_context.register_component_variable(
            block_timestep, scenario, self.component.id, model_var_name, variable
        )

    def get_variable(
        self, block_timestep: int, scenario: int, variable_name: str
    ) -> lp.Variable:
        return self.opt_context.get_component_variable(
            block_timestep,
            scenario,
            self.component.id,
            variable_name,
            self.component.model.variables[variable_name].structure,
        )

    def linearize_expression(
        self,
        block_timestep: int,
        scenario: int,
        expression: LinearExpressionEfficient,
    ) -> LinearExpression:
        parameters_valued_provider = _make_parameter_value_provider(
            self.opt_context, block_timestep, scenario
        )
        evaluated_expr = resolve_parameters(expression, parameters_valued_provider)

        value_provider = _make_value_provider(
            self.opt_context, block_timestep, scenario, self.component
        )
        structure_provider = _make_data_structure_provider(
            self.opt_context.network, self.component
        )

        return linearize_expression(evaluated_expr, structure_provider, value_provider)


def _get_data_time_key(block_timestep: int, data_indexing: IndexingStructure) -> int:
    return block_timestep if data_indexing.time else 0


def _get_data_scenario_key(scenario: int, data_indexing: IndexingStructure) -> int:
    return scenario if data_indexing.scenario else 0
