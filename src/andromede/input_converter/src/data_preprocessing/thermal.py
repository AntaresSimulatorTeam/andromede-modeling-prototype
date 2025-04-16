from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from antares.craft.model.thermal import ThermalCluster

from andromede.study.data import load_ts_from_txt
from andromede.study.parsing import InputComponentParameter


class ThermalDataPreprocessing:
    DEFAULT_PERIOD: int = 168
    VARIATION_DIRECTIONS = Literal["forward", "backward"]

    def __init__(self, thermal: ThermalCluster, study_path: Path):
        self.thermal = thermal
        self.study_path = study_path
        self.series_path = (
            self.study_path
            / "input"
            / "thermal"
            / "series"
            / self.thermal.area_id
            / self.thermal.id
        )

    def _compute_p_min_cluster(self) -> pd.DataFrame:
        modulation_data: pd.Series = self.thermal.get_prepro_modulation_matrix().iloc[
            :, 3
        ]
        series_data: pd.DataFrame = self.thermal.get_series_matrix()
        unit_count: int = self.thermal.properties.unit_count
        nominal_capacity: float = self.thermal.properties.nominal_capacity
        scaled_modulation: pd.Series = modulation_data * nominal_capacity * unit_count
        #  min(min_gen_modulation * unit_count * nominal_capacity, p_max_cluster)
        min_values: pd.Series = pd.concat([scaled_modulation, series_data], axis=1).min(
            axis=1
        )
        return min_values.to_frame(name="p_min_cluster")

    def _compute_nb_units_min(self) -> pd.DataFrame:
        p_min_cluster: pd.DataFrame = load_ts_from_txt(
            "p_min_cluster", self.series_path
        )
        nominal_capacity: float = self.thermal.properties.nominal_capacity
        return pd.DataFrame(
            np.ceil(p_min_cluster / nominal_capacity),
        )

    def _compute_nb_units_max(self) -> pd.DataFrame:
        series_data: pd.DataFrame = self.thermal.get_series_matrix()
        nominal_capacity: float = self.thermal.properties.nominal_capacity
        return pd.DataFrame(
            np.ceil(series_data / nominal_capacity),
        )

    def _compute_nb_units_max_variation(
        self, direction: VARIATION_DIRECTIONS, period: int = DEFAULT_PERIOD
    ) -> pd.DataFrame:
        nb_units_max = load_ts_from_txt("nb_units_max", self.series_path)
        previous_indices = []

        indices = np.arange(len(nb_units_max))
        previous_indices = (indices - 1) % period + (indices // period) * period

        variation = pd.DataFrame()
        if direction == "backward":
            variation = nb_units_max.reset_index(drop=True) - nb_units_max.iloc[
                previous_indices
            ].reset_index(drop=True)
        elif direction == "forward":
            variation = nb_units_max.iloc[previous_indices].reset_index(
                drop=True
            ) - nb_units_max.reset_index(drop=True)

        # Utilisation d'une opération vectorisée au lieu de applymap
        variation = variation.clip(lower=0)
        return variation.rename(
            columns={variation.columns[0]: f"nb_units_max_variation_{direction}"}
        )

    def _build_csv_path(self, component_id: str, suffix: str = ".txt") -> Path:
        return self.series_path / Path(f"{component_id}").with_suffix(suffix)

    def generate_component(
        self, component_id: str, period: int = 0
    ) -> InputComponentParameter:
        match component_id:
            case "p_min_cluster":
                df = self._compute_p_min_cluster()
                csv_path = self._build_csv_path(component_id)
            case "nb_units_min":
                df = self._compute_nb_units_min()
                csv_path = self._build_csv_path(component_id)
            case "nb_units_max":
                df = self._compute_nb_units_max()
                csv_path = self._build_csv_path(component_id)
            case "nb_units_max_variation_forward":
                df = self._compute_nb_units_max_variation("forward", period)
                csv_path = self._build_csv_path(component_id)
            case "nb_units_max_variation_backward":
                df = self._compute_nb_units_max_variation("backward", period)
                csv_path = self._build_csv_path(component_id)

        # This separator is chosen to comply with the antares_craft timeseries creation
        df.to_csv(csv_path, sep="\t", index=False, header=False)

        return InputComponentParameter(
            id=component_id,
            time_dependent=True,
            scenario_dependent=True,
            value=str(csv_path).removesuffix(".txt"),
        )
