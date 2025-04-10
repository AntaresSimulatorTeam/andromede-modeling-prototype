from pathlib import Path
from typing import Callable, Literal

import pandas as pd
import pytest
from antares.craft.model.study import Study

from andromede.input_converter.src.converter import AntaresStudyConverter
from andromede.input_converter.src.data_preprocessing.thermal import (
    ThermalDataPreprocessing,
)
from andromede.input_converter.src.logger import Logger
from andromede.study.parsing import InputComponentParameter


class TestPreprocessingThermal:
    def _init_area_reading(self, local_study: Study):
        logger = Logger(__name__, local_study.service.config.study_path)
        converter = AntaresStudyConverter(study_input=local_study, logger=logger)
        areas = converter.study.get_areas().values()
        return areas, converter

    def _generate_tdp_instance_parameter(
        self, areas, study_path: Path, create_dataframes: bool = True
    ) -> ThermalDataPreprocessing:
        if create_dataframes:
            modulation_timeseries = str(
                study_path
                / "input"
                / "thermal"
                / "prepro"
                / "fr"
                / "gaz"
                / "modulation.txt"
            )
            series_path = (
                study_path
                / "input"
                / "thermal"
                / "series"
                / "fr"
                / "gaz"
                / "series.txt"
            )
            data_p_max = [
                [1, 1, 1, 2],
                [2, 2, 2, 6],
                [3, 3, 3, 1],
            ]
            data_series = [
                [8],
                [10],
                [2],
            ]
            df = pd.DataFrame(data_p_max)
            df.to_csv(modulation_timeseries, sep="\t", index=False, header=False)

            df = pd.DataFrame(data_series)
            df.to_csv(series_path, sep="\t", index=False, header=False)

        for area in areas:
            thermals = area.get_thermals()
            for thermal in thermals.values():
                if thermal.area_id == "fr":
                    tdp = ThermalDataPreprocessing(thermal, study_path)
                    return tdp

    def _setup_test(self, local_study_w_thermal: Study, filename: Path):
        """
        Initializes test parameters and returns the instance and expected file path.
        """
        areas, converter = self._init_area_reading(local_study_w_thermal)
        study_path = converter.study_path
        instance = self._generate_tdp_instance_parameter(areas, study_path)
        expected_path = (
            study_path / "input" / "thermal" / "series" / "fr" / "gaz" / filename
        )
        return instance, expected_path

    def _validate_component(
        self,
        instance: ThermalDataPreprocessing,
        process_method: str,
        expected_path: Path,
        expected_values: list,
    ):
        """
        Executes the given processing method, validates the component, and compares the output dataframe.
        """
        component = getattr(instance, process_method)()
        expected_component = InputComponentParameter(
            id=process_method.split("process_")[1],
            time_dependent=True,
            scenario_dependent=True,
            value=str(expected_path),
        )
        current_df = pd.read_csv(expected_path.with_suffix(".txt"), header=None)
        expected_df = pd.DataFrame(expected_values)
        assert current_df.equals(expected_df)
        assert component == expected_component

    def _test_p_min_cluster(self, local_study_w_thermal: Study):
        """Tests the p_min_cluster parameter processing."""
        instance, expected_path = self._setup_test(
            local_study_w_thermal, "p_min_cluster.txt"
        )
        expected_values = [
            [6.0],
            [10.0],
            [2.0],
        ]  # min(min_gen_modulation * unit_count * nominal_capacity, p_max_cluster)
        self._validate_component(
            instance, "process_p_min_cluster", expected_path, expected_values
        )

    def test_nb_units_min(self, local_study_w_thermal: Study):
        """Tests the nb_units_min parameter processing."""
        instance, expected_path = self._setup_test(
            local_study_w_thermal, "nb_units_min"
        )
        instance.process_p_min_cluster()
        expected_values = [[2.0], [5.0], [1.0]]  # ceil(p_min_cluster / p_max_unit)
        self._validate_component(
            instance, "process_nb_units_min", expected_path, expected_values
        )

    def test_nb_units_max(self, local_study_w_thermal: Study):
        """Tests the nb_units_max parameter processing."""
        instance, expected_path = self._setup_test(
            local_study_w_thermal, "nb_units_max"
        )
        instance.process_p_min_cluster()
        expected_values = [[4.0], [5.0], [1.0]]  # ceil(p_max_cluster / p_max_unit)
        self._validate_component(
            instance, "process_nb_units_max", expected_path, expected_values
        )

    @pytest.mark.parametrize("direction", ["forward", "backward"])
    def test_nb_units_max_variation(
        self,
        local_study_w_thermal: Study,
        create_csv_from_constant_value: Callable[..., None],
        direction: Literal["forward"] | Literal["backward"],
    ):
        """
        Tests nb_units_max_variation_forward and nb_units_max_variation_backward processing.
        """
        instance, expected_path = self._setup_test(
            local_study_w_thermal, f"nb_units_max_variation_{direction}"
        )
        modulation_timeseries = (
            instance.study_path / "input" / "thermal" / "prepro" / "fr" / "gaz"
        )
        series_path = (
            instance.study_path / "input" / "thermal" / "series" / "fr" / "gaz"
        )
        create_csv_from_constant_value(modulation_timeseries, "modulation", 840, 4)
        create_csv_from_constant_value(series_path, "series", 840)
        instance.process_nb_units_max()
        nb_units_max_output = pd.read_csv(
            instance.series_path / "nb_units_max.txt", header=None
        )

        variation_component = getattr(
            instance, f"process_nb_units_max_variation_{direction}"
        )()
        current_df = pd.read_csv(variation_component.value + ".txt", header=None)

        assert current_df[0][0] == max(
            0, nb_units_max_output[0][167] - nb_units_max_output[0][0]
        )
        assert current_df[0][3] == max(
            0, nb_units_max_output[0][2] - nb_units_max_output[0][3]
        )
        assert current_df[0][168] == max(
            0, nb_units_max_output[0][335] - nb_units_max_output[0][168]
        )
        assert variation_component.value == str(expected_path)

    def test_nb_units_max_variation_forward(
        self,
        local_study_w_thermal: Study,
        create_csv_from_constant_value: Callable[..., None],
    ):
        self.test_nb_units_max_variation(
            local_study_w_thermal, create_csv_from_constant_value, direction="forward"
        )

    def test_nb_units_max_variation_backward(
        self,
        local_study_w_thermal: Study,
        create_csv_from_constant_value: Callable[..., None],
    ):
        self.test_nb_units_max_variation(
            local_study_w_thermal, create_csv_from_constant_value, direction="backward"
        )
