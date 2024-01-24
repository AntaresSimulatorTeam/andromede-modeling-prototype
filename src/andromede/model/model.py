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
The model module defines the data model for user-defined models.
A model allows to define the behaviour for components, by
defining parameters, variables, and equations.
"""
import itertools
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from andromede.expression import ExpressionNode
from andromede.expression.degree import is_linear
from andromede.expression.expression import (
    ComponentParameterNode,
    ComponentVariableNode,
)
from andromede.expression.indexing import IndexingStructureProvider, compute_indexation
from andromede.expression.indexing_structure import IndexingStructure
from andromede.model.common import ProblemContext
from andromede.model.constraint import Constraint
from andromede.model.parameter import Parameter
from andromede.model.port import PortType
from andromede.model.variable import Variable
from andromede.model.constraint import Constraint


# TODO: Introduce bool_variable ?
def _make_structure_provider(model: "Model") -> IndexingStructureProvider:
    class Provider(IndexingStructureProvider):
        def get_parameter_structure(self, name: str) -> IndexingStructure:
            return model.parameters[name].structure

        def get_variable_structure(self, name: str) -> IndexingStructure:
            return model.variables[name].structure

        def get_component_parameter_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            raise NotImplementedError("Cannot have instantiated parameters in models.")

        def get_component_variable_structure(
            self, component_id: str, name: str
        ) -> IndexingStructure:
            raise NotImplementedError("Cannot have instantiated parameters in models.")

    return Provider()


@dataclass(frozen=True)
class ModelPort:
    """
    Instance of a port as a model member.

    A model may carry multiple ports of the same type.
    For example, the 2 ports at line extremities.
    """

    port_type: PortType
    port_name: str


@dataclass(frozen=True)
class PortFieldId:
    port_name: str
    field_name: str


@dataclass(frozen=True)
class PortFieldDefinition:
    """
    Defines the values of one port field
    """

    port_field: PortFieldId
    definition: ExpressionNode


@dataclass(frozen=True)
class Model:
    """
    Defines a model that can be referenced by actual components.
    A model defines the behaviour of those components.
    """

    id: str
    constraints: Dict[str, Constraint] = field(default_factory=dict)
    binding_constraints: Dict[str, Constraint] = field(default_factory=dict)
    inter_block_dyn: bool = False
    parameters: Dict[str, Parameter] = field(default_factory=dict)
    variables: Dict[str, Variable] = field(default_factory=dict)
    objective_contribution: Optional[ExpressionNode] = None
    ports: Dict[str, ModelPort] = field(default_factory=dict)  # key = port name
    port_fields_definitions: Dict[PortFieldId, PortFieldDefinition] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        if self.objective_contribution:
            if not is_linear(self.objective_contribution):
                raise ValueError("Objective contribution must be a linear expression.")

            data_structure_provider = _make_structure_provider(self)
            objective_structure = compute_indexation(
                self.objective_contribution, data_structure_provider
            )
            if objective_structure != IndexingStructure(time=False, scenario=False):
                raise ValueError(
                    "Objective contribution should be a real-valued expression."
                )
            # TODO: We should also check that the number of instances is equal to 1, but this would require a linearization here, do not want to do that for now...

        for definition in self.port_fields_definitions.values():
            port_name = definition.port_field.port_name
            port_field = definition.port_field.field_name
            port = self.ports.get(port_name, None)
            if port is None:
                raise ValueError(f"Invalid port in port field definition: {port_name}")
            if port_field not in [f.name for f in port.port_type.fields]:
                raise ValueError(
                    f"Invalid port field in port field definition: {port_field}"
                )
            # TODO: should we check something on the expression ? (comparison...)

    def get_all_constraints(self) -> Iterable[Constraint]:
        """
        Get binding constraints and inner constraints altogether.
        """
        return itertools.chain(
            self.binding_constraints.values(), self.constraints.values()
        )


def model(
    id: str,
    constraints: Optional[Iterable[Constraint]] = None,
    binding_constraints: Optional[Iterable[Constraint]] = None,
    parameters: Optional[Iterable[Parameter]] = None,
    variables: Optional[Iterable[Variable]] = None,
    objective_contribution: Optional[ExpressionNode] = None,
    inter_block_dyn: bool = False,
    ports: Optional[Iterable[ModelPort]] = None,
    port_fields_definitions: Optional[Iterable[PortFieldDefinition]] = None,
) -> Model:
    """
    Utility method to create Models from relaxed arguments
    """
    existing_port_names = {}
    if ports:
        for port in ports:
            port_name = port.port_name
            if port_name not in existing_port_names:
                existing_port_names[port_name] = port
            else:
                raise ValueError(
                    f"2 ports have the same name inside the model, it's not authorized : {port_name}"
                )
    return Model(
        id=id,
        constraints={c.name: c for c in constraints} if constraints else {},
        binding_constraints={c.name: c for c in binding_constraints}
        if binding_constraints
        else {},
        parameters={p.name: p for p in parameters} if parameters else {},
        variables={v.name: v for v in variables} if variables else {},
        objective_contribution=objective_contribution,
        inter_block_dyn=inter_block_dyn,
        ports=existing_port_names,
        port_fields_definitions={d.port_field: d for d in port_fields_definitions}
        if port_fields_definitions
        else {},
    )
