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

from andromede.expression.indexing_structure import IndexingStructure


class IndexingStructureProvider(ABC):
    @abstractmethod
    def get_parameter_structure(self, name: str) -> IndexingStructure:
        ...

    @abstractmethod
    def get_variable_structure(self, name: str) -> IndexingStructure:
        ...

    @abstractmethod
    def get_component_variable_structure(
        self, component_id: str, name: str
    ) -> IndexingStructure:
        ...

    @abstractmethod
    def get_component_parameter_structure(
        self, component_id: str, name: str
    ) -> IndexingStructure:
        ...
