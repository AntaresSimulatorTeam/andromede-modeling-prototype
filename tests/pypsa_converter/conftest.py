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


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def results_dir(data_dir: Path) -> Path:
    results_dir = data_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


@pytest.fixture
def systems_dir(data_dir: Path) -> Path:
    systems_dir = data_dir / "systems"
    systems_dir.mkdir(parents=True, exist_ok=True)
    return systems_dir


@pytest.fixture
def series_dir(data_dir: Path) -> Path:
    series_dir = data_dir / "series"
    series_dir.mkdir(parents=True, exist_ok=True)
    return series_dir
