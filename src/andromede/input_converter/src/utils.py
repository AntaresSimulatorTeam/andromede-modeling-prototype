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

import yaml
from pydantic import BaseModel


def resolve_path(path_str: Path) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError

    absolute_path = path.resolve()
    return absolute_path


def transform_to_yaml(model: BaseModel, output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as yaml_file:
        yaml.dump(
            {"system": model.model_dump(by_alias=True, exclude_unset=True)},
            yaml_file,
            allow_unicode=True,
        )
