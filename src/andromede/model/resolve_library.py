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
from typing import Dict, List, Optional, Set

from andromede.expression import ExpressionNode
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
from andromede.model.library import Library
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
    input_libs: List[InputLibrary], preloaded_libs: Optional[List[Library]] = None
) -> Library:
    """
    Converts parsed data into an actually usable library of models.

     - resolves references between models and ports
     - parses expressions and resolves references to variables/params
    """
    yaml_lib_dict = dict((l.id, l) for l in input_libs)

    preloaded_port_types = {}
    if preloaded_libs:
        for preloaded_lib in preloaded_libs:
            preloaded_port_types.update(preloaded_lib.port_types)

    output_lib = Library(port_types=preloaded_port_types, models={})

    todo: List[str] = list(yaml_lib_dict)
    done: Set[str] = set()
    import_stack: List[str] = []

    while todo:
        next_lib_id = todo.pop()

        if next_lib_id in done:
            continue
        else:
            import_stack.append(next_lib_id)

        while import_stack:
            cur_lib = yaml_lib_dict[import_stack[-1]]
            dependencies = set(cur_lib.dependencies) - done

            if dependencies:
                first_dependency = dependencies.pop()

                if first_dependency in import_stack:
                    raise Exception("Circular import in yaml libraries")
                import_stack.append(first_dependency)

            else:
                port_types = [_convert_port_type(p) for p in cur_lib.port_types]
                port_types_dict = dict((p.id, p) for p in port_types)

                if output_lib.port_types.keys() & port_types_dict.keys():
                    raise Exception(
                        f"Port(s) : {str(output_lib.port_types.keys() & port_types_dict.keys())} is(are) defined twice."
                    )
                output_lib.port_types.update(port_types_dict)

                models = [
                    _resolve_model(m, output_lib.port_types) for m in cur_lib.models
                ]

                models_dict = dict((m.id, m) for m in models)
                if output_lib.models.keys() & models_dict.keys():
                    raise Exception(
                        f"Model(s) : {str(output_lib.models.keys() & models_dict.keys())} is(are) defined twice"
                    )
                output_lib.models.update(models_dict)

                done.add(import_stack.pop())

    return output_lib


def _convert_field(field: InputField) -> PortField:
    return PortField(name=field.id)


def _convert_port_type(port_type: InputPortType) -> PortType:
    return PortType(
        id=port_type.id, fields=[_convert_field(f) for f in port_type.fields]
    )


def _resolve_model(input_model: InputModel, port_types: Dict[str, PortType]) -> Model:
    identifiers = ModelIdentifiers(
        variables={v.id for v in input_model.variables},
        parameters={p.id for p in input_model.parameters},
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
    return ModelPort(port_name=port.id, port_type=port_types[port.type])


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
        name=param.id,
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
        name=var.id,
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
    return Constraint(
        name=constraint.id,
        expression=parse_expression(constraint.expression, identifiers),
        lower_bound=_to_expression_if_present(constraint.lower_bound, identifiers),
        upper_bound=_to_expression_if_present(constraint.upper_bound, identifiers),
    )
