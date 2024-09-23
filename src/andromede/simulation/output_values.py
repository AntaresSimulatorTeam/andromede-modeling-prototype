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
from typing import Any, Dict, List, Mapping, Optional, Tuple, TypeVar, Union, cast

from andromede.simulation.optimization import OptimizationProblem
from andromede.study.data import TimeScenarioIndex


@dataclass(frozen=True)
class OutputVariableIndex:
    timestep: Optional[int]
    scenario: Optional[int]


@dataclass(frozen=True)
class OutputVariableValues:
    def flatten(self) -> Union[None, float, List[float], List[List[float]]]:
        return None


@dataclass(frozen=True)
class ConstantValues(OutputVariableValues):
    value: float

    def flatten(self) -> Union[None, float, List[float], List[List[float]]]:
        return self.value


def constant_value(value: float) -> ConstantValues:
    return ConstantValues(value)


@dataclass(frozen=True)
class ScenarioValues(OutputVariableValues):
    values: Dict[int, float]

    def flatten(self) -> Union[None, float, List[float], List[List[float]]]:
        return [self.values[s] for s in range(len(self.values))]


def scenario_values(values: List[float]) -> ScenarioValues:
    return ScenarioValues(dict((k, v) for k, v in enumerate(values)))


@dataclass(frozen=True)
class TimeValues(OutputVariableValues):
    values: Dict[int, float]

    def flatten(self) -> Union[None, float, List[float], List[List[float]]]:
        return [self.values[t] for t in range(len(self.values))]


def time_values(values: List[float]) -> TimeValues:
    return TimeValues(dict((k, v) for k, v in enumerate(values)))


@dataclass(frozen=True)
class TimeScenarioValues(OutputVariableValues):
    values: Dict[TimeScenarioIndex, float]

    def flatten(self) -> Union[None, float, List[float], List[List[float]]]:
        timesteps = max([k.time for k in self.values]) + 1
        scenarios = max([k.scenario for k in self.values]) + 1
        return [
            [self.values[TimeScenarioIndex(t, s)] for t in range(timesteps)]
            for s in range(scenarios)
        ]


def time_scenario_values(values: List[List[float]]) -> TimeScenarioValues:
    values_dict = {}
    for s, time_values in enumerate(values):
        for t, value in enumerate(time_values):
            values_dict[TimeScenarioIndex(t, s)] = value
    return TimeScenarioValues(values_dict)


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
        _value: OutputVariableValues = OutputVariableValues()
        ignore: bool = field(default=False, init=False)

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, OutputValues.Variable):
                return NotImplemented
            return (self.ignore or other.ignore) or (
                self._name == other._name and self._value == other._value
            )

        def is_close(
            self,
            other: "OutputValues.Variable",
            *,
            rel_tol: float = 1.0e-9,
            abs_tol: float = 0.0,
        ) -> bool:
            # From the docs in https://docs.python.org/3/library/math.html#math.isclose
            # math.isclose(a, b) returns abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
            return (self.ignore or other.ignore) or (
                self._name == other._name
                and self._value.keys() == other._value.keys()
                and all(
                    math.isclose(
                        self._value[key],
                        other._value[key],
                        rel_tol=rel_tol,
                        abs_tol=abs_tol,
                    )
                    for key in self._value
                )
            )

        def __str__(self) -> str:
            return (
                f"{self._name} : {str(self.value)} {'(ignored)' if self.ignore else ''}"
            )

        @property
        def value(self) -> Union[None, float, List[float], List[List[float]]]:
            return self._value.flatten()

        @value.setter
        def value(self, values: OutputVariableValues) -> None:
            self._value = values

        def _set(
            self, timestep: Optional[int], scenario: Optional[int], value: float
        ) -> None:
            if timestep is not None and scenario is not None:
                if isinstance(self._value, OutputVariableValues):
                    self._value = TimeScenarioValues({})
                if not isinstance(self._value, TimeScenarioValues):
                    raise ValueError("Variable cannot have different indexings.")
                self._value.values[TimeScenarioIndex(timestep, scenario)] = value
            elif timestep is not None:
                if isinstance(self._value, OutputVariableValues):
                    self._value = TimeValues({})
                if not isinstance(self._value, TimeValues):
                    raise ValueError("Variable cannot have different indexings.")
                self._value.values[timestep] = value
            elif scenario is not None:
                if isinstance(self._value, OutputVariableValues):
                    self._value = ScenarioValues({})
                if not isinstance(self._value, ScenarioValues):
                    raise ValueError("Variable cannot have different indexings.")
                self._value.values[scenario] = value
            else:
                if isinstance(self._value, OutputVariableValues):
                    self._value = ConstantValues(value)
                else:
                    raise ValueError("Variable cannot have different indexings.")

    @dataclass
    class Component:
        _id: str
        _variables: Dict[str, "OutputValues.Variable"] = field(
            init=False, default_factory=dict
        )
        ignore: bool = field(default=False, init=False)

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, OutputValues.Component):
                return NotImplemented
            return self.is_close(other, rel_tol=0.0, abs_tol=0.0)

        def is_close(
            self,
            other: "OutputValues.Component",
            *,
            rel_tol: float = 1.0e-9,
            abs_tol: float = 0.0,
        ) -> bool:
            return (self.ignore or other.ignore) or (
                self._id == other._id
                and _are_mappings_close(
                    self._variables, other._variables, rel_tol, abs_tol
                )
            )

        def __str__(self) -> str:
            string = f"{self._id} : {'(ignored)' if self.ignore else ''}\n"
            for var in self._variables.values():
                string += f"  {str(var)}\n"
            return string

        def var(self, variable_name: str) -> "OutputValues.Variable":
            if variable_name not in self._variables:
                self._variables[variable_name] = OutputValues.Variable(variable_name)
            return self._variables[variable_name]

    problem: Optional[OptimizationProblem] = field(default=None)
    _components: Dict[str, "OutputValues.Component"] = field(
        init=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        self._build_components()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OutputValues):
            return NotImplemented
        return _are_mappings_close(self._components, other._components, 0.0, 0.0)

    def is_close(
        self, other: "OutputValues", *, rel_tol: float = 1.0e-9, abs_tol: float = 0.0
    ) -> bool:
        return _are_mappings_close(
            self._components, other._components, rel_tol, abs_tol
        )

    def __str__(self) -> str:
        string = "\n"
        for comp in self._components.values():
            string += f"{str(comp)}"

        return string

    def _build_components(self) -> None:
        if self.problem is None:
            return

        for key, value in self.problem.context.get_all_component_variables().items():
            (
                self.component(key.component_id)
                .var(key.variable_name)
                ._set(key.block_timestep, key.scenario, value.solution_value())
            )

    def component(self, component_id: str) -> "OutputValues.Component":
        if component_id not in self._components:
            self._components[component_id] = OutputValues.Component(component_id)
        return self._components[component_id]


Comparable = TypeVar("Comparable", OutputValues.Component, OutputValues.Variable)


def _are_mappings_close(
    lhs: Mapping[str, Comparable],
    rhs: Mapping[str, Comparable],
    rel_tol: float,
    abs_tol: float,
) -> bool:
    lhs_keys = lhs.keys()
    rhs_keys = rhs.keys()

    if (lhs_only_keys := lhs_keys - rhs_keys) and any(
        not lhs[key].ignore for key in lhs_only_keys
    ):
        return False

    elif (rhs_only_keys := rhs_keys - lhs_keys) and any(
        not rhs[key].ignore for key in rhs_only_keys
    ):
        return False

    elif intersect_keys := lhs_keys & rhs_keys:
        if rel_tol == abs_tol == 0.0:
            return all(lhs[key] == rhs[key] for key in intersect_keys)
        else:
            return all(
                lhs[key].is_close(rhs[key], rel_tol=rel_tol, abs_tol=abs_tol)
                for key in intersect_keys
            )
    else:
        return True


@dataclass(frozen=True)
class BendersSolution:
    data: Dict[str, Any]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BendersSolution):
            return NotImplemented
        return (
            self.overall_cost == other.overall_cost
            and self.candidates == other.candidates
        )

    def is_close(
        self,
        other: "BendersSolution",
        *,
        rel_tol: float = 1.0e-9,
        abs_tol: float = 0.0,
    ) -> bool:
        return (
            math.isclose(
                self.overall_cost, other.overall_cost, abs_tol=abs_tol, rel_tol=rel_tol
            )
            and self.candidates.keys() == other.candidates.keys()
            and all(
                math.isclose(
                    self.candidates[key],
                    other.candidates[key],
                    rel_tol=rel_tol,
                    abs_tol=abs_tol,
                )
                for key in self.candidates
            )
        )

    def __str__(self) -> str:
        lpad = 30
        rpad = 12

        string = "Benders' solution:\n"
        string += f"{'Overall cost':<{lpad}} : {self.overall_cost:>{rpad}}\n"
        string += f"{'Investment cost':<{lpad}} : {self.investment_cost:>{rpad}}\n"
        string += f"{'Operational cost':<{lpad}} : {self.operational_cost:>{rpad}}\n"
        string += "-" * (lpad + rpad + 3) + "\n"
        for candidate, investment in self.candidates.items():
            string += f"{candidate:<{lpad}} : {investment:>{rpad}}\n"

        return string

    @property
    def investment_cost(self) -> float:
        return self.data["solution"]["investment_cost"]

    @property
    def operational_cost(self) -> float:
        return self.data["solution"]["operational_cost"]

    @property
    def overall_cost(self) -> float:
        return self.data["solution"]["overall_cost"]

    @property
    def candidates(self) -> Dict[str, float]:
        return self.data["solution"]["values"]

    @property
    def status(self) -> str:
        return self.data["solution"]["problem_status"]

    @property
    def absolute_gap(self) -> float:
        return self.data["solution"]["optimality_gap"]

    @property
    def relative_gap(self) -> float:
        return self.data["solution"]["relative_gap"]

    @property
    def stopping_criterion(self) -> str:
        return self.data["solution"]["stopping_criterion"]


@dataclass(frozen=True, eq=False)
class BendersMergedSolution(BendersSolution):
    @property
    def lower_bound(self) -> float:
        return self.data["solution"]["lb"]

    @property
    def upper_bound(self) -> float:
        return self.data["solution"]["ub"]


@dataclass(frozen=True, eq=False)
class BendersDecomposedSolution(BendersSolution):
    @property
    def nb_iterations(self) -> int:
        return self.data["solution"]["iteration"]

    @property
    def duration(self) -> float:
        return self.data["run_duration"]
