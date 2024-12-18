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
from antares.model.study import Study  # type: ignore
from typing import Optional
from pydantic import BaseModel
from andromede.study.parsing import InputComponents
import yaml
from andromede.input_converter.src.utils import (
    resolve_path,
    convert_renewable_to_components,
    convert_area_to_components,
)


class StudyConverter:
    def __init__(self, study_path: Optional[Path]):
        """
        Initialize processor
        """
        self.study_path = resolve_path(study_path) if study_path else None
        self.study: Study = None

    def convert_study_to_input_components(self) -> InputComponents:
        areas = self.study.read_areas()
        area_components = convert_area_to_components(areas)
        return InputComponents(nodes=area_components)

    def validate_with_pydantic(
        self, data: dict, model_class: type[BaseModel]
    ) -> BaseModel:
        return model_class(**data)

    def transform_to_yaml(self, data: dict, output_path: str) -> None:
        with open(output_path, "w") as yaml_file:
            yaml.dump(data, yaml_file)

    def process_all(self) -> None:
        raise NotImplementedError
