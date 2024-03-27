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
import typing
from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from yaml import safe_load


def parse_yaml_library(input: typing.TextIO) -> "InputLibrary":
    tree = safe_load(input)
    return InputLibrary.model_validate(tree["library"])


def parse_yaml_components(input_components: typing.TextIO) -> "InputComponents":
    tree = safe_load(input_components)
    return InputComponents.model_validate(tree["component"])


# def components_model_consistency(
#     input_model: typing.TextIO, input_components: typing.TextIO
# ) -> typing.Tuple["InputLibrary", "InputComponents"]:
#     library = parse_yaml_library(input_model)
#     components = parse_yaml_components(input_components)
#
#     # Check if models used by components are defined in the library
#     library_models = {model.id for model in library.models}
#     component_models = {comp.model.id for comp in components}
#
#     # Ensure all component models are present in the library
#     invalid_models = component_models - library_models
#     if invalid_models:
#         raise ValueError(f"Components use undefined models: {invalid_models}")
#
#     return library, components


# Design note: actual parsing and validation is delegated to pydantic models
def _to_kebab(snake: str) -> str:
    return snake.replace("_", "-")


class InputParameter(BaseModel):
    name: str
    time_dependent: bool = False
    scenario_dependent: bool = False

    class Config:
        alias_generator = _to_kebab


class InputVariable(BaseModel):
    name: str
    time_dependent: bool = True
    scenario_dependent: bool = True
    lower_bound: Optional[str] = None
    upper_bound: Optional[str] = None

    class Config:
        alias_generator = _to_kebab
        coerce_numbers_to_str = True


class InputConstraint(BaseModel):
    name: str
    expression: str
    lower_bound: Optional[str] = None
    upper_bound: Optional[str] = None

    class Config:
        alias_generator = _to_kebab


class InputField(BaseModel):
    name: str


class InputPortType(BaseModel):
    id: str
    fields: List[InputField] = Field(default_factory=list)


class InputModelPort(BaseModel):
    name: str
    type: str


class InputPortFieldDefinition(BaseModel):
    port: str
    field: str
    definition: str


class InputModel(BaseModel):
    id: str
    parameters: List[InputParameter] = Field(default_factory=list)
    variables: List[InputVariable] = Field(default_factory=list)
    ports: List[InputModelPort] = Field(default_factory=list)
    port_field_definitions: List[InputPortFieldDefinition] = Field(default_factory=list)
    binding_constraints: List[InputConstraint] = Field(default_factory=list)
    constraints: List[InputConstraint] = Field(default_factory=list)
    objective: Optional[str] = None

    class Config:
        alias_generator = _to_kebab


class InputComponents(BaseModel):
    id: str
    models: List[InputModel] = Field(default_factory=list)


class InputPortRef(BaseModel):
    component: InputComponents
    port_id: str


class InputPortConnections(BaseModel):
    port1: InputPortRef
    port2: InputPortRef
    master_port: Dict[InputField, InputPortRef]


class InputLibrary(BaseModel):
    id: str
    port_types: List[InputPortType] = Field(default_factory=list)
    models: List[InputModel] = Field(default_factory=list)

    class Config:
        alias_generator = _to_kebab
