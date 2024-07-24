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
from typing import Dict, List, Optional

from andromede.expression import ExpressionNode, literal
from andromede.expression.indexing_structure import IndexingStructure
from andromede.expression.parsing.parse_expression import (
    ModelIdentifiers,
    parse_expression,
)
from andromede.model import (
    Constraint,
    Model,
    ModelPort,
    Parameter,
    PortField,
    PortType,
    ProblemContext,
    ValueType,
    Variable,
    model,
)
from andromede.model.library import Library, library
from andromede.model.model import PortFieldDefinition, port_field_def
from andromede.model.parsing import (
    InputConstraint,
    InputField,
    InputLibrary,
    InputModel,
    InputModelPort,
    InputParameter,
    InputPortFieldDefinition,
    InputPortType,
    InputVariable,
)


def resolve_library(
    input_lib: InputLibrary, preloaded_libraries: Optional[List[Library]] = None
) -> Library:
    """
    Converts parsed data into an actually usable library of models.

     - resolves references between models and ports
     - parses expressions and resolves references to variables/params
    """
    if preloaded_libraries is None:
        preloaded_libraries = []
    port_types = [_convert_port_type(p) for p in input_lib.port_types]
    for lib in preloaded_libraries:
        port_types.extend(lib.port_types.values())
    port_types_dict = dict((p.id, p) for p in port_types)
    models = [_resolve_model(m, port_types_dict) for m in input_lib.models]
    return library(port_types, models)


def _convert_field(field: InputField) -> PortField:
    return PortField(name=field.name)


def _convert_port_type(port_type: InputPortType) -> PortType:
    return PortType(
        id=port_type.id, fields=[_convert_field(f) for f in port_type.fields]
    )


def _resolve_model(input_model: InputModel, port_types: Dict[str, PortType]) -> Model:
    identifiers = ModelIdentifiers(
        variables={v.name for v in input_model.variables},
        parameters={p.name for p in input_model.parameters},
    )
    return model(
        id=input_model.id,
        parameters=[_to_parameter(p) for p in input_model.parameters],
        variables=[_to_variable(v, identifiers) for v in input_model.variables],
        ports=[_resolve_model_port(p, port_types) for p in input_model.ports],
        port_fields_definitions=[
            _resolve_field_definition(d, identifiers)
            for d in input_model.port_field_definitions
        ],
        binding_constraints=[
            _to_constraint(c, identifiers) for c in input_model.binding_constraints
        ],
        constraints=[_to_constraint(c, identifiers) for c in input_model.constraints],
        objective_operational_contribution=_to_expression_if_present(
            input_model.objective, identifiers
        ),
    )


def _resolve_model_port(
    port: InputModelPort, port_types: Dict[str, PortType]
) -> ModelPort:
    return ModelPort(port_name=port.name, port_type=port_types[port.type])


def _resolve_field_definition(
    definition: InputPortFieldDefinition, ids: ModelIdentifiers
) -> PortFieldDefinition:
    return port_field_def(
        port_name=definition.port,
        field_name=definition.field,
        definition=parse_expression(definition.definition, ids),
    )


def _to_parameter(param: InputParameter) -> Parameter:
    return Parameter(
        name=param.name,
        type=ValueType.FLOAT,
        structure=IndexingStructure(param.time_dependent, param.scenario_dependent),
    )


def _to_expression_if_present(
    expr: Optional[str], identifiers: ModelIdentifiers
) -> Optional[ExpressionNode]:
    if not expr:
        return None
    return parse_expression(expr, identifiers)


def _to_variable(var: InputVariable, identifiers: ModelIdentifiers) -> Variable:
    return Variable(
        name=var.name,
        data_type={"float": ValueType.FLOAT, "integer": ValueType.INTEGER}[
            var.variable_type
        ],
        structure=IndexingStructure(var.time_dependent, var.scenario_dependent),
        lower_bound=_to_expression_if_present(var.lower_bound, identifiers),
        upper_bound=_to_expression_if_present(var.upper_bound, identifiers),
        context=ProblemContext.OPERATIONAL,
    )


def _to_constraint(
    constraint: InputConstraint, identifiers: ModelIdentifiers
) -> Constraint:
    lb = _to_expression_if_present(constraint.lower_bound, identifiers)
    ub = _to_expression_if_present(constraint.upper_bound, identifiers)
    return Constraint(
        name=constraint.name,
        expression=parse_expression(constraint.expression, identifiers),
        lower_bound=(lb if lb is not None else literal(-float("inf"))),
        upper_bound=(ub if ub is not None else literal(float("inf"))),
    )
