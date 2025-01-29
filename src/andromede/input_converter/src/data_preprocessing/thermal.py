from pathlib import Path

import numpy as np
import pandas as pd
from antares.craft.model.thermal import ThermalCluster

from andromede.study.parsing import InputComponentParameter


class ThermalDataPreprocessing:
    def __init__(self, thermal: ThermalCluster, study_path: Path):
        self.thermal = thermal
        self.study_path = study_path

        self.p_min_cluster_output = None
        self.nb_units_min_output = None
        self.nb_units_max_output = None

    def get_p_min_cluster_parameter(self):
        modulation_data = self.thermal.get_prepro_modulation_matrix().iloc[:, 3]
        series_data = self.thermal.get_series_matrix()

        unit_count = self.thermal.properties.unit_count
        nominal_capacity = self.thermal.properties.nominal_capacity
        modulation_data = modulation_data * nominal_capacity * unit_count

        p_min_cluster = pd.concat([modulation_data, series_data], axis=1).min(axis=1)

        self.p_min_cluster_output = (
            self.study_path
            / "input"
            / "thermal"
            / "prepro"
            / self.thermal.area_id
            / self.thermal.id
            / "p_min_cluster.txt"
        )

        # This separator is chosen to comply with the antares_craft timeseries creation
        p_min_cluster.to_csv(
            self.p_min_cluster_output, sep="\t", index=False, header=False
        )

        return InputComponentParameter(
            name="p_min_cluster",
            type="series",
            timeseries=str(self.p_min_cluster_output),
        )

    def get_nb_units_min(self):
        p_min_cluster = pd.read_csv(self.p_min_cluster_output, header=None)

        nb_units_min = np.ceil(p_min_cluster / self.thermal.properties.nominal_capacity)
        self.nb_units_min_output = (
            self.study_path
            / "input"
            / "thermal"
            / "prepro"
            / self.thermal.area_id
            / self.thermal.id
            / "nb_units_min.txt"
        )

        # This separator is chosen to comply with the antares_craft timeseries creation
        nb_units_min.to_csv(
            self.nb_units_min_output, sep="\t", index=False, header=False
        )

        return InputComponentParameter(
            name="nb_units_min",
            type="series",
            timeseries=str(self.nb_units_min_output),
        )

    def get_nb_units_max(self):
        series_data = self.thermal.get_series_matrix()

        nb_units_max = np.ceil(series_data / self.thermal.properties.nominal_capacity)
        self.nb_units_max_output = (
            self.study_path
            / "input"
            / "thermal"
            / "prepro"
            / self.thermal.area_id
            / self.thermal.id
            / "nb_units_max.txt"
        )

        nb_units_max.to_csv(
            self.nb_units_max_output, sep="\t", index=False, header=False
        )
        return InputComponentParameter(
            name="nb_units_max",
            type="series",
            timeseries=str(self.nb_units_max_output),
        )

    def get_nb_units_max_variation(self):
        nb_units_max_output = pd.read_csv(self.nb_units_max_output, header=None)
        nb_units_max_output = nb_units_max_output.shift(1) - nb_units_max_output
        nb_units_max_variation = nb_units_max_output.applymap(lambda x: max(0, x))
        nb_units_max_variation_output = (
            self.study_path
            / "input"
            / "thermal"
            / "prepro"
            / self.thermal.area_id
            / self.thermal.id
            / "nb_units_max_variation_output.txt"
        )
        nb_units_max_variation.to_csv(
            nb_units_max_variation_output, sep="\t", index=False, header=False
        )
        return InputComponentParameter(
            name="nb_units_max_variation",
            type="series",
            timeseries=str(nb_units_max_variation_output),
        )
