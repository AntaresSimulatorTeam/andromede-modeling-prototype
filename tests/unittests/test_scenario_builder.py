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

import pandas as pd
import pytest

from andromede.study import DataBase
from andromede.study.data import ComponentParameterIndex
from andromede.study.parsing import parse_yaml_components
from andromede.study.resolve_components import build_scenarized_data_base


@pytest.fixture
def database(data_dir: Path) -> DataBase:
    builder = pd.DataFrame(
        {
            "name": [
                "load",
                "load",
                "load",
                "load",
                "cost-group",
                "cost-group",
                "cost-group",
                "cost-group",
            ],
            "year": [0, 1, 2, 3, 0, 1, 2, 3],
            "scenario": [0, 1, 0, 1, 0, 0, 1, 1],
        }
    )
    builder = builder.reset_index()

    study_path = data_dir / "components_for_scenarization_test.yml"
    ts_path = data_dir
    with study_path.open() as components:
        return build_scenarized_data_base(
            parse_yaml_components(components), builder, ts_path
        )


def test_scenarized_data_base(database):
    cost_index = ComponentParameterIndex("G", "cost")
    assert database.get_value(cost_index, 0, 0) == 100
    assert database.get_value(cost_index, 0, 1) == 100
    assert database.get_value(cost_index, 0, 2) == 200
    assert database.get_value(cost_index, 0, 3) == 200

    load_index = ComponentParameterIndex("D", "demand")
    assert database.get_value(load_index, 0, 0) == 50
    assert database.get_value(load_index, 0, 1) == 100
    assert database.get_value(load_index, 0, 2) == 50
    assert database.get_value(load_index, 0, 3) == 100
