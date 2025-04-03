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


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return Path(__file__).parents[1] / "data"


@pytest.fixture(scope="session")
def libs_dir(data_dir: Path) -> Path:
    return data_dir / "libs"


@pytest.fixture(scope="session")
def series_dir(data_dir: Path) -> Path:
    return data_dir / "series"


@pytest.fixture(scope="session")
def systems_dir(data_dir: Path) -> Path:
    return data_dir / "systems"
