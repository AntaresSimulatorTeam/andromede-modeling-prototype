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

"""
Util class to obtain solver results
"""
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TypeVar, Union, cast

from andromede.simulation.optimization import SolverAndContext
from andromede.study.data import TimeScenarioIndex

T = TypeVar("T")
K = TypeVar("K")


@dataclass
class OutputValues:
    """
    Contents variables output values after solver work completion.
    """

    @dataclass
    class Variable:
        """
        'constant_var':      c1,
        'time_only_var':     [[t1, t2, t3]],
        'scenario_only_var': [s1, s2],
        'time_scenario_var': [[t1s1, t2s1, t3s1], [t1s2, t2s2, t3s2]]

        Internally, the _value attribute will be a dict mapping TimeScenarioIndex(t,s) to float
        """

        _name: str
        _value: Dict[TimeScenarioIndex, float] = field(init=False, default_factory=dict)
        _size: Tuple[int, int] = field(init=False, default=(0, 0))

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, OutputValues.Variable):
                return NotImplemented
            return (
                self._name == other._name
                and self._size == other._size
                and self._value.keys() == other._value.keys()
                and all(
                    math.isclose(self._value[key], other._value[key])
                    for key in self._value
                )
            )

        def __str__(self) -> str:
            return f"{self._name} : {str(self.value)}"

        @property
        def value(self) -> Union[None, float, List[float], List[List[float]]]:
            size_s, size_t = self._size
            if size_t == 1:
                if size_s == 1:
                    # Constant
                    return self._value[TimeScenarioIndex(0, 0)]
                else:
                    # Scenario-only
                    return [self._value[TimeScenarioIndex(0, s)] for s in range(size_s)]
            else:
                # Either Time-only or Time-Scenario
                return [
                    [self._value[TimeScenarioIndex(t, s)] for t in range(size_t)]
                    for s in range(size_s)
                ]

        @value.setter
        def value(self, values: Union[float, List[float], List[List[float]]]) -> None:
            size_s, size_t = 1, 1

            if isinstance(values, list):
                size_s = len(values)
                for scenario, timesteps in enumerate(values):
                    if isinstance(timesteps, list):
                        size_t = len(timesteps)
                        for timestep, value in enumerate(timesteps):
                            # Either Time-only or Time-Scenario
                            self._value[TimeScenarioIndex(timestep, scenario)] = value
                    else:
                        # Scenario-only
                        self._value[TimeScenarioIndex(0, scenario)] = cast(
                            float, timesteps
                        )
            else:
                # Constant
                self._value[TimeScenarioIndex(0, 0)] = values

            self._size = (size_s, size_t)

        def _set(self, timestep: int, scenario: int, value: float) -> None:
            key = TimeScenarioIndex(timestep, scenario)
            if key not in self._value:
                size_s = max(self._size[0], scenario + 1)
                size_t = max(self._size[1], timestep + 1)
                self._size = (size_s, size_t)

            self._value[key] = value

    @dataclass
    class Component:
        _id: str
        _variables: Dict[str, "OutputValues.Variable"] = field(
            init=False, default_factory=dict
        )

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, OutputValues.Component):
                return NotImplemented
            return self._id == other._id and self._variables == other._variables

        def __str__(self) -> str:
            string = f"{self._id} :\n"
            for var in self._variables.values():
                string += f"  {str(var)}\n"
            return string

        def var(self, variable_name: str) -> "OutputValues.Variable":
            if variable_name not in self._variables:
                self._variables[variable_name] = OutputValues.Variable(variable_name)
            return self._variables[variable_name]

    problem: Optional[SolverAndContext] = field(default=None)
    _components: Dict[str, "OutputValues.Component"] = field(
        init=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        self._build_components()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OutputValues):
            return NotImplemented
        return self._components == other._components

    def __str__(self) -> str:
        string = "\n"
        for comp in self._components.values():
            string += f"{str(comp)}"

        return string

    def _build_components(self) -> None:
        if self.problem is None:
            return

        for key, value in self.problem.context.get_all_component_variables().items():
            if (key.block_timestep is None) or (key.scenario is None):
                continue

            (
                self.component(key.component_id)
                .var(str(key.variable_name))
                ._set(key.block_timestep, key.scenario, value.solution_value())
            )

    def component(self, component_id: str) -> "OutputValues.Component":
        if component_id not in self._components:
            self._components[component_id] = OutputValues.Component(component_id)
        return self._components[component_id]
