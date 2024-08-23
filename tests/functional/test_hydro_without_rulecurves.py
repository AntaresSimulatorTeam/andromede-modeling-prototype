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
from typing import List

import pytest

from andromede.hydro_heuristic.problem import (
    DataAggregatorParameters,
    ReservoirParameters,
)
from andromede.model import Model
from tests.functional.conftest import antares_hydro_heuristic_workflow


@pytest.fixture
def data_path() -> str:
    return str(Path(__file__).parent) + "/data/hydro_without_rulecurves"


def test_hydro_heuristic(
    data_path: str,
    monthly_aggregator_parameters: DataAggregatorParameters,
    monthly_hydro_heuristic_model: Model,
    daily_aggregator_parameters: List[DataAggregatorParameters],
    daily_hydro_heuristic_model: Model,
) -> None:
    """Check that weekly targets are the same in the POC and in Antares."""
    capacity = 1711510
    initial_level = 0.5 * capacity
    reservoir_data = ReservoirParameters(capacity, initial_level, data_path, scenario=0)

    intermonthly = 1
    interdaily = 3

    weekly_target = antares_hydro_heuristic_workflow(
        monthly_aggregator_parameters,
        monthly_hydro_heuristic_model,
        intermonthly,
        daily_aggregator_parameters,
        daily_hydro_heuristic_model,
        interdaily,
        reservoir_data,
    )

    # Check values
    expected_output_file = open(data_path + "/values-weekly.txt", "r")
    expected_output = expected_output_file.readlines()
    for week in range(52):
        assert float(expected_output[week + 7].strip().split("\t")[9]) == round(
            weekly_target[week]
        )
