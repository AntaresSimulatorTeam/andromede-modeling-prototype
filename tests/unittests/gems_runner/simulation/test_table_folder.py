# Copyright (c) 2024, RTE (https://www.rte-france.com)
# SPDX-License-Identifier: MPL-2.0

"""Tests for a simulation table stored on disk: the writer, the manifest,
SimulationTable.open() / save(), and reading through the folder store."""

import json
import os
import pickle
from pathlib import Path
from typing import Any, Tuple

import pandas as pd
import pytest
from test_simulation_table_read_api import _CountingStore, _keys, _table

from gems_craft.study.parsing import OutputFormat
from gems_runner.simulation.simulation_table import (
    SIMULATION_TABLE_DTYPES,
    SimulationTable,
)
from gems_runner.simulation.table_folder import MANIFEST_FILE, _TableWriter
from gems_runner.simulation.table_schema import _empty_frame

_FORMATS = [OutputFormat.PARQUET, OutputFormat.CSV]
_KEY = ["block", "component", "output", "absolute_time_index", "scenario_index"]


def _sorted(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(_KEY, na_position="first").reset_index(drop=True)


def _stored(
    tmp_path: Path, fmt: OutputFormat = OutputFormat.PARQUET
) -> SimulationTable:
    return SimulationTable.open(_table().save(tmp_path / "table", fmt))


# ---------------------------------------------------------------------------
# Layout and manifest
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fmt", _FORMATS)
def test_save_writes_scenario_files_common_file_and_manifest(
    tmp_path: Path, fmt: OutputFormat
) -> None:
    folder = _table().save(tmp_path / "table", fmt)

    ext = fmt.value
    assert sorted(os.listdir(folder)) == sorted(
        [
            MANIFEST_FILE,
            f"scenario-0.{ext}",
            f"scenario-1.{ext}",
            f"scenario-common.{ext}",
        ]
    )
    manifest = json.loads((folder / MANIFEST_FILE).read_text())
    assert manifest["schema_version"] == 1
    assert manifest["run_id"] == "run"
    assert manifest["format"] == ext
    assert manifest["scenarios"] == [0, 1]
    assert manifest["has_common"] is True
    assert [c["name"] for c in manifest["columns"]] == list(SIMULATION_TABLE_DTYPES)


@pytest.mark.parametrize("fmt", _FORMATS)
def test_open_reads_back_the_same_rows_and_dtypes(
    tmp_path: Path, fmt: OutputFormat
) -> None:
    table = _table()
    reopened = SimulationTable.open(table.save(tmp_path / "table", fmt))

    pd.testing.assert_frame_equal(
        _sorted(reopened.to_pandas(load_all=True)), _sorted(table.data)
    )
    assert reopened.table_id == "run"
    assert reopened.scenarios == [0, 1]
    assert reopened.path == tmp_path / "table"


def test_csv_empty_cells_read_back_as_missing_values(tmp_path: Path) -> None:
    rows = _stored(tmp_path, OutputFormat.CSV).to_pandas(outputs=["objective-value"])

    assert rows["component"].isna().all()
    assert rows["scenario_index"].isna().all()
    assert rows.dtypes.to_dict() == SIMULATION_TABLE_DTYPES


def test_a_table_without_rows_round_trips(tmp_path: Path) -> None:
    folder = SimulationTable(_empty_frame()).save(tmp_path / "table")
    reopened = SimulationTable.open(folder)

    assert reopened.scenarios == []
    assert reopened.to_pandas(load_all=True).empty
    assert reopened.to_pandas(load_all=True).dtypes.to_dict() == SIMULATION_TABLE_DTYPES


def test_a_stored_table_can_be_saved_again(tmp_path: Path) -> None:
    stored = _stored(tmp_path)
    copy = SimulationTable.open(stored.save(tmp_path / "copy", OutputFormat.CSV))

    pd.testing.assert_frame_equal(
        _sorted(copy.to_pandas(load_all=True)), _sorted(stored.to_pandas(load_all=True))
    )


# ---------------------------------------------------------------------------
# Folders: created, refused, incomplete
# ---------------------------------------------------------------------------


def test_save_creates_a_missing_folder(tmp_path: Path) -> None:
    assert (_table().save(tmp_path / "a" / "b") / MANIFEST_FILE).is_file()


def test_save_accepts_an_empty_folder(tmp_path: Path) -> None:
    (tmp_path / "table").mkdir()
    assert (_table().save(tmp_path / "table") / MANIFEST_FILE).is_file()


def test_save_refuses_a_folder_that_is_not_empty(tmp_path: Path) -> None:
    (tmp_path / "table").mkdir()
    (tmp_path / "table" / "old.csv").write_text("")
    with pytest.raises(FileExistsError, match="is not empty"):
        _table().save(tmp_path / "table")


def test_open_refuses_a_folder_without_manifest(tmp_path: Path) -> None:
    folder = _table().save(tmp_path / "table")
    (folder / MANIFEST_FILE).unlink()  # as left by an interrupted run
    with pytest.raises(FileNotFoundError, match="has no manifest.json"):
        SimulationTable.open(folder)


def test_open_refuses_an_unknown_schema_version(tmp_path: Path) -> None:
    folder = _table().save(tmp_path / "table")
    manifest = json.loads((folder / MANIFEST_FILE).read_text())
    (folder / MANIFEST_FILE).write_text(json.dumps({**manifest, "schema_version": 99}))
    with pytest.raises(ValueError, match="unsupported schema_version 99"):
        SimulationTable.open(folder)


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def _writer(tmp_path: Path) -> Tuple[_TableWriter, pd.DataFrame]:
    return _TableWriter(tmp_path / "table", "run", OutputFormat.PARQUET), _table().data


def test_no_manifest_before_finalize_and_no_write_after(tmp_path: Path) -> None:
    writer, df = _writer(tmp_path)
    writer.write_scenario(df[df["scenario_index"] == 0])
    assert not (tmp_path / "table" / MANIFEST_FILE).exists()

    writer.finalize()

    assert (tmp_path / "table" / MANIFEST_FILE).is_file()
    with pytest.raises(ValueError, match="already finalized"):
        writer.write_scenario(df[df["scenario_index"] == 1])


@pytest.mark.parametrize(
    "rows",
    [
        pytest.param(lambda df: df[df["scenario_index"].notna()], id="several"),
        pytest.param(lambda df: df[df["scenario_index"].isna()], id="empty-index"),
        pytest.param(lambda df: df.iloc[0:0], id="no-rows"),
    ],
)
def test_write_scenario_takes_the_rows_of_exactly_one_scenario(
    tmp_path: Path, rows: Any
) -> None:
    writer, df = _writer(tmp_path)
    with pytest.raises(ValueError, match="exactly one scenario"):
        writer.write_scenario(rows(df))


def test_write_scenario_refuses_a_scenario_written_twice(tmp_path: Path) -> None:
    writer, df = _writer(tmp_path)
    writer.write_scenario(df[df["scenario_index"] == 0])
    with pytest.raises(ValueError, match="Scenario 0 is already written"):
        writer.write_scenario(df[df["scenario_index"] == 0])


def test_write_common_refuses_rows_with_a_scenario(tmp_path: Path) -> None:
    writer, df = _writer(tmp_path)
    with pytest.raises(ValueError, match="empty scenario_index only"):
        writer.write_common(df[df["scenario_index"] == 0])


# ---------------------------------------------------------------------------
# Reading a stored table
# ---------------------------------------------------------------------------


def test_data_raises_on_a_stored_table(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"to_pandas\(load_all=True\)"):
        _stored(tmp_path).data


def test_to_pandas_without_filter_needs_load_all(tmp_path: Path) -> None:
    stored = _stored(tmp_path)
    with pytest.raises(ValueError, match="load_all=True"):
        stored.to_pandas()
    assert len(stored.to_pandas(load_all=True)) == len(_table().data)


@pytest.mark.parametrize("fmt", _FORMATS)
def test_filters_and_iter_scenarios_match_the_table_in_memory(
    tmp_path: Path, fmt: OutputFormat
) -> None:
    table, stored = _table(), _stored(tmp_path, fmt)

    for kwargs in (
        {"components": ["gen"]},
        {"outputs": ["d", "objective-value"]},
        {"scenarios": [1]},
        {"components": ["gen"], "scenarios": [0]},
    ):
        assert _keys(stored.to_pandas(**kwargs)) == _keys(table.to_pandas(**kwargs))
    assert [s for s, _ in stored.iter_scenarios()] == [None, 0, 1]
    for (s1, a), (s2, b) in zip(stored.iter_scenarios(), table.iter_scenarios()):
        assert s1 == s2 and _keys(a) == _keys(b)


def test_scan_covers_every_file(tmp_path: Path) -> None:
    assert _stored(tmp_path).scan().count_rows() == len(_table().data)


def test_scenario_value_on_disk_reads_that_scenario_and_the_shared_rows(
    tmp_path: Path,
) -> None:
    stored = _stored(tmp_path)
    store = _CountingStore(stored._store, stored.path)  # type: ignore[arg-type]
    stored._store = store

    # p_max is in the common file: a one-scenario read must include it.
    p_max = stored.component("gen").output("p_max")
    assert p_max.value(time_index=0, scenario_index=1) == 200.0
    assert [f.scenarios for f in store.reads] == [frozenset({1})]
    files = stored._store._store._files(frozenset({1}))  # type: ignore[attr-defined]
    assert [f.name for f in files] == ["scenario-1.parquet", "scenario-common.parquet"]


def test_rows_read_in_full_are_reused_on_disk(tmp_path: Path) -> None:
    stored = _stored(tmp_path)
    store = _CountingStore(stored._store, stored.path)  # type: ignore[arg-type]
    stored._store = store
    view = stored.component("gen").output("p")

    view.data
    view.value(time_index=0, scenario_index=1)

    assert [f.scenarios for f in store.reads] == [None]


def test_a_stored_table_is_cheap_to_pickle(tmp_path: Path) -> None:
    stored = _stored(tmp_path)
    payload = pickle.dumps(stored)

    assert len(payload) < 2_000  # the path and the manifest, no rows
    assert pickle.loads(payload).component("gen").output("p").value(1, 1) == 13.0


# ---------------------------------------------------------------------------
# Deprecated exports
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "export",
    [
        pytest.param(lambda t, p: t.to_csv(p), id="to_csv"),
        pytest.param(lambda t, p: t.to_parquet(p), id="to_parquet"),
        pytest.param(lambda t, p: t.to_dataset(), id="to_dataset"),
        pytest.param(lambda t, p: t.to_netcdf(p), id="to_netcdf"),
    ],
)
def test_deprecated_exports_warn_in_memory_and_raise_on_disk(
    tmp_path: Path, export: Any
) -> None:
    with pytest.warns(DeprecationWarning, match="is deprecated"):
        export(_table(), tmp_path / "out")
    with pytest.raises(TypeError, match="not available on a simulation table stored"):
        export(_stored(tmp_path), tmp_path / "out")
