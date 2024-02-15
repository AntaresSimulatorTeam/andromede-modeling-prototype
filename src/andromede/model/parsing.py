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
import io
from typing import List, Optional

from pydantic import BaseModel, Field
from yaml import safe_load


def parse_yaml_library(input: io.StringIO) -> "InputLibrary":
    tree = safe_load(input)
    return InputLibrary.model_validate(tree["library"])


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


class InputLibrary(BaseModel):
    id: str
    port_types: List[InputPortType] = Field(default_factory=list)
    models: List[InputModel] = Field(default_factory=list)

    class Config:
        alias_generator = _to_kebab
