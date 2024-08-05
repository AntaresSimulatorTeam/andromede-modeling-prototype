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

import pytest

from andromede.model.parsing import parse_yaml_library
from andromede.model.resolve_library import resolve_library, Library


@pytest.fixture(scope="session")
def libs_dir() -> Path:
    return Path(__file__).parent / "libs"


@pytest.fixture(scope="session")
def lib(libs_dir: Path) -> Library:
    lib_file = libs_dir / "lib.yml"

    with lib_file.open() as f:
        input_lib = parse_yaml_library(f)

    lib = resolve_library(input_lib)
    return lib
