from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from antares.craft.model.thermal import ThermalCluster

from andromede.study.data import load_ts_from_txt
from andromede.study.parsing import InputComponentParameter


class ThermalDataPreprocessing:
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

    def get_p_min_cluster_parameter(self) -> InputComponentParameter:
        modulation_data = self.thermal.get_prepro_modulation_matrix().iloc[:, 3]
        series_data = self.thermal.get_series_matrix()

        unit_count = self.thermal.properties.unit_count
        nominal_capacity = self.thermal.properties.nominal_capacity
        modulation_data = modulation_data * nominal_capacity * unit_count

        p_min_cluster = pd.concat([modulation_data, series_data], axis=1).min(axis=1)
        p_min_cluster_output = self.series_path / "p_min_cluster.txt"

        # This separator is chosen to comply with the antares_craft timeseries creation
        p_min_cluster.to_csv(p_min_cluster_output, sep="\t", index=False, header=False)

        return InputComponentParameter(
            name="p_min_cluster",
            type="timeseries",
            timeseries=str(p_min_cluster_output).removesuffix(".txt"),
        )

    def get_nb_units_min(self) -> InputComponentParameter:
        p_min_cluster = load_ts_from_txt("p_min_cluster", self.series_path)
        nb_units_min = pd.DataFrame(
            np.ceil(p_min_cluster / self.thermal.properties.nominal_capacity)
        )
        self.nb_units_min_output = self.series_path / "nb_units_min.txt"

        # This separator is chosen to comply with the antares_craft timeseries creation
        nb_units_min.to_csv(
            self.nb_units_min_output, sep="\t", index=False, header=False
        )

        return InputComponentParameter(
            name="nb_units_min",
            type="timeseries",
            timeseries=str(self.nb_units_min_output).removesuffix(".txt"),
        )

    def get_nb_units_max(self) -> InputComponentParameter:
        series_data = self.thermal.get_series_matrix()

        nb_units_max = pd.DataFrame(
            np.ceil(series_data / self.thermal.properties.nominal_capacity)
        )
        nb_units_max_output = self.series_path / "nb_units_max.txt"

        nb_units_max.to_csv(nb_units_max_output, sep="\t", index=False, header=False)
        return InputComponentParameter(
            name="nb_units_max",
            type="timeseries",
            timeseries=str(nb_units_max_output).removesuffix(".txt"),
        )

    def get_nb_units_max_variation_forward(
        self, period: int = 168
    ) -> InputComponentParameter:
        nb_units_max_output = load_ts_from_txt("nb_units_max", self.series_path)
        previous_indices = []
        for i in range(len(nb_units_max_output)):
            previous_indices.append((i - 1) % period + (i // period) * period)

        nb_units_max_output = nb_units_max_output.iloc[previous_indices].reset_index(
            drop=True
        ) - nb_units_max_output.reset_index(drop=True)
        nb_units_max_variation = nb_units_max_output.applymap(lambda x: max(0, x))  # type: ignore
        nb_units_max_variation_output = (
            self.series_path / "nb_units_max_variation_forward.txt"
        )
        nb_units_max_variation.to_csv(
            nb_units_max_variation_output, sep="\t", index=False, header=False
        )
        return InputComponentParameter(
            name="nb_units_max_variation_forward",
            type="timeseries",
            timeseries=str(nb_units_max_variation_output).removesuffix(".txt"),
        )

    def get_nb_units_max_variation_backward(
        self, period: int = 168
    ) -> InputComponentParameter:
        nb_units_max_output = load_ts_from_txt("nb_units_max", self.series_path)
        previous_indices = []
        for i in range(len(nb_units_max_output)):
            previous_indices.append((i - 1) % period + (i // period) * period)

        nb_units_max_output = nb_units_max_output.reset_index(
            drop=True
        ) - nb_units_max_output.iloc[previous_indices].reset_index(drop=True)
        nb_units_max_variation = nb_units_max_output.applymap(lambda x: max(0, x))  # type: ignore
        nb_units_max_variation_output = (
            self.series_path / "nb_units_max_variation_backward.txt"
        )
        nb_units_max_variation.to_csv(
            nb_units_max_variation_output, sep="\t", index=False, header=False
        )
        return InputComponentParameter(
            name="nb_units_max_variation_backward",
            type="timeseries",
            timeseries=str(nb_units_max_variation_output).removesuffix(".txt"),
        )
