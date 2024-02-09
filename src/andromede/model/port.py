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

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PortField:
    name: str


@dataclass
class PortType:
    """
    Defines a port type.

    A port is an external interface of a model, where other
    ports can be connected.
    Only compatible ports may be connected together (?)
    """

    id: str
    fields: List[PortField]  # TODO: should we rename with "pin" ?
