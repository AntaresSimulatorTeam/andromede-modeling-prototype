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
from pathlib import Path
from typing import Optional

import yaml
from antares.craft.model.study import Study, read_study_local
from pydantic import BaseModel

from andromede.input_converter.src.utils import (
    convert_area_to_component_list,
    resolve_path,
    convert_renewable_to_component_list,
)

from andromede.study.parsing import InputStudy


class AntaresStudyConverter:
    def __init__(self, study_path: Optional[Path]):
        """
        Initialize processor
        """
        self.study_path = resolve_path(study_path) if study_path else None
        self.study: Study = (
            read_study_local(self.study_path) if self.study_path else None  # type: ignore
        )

    def convert_study_to_input_study(self) -> InputStudy:
        areas = self.study.read_areas()
        area_components = convert_area_to_component_list(areas)
        root_path = self.study.service.config.study_path  # type: ignore
        renewable_components = convert_renewable_to_component_list(areas, root_path)
        return InputStudy(nodes=area_components, components=renewable_components)

    @staticmethod
    def transform_to_yaml(model: BaseModel, output_path: str) -> None:
        with open(output_path, "w", encoding="utf-8") as yaml_file:
            yaml.dump(
                {"study": model.model_dump(by_alias=True, exclude_unset=True)},
                yaml_file,
                allow_unicode=True,
            )

    def process_all(self) -> None:
        raise NotImplementedError
