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

"""Storage behind a ``SimulationTable``: the table and its views read their
rows through a ``_TableStore``, whatever the storage."""

import functools
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Protocol, Tuple, cast

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds

from gems_runner.simulation.table_schema import (
    _COMPONENT,
    _OUTPUT,
    _SCENARIO,
    SIMULATION_TABLE_SCHEMA,
)


def _intersect(
    current: Optional[FrozenSet[Any]], extra: Optional[FrozenSet[Any]]
) -> Optional[FrozenSet[Any]]:
    if extra is None:
        return current
    return extra if current is None else current & extra


@dataclass(frozen=True)
class _RowFilter:
    """Rows to read; None means no restriction.

    Rows with an empty ``scenario_index`` (shared by all scenarios) always pass
    the scenario filter: they hold the value of every scenario.
    """

    components: Optional[FrozenSet[str]] = None
    outputs: Optional[FrozenSet[str]] = None
    scenarios: Optional[FrozenSet[int]] = None

    def narrow(
        self,
        *,
        components: Optional[FrozenSet[str]] = None,
        outputs: Optional[FrozenSet[str]] = None,
        scenarios: Optional[FrozenSet[int]] = None,
    ) -> "_RowFilter":
        """This filter, further restricted."""
        return replace(
            self,
            components=_intersect(self.components, components),
            outputs=_intersect(self.outputs, outputs),
            scenarios=_intersect(self.scenarios, scenarios),
        )

    @property
    def is_unrestricted(self) -> bool:
        return (
            self.components is None
            and self.outputs is None
            and (self.scenarios is None)
        )

    def mask(self, df: pd.DataFrame) -> "pd.Series[bool]":
        """The rows of *df* that pass the filter."""
        mask = pd.Series(True, index=df.index)
        if self.components is not None:
            mask &= df[_COMPONENT].isin(self.components)
        if self.outputs is not None:
            mask &= df[_OUTPUT].isin(self.outputs)
        if self.scenarios is not None:
            mask &= df[_SCENARIO].isin(self.scenarios) | df[_SCENARIO].isna()
        return mask


class _TableStore(Protocol):
    """Read-only storage of a simulation table."""

    table_id: str

    @property
    def scenarios(self) -> List[int]:
        """The scenarios of the table, sorted, without the empty index."""
        ...

    @property
    def path(self) -> Optional[Path]:
        """Where the table is stored, None in memory."""
        ...

    def read(self, row_filter: _RowFilter) -> pd.DataFrame:
        """The rows passing *row_filter*, in no particular order."""
        ...

    def iter_scenarios(
        self, row_filter: _RowFilter
    ) -> Iterator[Tuple[Optional[int], pd.DataFrame]]:
        """The rows passing *row_filter*, one scenario at a time.

        The rows shared by all scenarios come first, as ``(None, rows)``, and
        only if there are any; then ``(scenario, rows)`` for each scenario of
        the table allowed by the filter, even when it has no matching row.
        """
        ...

    def scan(self) -> ds.Dataset:
        """The whole table as a ``pyarrow.dataset.Dataset``."""
        ...


class _MemoryStore:
    """A simulation table held in memory as a single DataFrame, which must not
    be modified afterwards."""

    def __init__(self, df: pd.DataFrame, table_id: str = "") -> None:
        self.df = df
        self.table_id = table_id

    @property
    def scenarios(self) -> List[int]:
        if _SCENARIO not in self.df.columns:
            return []
        return sorted(int(s) for s in self.df[_SCENARIO].dropna().unique())

    @property
    def path(self) -> Optional[Path]:
        return None

    @functools.cached_property
    def _component_positions(self) -> Dict[str, Any]:
        """Row positions of each component, found once, so that reading one
        component does not scan the whole table."""
        codes, components = pd.factorize(self.df[_COMPONENT])  # -1 for empty cells
        order = np.argsort(codes, kind="stable")
        bounds = np.searchsorted(codes[order], np.arange(len(components) + 1))
        return {
            str(component): order[bounds[i] : bounds[i + 1]]
            for i, component in enumerate(components)
        }

    def read(self, row_filter: _RowFilter) -> pd.DataFrame:
        if row_filter.is_unrestricted:
            return self.df
        rows = self.df
        if row_filter.components is not None and _COMPONENT in rows.columns:
            positions = [
                self._component_positions[c]
                for c in row_filter.components
                if c in self._component_positions
            ]
            rows = rows.iloc[
                np.sort(np.concatenate(positions)) if positions else np.arange(0)
            ]
            row_filter = replace(row_filter, components=None)
        return rows if row_filter.is_unrestricted else rows[row_filter.mask(rows)]

    def iter_scenarios(
        self, row_filter: _RowFilter
    ) -> Iterator[Tuple[Optional[int], pd.DataFrame]]:
        rows = self.read(row_filter)
        if _SCENARIO not in rows.columns:
            return
        common = rows[rows[_SCENARIO].isna()]
        if not common.empty:
            yield None, common
        by_scenario = {
            int(cast(int, scenario)): part for scenario, part in rows.groupby(_SCENARIO)
        }
        for scenario in self.scenarios:
            if row_filter.scenarios is None or scenario in row_filter.scenarios:
                yield scenario, by_scenario.get(scenario, rows.iloc[0:0])

    def scan(self) -> ds.Dataset:
        return ds.dataset(  # type: ignore[no-untyped-call]
            pa.Table.from_pandas(
                self.df, schema=SIMULATION_TABLE_SCHEMA, preserve_index=False
            )
        )
