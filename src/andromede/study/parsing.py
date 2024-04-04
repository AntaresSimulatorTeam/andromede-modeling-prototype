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
from typing import List, Optional

from pydantic import BaseModel, Field
from yaml import safe_load

from andromede.model.parsing import InputModel


def parse_yaml_components(input_components: typing.TextIO) -> "InputComponents":
    tree = safe_load(input_components)
    return InputComponents.model_validate(tree["study"])


# Design note: actual parsing and validation is delegated to pydantic models
def _to_kebab(snake: str) -> str:
    return snake.replace("_", "-")


class InputPortConnections(BaseModel):
    id: str
    component1: str
    port_1: str
    component2: str
    port_2: str


class InputComponentParameter(BaseModel):
    name: str
    type: str
    value: Optional[int] = None
    timeseries: Optional[str] = None


class InputComponent(BaseModel):
    id: str
    model: str
    parameters: Optional[List[InputComponentParameter]] = None


class InputComponents(BaseModel):
    nodes: List[InputComponent] = Field(default_factory=list)
    components: List[InputComponent] = Field(default_factory=list)
    connections: List[InputPortConnections] = Field(default_factory=list)

    class Config:
        alias_generator = _to_kebab
