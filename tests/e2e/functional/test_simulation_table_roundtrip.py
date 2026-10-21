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

"""E2E test: a simulation table saved to disk and reopened returns the same
values as the table in memory, through every accessor, regardless of row order.

Runs cover frontal, sequential with overlap and parallel modes, each with one
and with several scenarios, saved in CSV and in Parquet.
"""

from pathlib import Path
from typing import Callable, Dict

import pandas as pd
import pytest

from gems_craft.optim_config.parsing import ResolutionMode
from gems_craft.study.parsing import OutputFormat
from gems_runner.simulation.simulation_table import SimulationTable
from tests.e2e.functional.test_simulation_table_views import (
    _run_13_1,
    _sequential_overlap,
)

_KEY = ["block", "component", "output", "absolute_time_index", "scenario_index"]

_RUNS: Dict[str, Callable[[], SimulationTable]] = {
    "frontal-1": lambda: _run_13_1(ResolutionMode.FRONTAL, [0]),
    "frontal-2": lambda: _run_13_1(ResolutionMode.FRONTAL, [0, 1]),
    "sequential-overlap-1": _sequential_overlap,
    "sequential-overlap-2": lambda: _run_13_1(
        ResolutionMode.SEQUENTIAL_SUBPROBLEMS, [0, 1], block_length=2, block_overlap=1
    ),
    "parallel-1": lambda: _run_13_1(
        ResolutionMode.PARALLEL_SUBPROBLEMS, [0], block_length=2
    ),
    "parallel-2": lambda: _run_13_1(
        ResolutionMode.PARALLEL_SUBPROBLEMS, [0, 1], block_length=2
    ),
}


def _sorted(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(_KEY, na_position="first").reset_index(drop=True)


def _assert_same(memory: SimulationTable, stored: SimulationTable) -> None:
    """Compare every accessor of two tables, regardless of row order."""
    data = memory.data
    pd.testing.assert_frame_equal(
        _sorted(stored.to_pandas(load_all=True)), _sorted(data)
    )
    pd.testing.assert_frame_equal(
        stored.objective_values()
        .sort_values(["block", "scenario_index"])
        .reset_index(drop=True),
        memory.objective_values()
        .sort_values(["block", "scenario_index"])
        .reset_index(drop=True),
    )
    assert stored.scenarios == memory.scenarios
    assert stored.table_id == memory.table_id

    stored_parts = list(stored.iter_scenarios())
    memory_parts = list(memory.iter_scenarios())
    assert [s for s, _ in stored_parts] == [s for s, _ in memory_parts]
    for (_, a), (_, b) in zip(stored_parts, memory_parts):
        pd.testing.assert_frame_equal(_sorted(a), _sorted(b))

    outputs = data[data["component"].notna()][["component", "output", "block"]]
    for component, output, block in outputs.drop_duplicates().itertuples(index=False):
        # A fresh view per call, so that on disk the scenario reads are used.
        pd.testing.assert_frame_equal(
            stored.component(component).output(output, block=block).data,
            memory.component(component).output(output, block=block).data,
        )
        for scenario in memory.scenarios:
            pd.testing.assert_series_equal(
                stored.component(component)
                .output(output, block=block)
                .value(scenario_index=scenario),
                memory.component(component)
                .output(output, block=block)
                .value(scenario_index=scenario),
            )


@pytest.mark.parametrize("fmt", [OutputFormat.PARQUET, OutputFormat.CSV])
@pytest.mark.parametrize("run", list(_RUNS))
def test_saved_table_reopens_with_the_same_values(
    tmp_path: Path, run: str, fmt: OutputFormat
) -> None:
    memory = _RUNS[run]()

    stored = SimulationTable.open(memory.save(tmp_path / "table", fmt))

    _assert_same(memory, stored)
