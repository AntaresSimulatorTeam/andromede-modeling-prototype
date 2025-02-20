from pathlib import Path

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

    def _write_dataframe_to_csv(self, dataframe: pd.DataFrame, filename: str) -> Path:
        csv_path = self.series_path / filename
        # This separator is chosen to comply with the antares_craft timeseries creation
        dataframe.to_csv(csv_path, sep="\t", index=False, header=False)

        return csv_path

    def _get_p_min_cluster(self) -> pd.DataFrame:
        modulation_data = self.thermal.get_prepro_modulation_matrix().iloc[:, 3]
        series_data = self.thermal.get_series_matrix()

        unit_count = self.thermal.properties.unit_count
        nominal_capacity = self.thermal.properties.nominal_capacity
        modulation_data = modulation_data * nominal_capacity * unit_count

        min_values = pd.concat([modulation_data, series_data], axis=1).min(axis=1)
        return min_values.to_frame(name="p_min_cluster")  # Convert from series to dataframe

    def process_p_min_cluster(self) -> InputComponentParameter:
        p_min_cluster = self._get_p_min_cluster()
        csv_path = self._write_dataframe_to_csv(p_min_cluster, "p_min_cluster.txt")

        return InputComponentParameter(
            id="p_min_cluster",
            time_dependent=True,
            scenario_dependent=True,
            value=str(csv_path).removesuffix(".txt"),
        )

    def _get_nb_units_min(self) -> pd.DataFrame:
        p_min_cluster = load_ts_from_txt("p_min_cluster", self.series_path)
        return pd.DataFrame(
            np.ceil(p_min_cluster / self.thermal.properties.nominal_capacity)
        )

    def process_nb_units_min(self) -> InputComponentParameter:
        nb_units_min = self._get_nb_units_min()
        csv_path = self._write_dataframe_to_csv(nb_units_min, "nb_units_min.txt")

        return InputComponentParameter(
            id="nb_units_min",
            time_dependent=True,
            scenario_dependent=True,
            value=str(csv_path).removesuffix(".txt"),
        )

    def _get_nb_units_max(self) -> pd.DataFrame:
        series_data = self.thermal.get_series_matrix()

        return pd.DataFrame(
            np.ceil(series_data / self.thermal.properties.nominal_capacity)
        )

    def process_nb_units_max(self) -> InputComponentParameter:
        nb_units_max = self._get_nb_units_max()
        csv_path = self._write_dataframe_to_csv(nb_units_max, "nb_units_max.txt")

        return InputComponentParameter(
            id="nb_units_max",
            time_dependent=True,
            scenario_dependent=True,
            value=str(csv_path).removesuffix(".txt"),
        )

    def _get_nb_units_max_variation_forward(self, period: int = 168) -> pd.DataFrame:
        nb_units_max_output = load_ts_from_txt("nb_units_max", self.series_path)
        previous_indices = []
        for i in range(len(nb_units_max_output)):
            previous_indices.append((i - 1) % period + (i // period) * period)
        nb_units_max_output = nb_units_max_output.iloc[previous_indices].reset_index(
            drop=True
        ) - nb_units_max_output.reset_index(drop=True)

        return nb_units_max_output.applymap(lambda x: max(0, x))  # type: ignore

    def process_nb_units_max_variation_forward(
        self, period: int = 168
    ) -> InputComponentParameter:
        nb_units_max_variation = self._get_nb_units_max_variation_forward(period=period)
        csv_path = self._write_dataframe_to_csv(
            nb_units_max_variation, "nb_units_max_variation_forward.txt"
        )

        return InputComponentParameter(
            id="nb_units_max_variation_forward",
            time_dependent=True,
            scenario_dependent=True,
            value=str(csv_path).removesuffix(".txt"),
        )

    def _get_nb_units_max_variation_backward(self, period: int = 168) -> pd.DataFrame:
        nb_units_max_output = load_ts_from_txt("nb_units_max", self.series_path)
        previous_indices = []
        for i in range(len(nb_units_max_output)):
            previous_indices.append((i - 1) % period + (i // period) * period)
        nb_units_max_output = nb_units_max_output.reset_index(
            drop=True
        ) - nb_units_max_output.iloc[previous_indices].reset_index(drop=True)

        return nb_units_max_output.applymap(lambda x: max(0, x))  # type: ignore

    def process_nb_units_max_variation_backward(
        self, period: int = 168
    ) -> InputComponentParameter:
        nb_units_max_variation = self._get_nb_units_max_variation_backward(
            period=period
        )
        csv_path = self._write_dataframe_to_csv(
            nb_units_max_variation, "nb_units_max_variation_backward.txt"
        )

        return InputComponentParameter(
            id="nb_units_max_variation_backward",
            time_dependent=True,
            scenario_dependent=True,
            value=str(csv_path).removesuffix(".txt"),
        )
