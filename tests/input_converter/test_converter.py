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

from typing import Callable, Literal

import pandas as pd
import pytest
from antares.craft.model.study import Study

from andromede.input_converter.src.converter import AntaresStudyConverter
from andromede.input_converter.src.data_preprocessing.thermal import (
    ThermalDataPreprocessing,
)
from andromede.input_converter.src.logger import Logger
from andromede.input_converter.src.utils import transform_to_yaml
from andromede.study.parsing import (
    InputComponent,
    InputComponentParameter,
    InputPortConnections,
    InputSystem,
    parse_yaml_components,
)


class TestConverter:
    def _init_area_reading(self, local_study):
        logger = Logger(__name__, local_study.service.config.study_path)
        converter = AntaresStudyConverter(study_input=local_study, logger=logger)
        areas = converter.study.get_areas().values()
        return areas, converter

    def test_convert_study_to_input_study(self, local_study_w_areas: Study):
        logger = Logger(__name__, local_study_w_areas.service.config.study_path)
        converter = AntaresStudyConverter(
            study_input=local_study_w_areas, logger=logger
        )
        input_study = converter.convert_study_to_input_study()
        expected_input_study = InputSystem(
            nodes=[
                InputComponent(
                    id="fr",
                    model="antares-historic.area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            id="ens_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            scenario_group=None,
                            value=0.5,
                        ),
                        InputComponentParameter(
                            id="spillage_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            scenario_group=None,
                            value=1.0,
                        ),
                    ],
                ),
                InputComponent(
                    id="it",
                    model="antares-historic.area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            id="ens_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            scenario_group=None,
                            value=0.5,
                        ),
                        InputComponentParameter(
                            id="spillage_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            scenario_group=None,
                            value=1.0,
                        ),
                    ],
                ),
            ],
            components=[],
            connections=[],
        )

        # To ensure that the comparison between the actual and expected results is not affected by the order of the nodes,
        # both the area_components.nodes and expected_area_components.nodes lists are sorted by the id attribute of each node.
        # This sorting step ensures that the test checks only the presence and validity of the nodes, not their order.
        input_study.nodes.sort(key=lambda x: x.id)
        expected_input_study.nodes.sort(key=lambda x: x.id)

        assert input_study == expected_input_study

    def test_convert_area_to_component(self, local_study_w_areas: Study, lib_id: str):
        areas, converter = self._init_area_reading(local_study_w_areas)
        area_components = converter._convert_area_to_component_list(areas, lib_id)

        expected_area_components = [
            InputComponent(
                id="fr",
                model="antares-historic.area",
                parameters=[
                    InputComponentParameter(
                        id="ens_cost",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=0.5,
                    ),
                    InputComponentParameter(
                        id="spillage_cost",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=1.0,
                    ),
                ],
            ),
            InputComponent(
                id="it",
                model="antares-historic.area",
                parameters=[
                    InputComponentParameter(
                        id="ens_cost",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=0.5,
                    ),
                    InputComponentParameter(
                        id="spillage_cost",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=1.0,
                    ),
                ],
            ),
        ]

        # To ensure that the comparison between the actual and expected results is not affected by the order of the nodes,
        # both the area_components.nodes and expected_area_components.nodes lists are sorted by the id attribute of each node.
        # This sorting step ensures that the test checks only the presence and validity of the nodes, not their order.
        expected_area_components.sort(key=lambda x: x.id)
        area_components.sort(key=lambda x: x.id)
        assert area_components == expected_area_components

    def test_convert_renewables_to_component(
        self, local_study_with_renewable: Study, lib_id: str
    ):
        areas, converter = self._init_area_reading(local_study_with_renewable)
        study_path = converter.study_path
        (
            renewables_components,
            renewable_connections,
        ) = converter._convert_renewable_to_component_list(areas, lib_id)

        timeserie_path = str(
            study_path
            / "input"
            / "renewables"
            / "series"
            / "fr"
            / "generation"
            / "series"
        )
        expected_renewable_connections = [
            InputPortConnections(
                component1="generation",
                port1="balance_port",
                component2="fr",
                port2="balance_port",
            )
        ]
        expected_renewable_component = [
            InputComponent(
                id="generation",
                model="antares-historic.renewable",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        id="unit_count",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=1.0,
                    ),
                    InputComponentParameter(
                        id="p_max_unit",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=0.0,
                    ),
                    InputComponentParameter(
                        id="generation",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{timeserie_path}",
                    ),
                ],
            )
        ]
        assert renewables_components == expected_renewable_component
        assert renewable_connections == expected_renewable_connections

    def test_convert_st_storages_to_component(
        self, local_study_with_st_storage, lib_id: str
    ):
        areas, converter = self._init_area_reading(local_study_with_st_storage)
        study_path = converter.study_path
        (
            storage_components,
            storage_connections,
        ) = converter._convert_st_storage_to_component_list(areas, lib_id)

        inflows_path = (
            study_path
            / "input"
            / "st-storage"
            / "series"
            / "fr"
            / "battery"
            / "inflows"
        )
        lower_rule_curve_path = (
            study_path
            / "input"
            / "st-storage"
            / "series"
            / "fr"
            / "battery"
            / "lower-rule-curve"
        )
        pmax_injection_path = (
            study_path
            / "input"
            / "st-storage"
            / "series"
            / "fr"
            / "battery"
            / "PMAX-injection"
        )
        pmax_withdrawal_path = (
            study_path
            / "input"
            / "st-storage"
            / "series"
            / "fr"
            / "battery"
            / "PMAX-withdrawal"
        )
        upper_rule_curve_path = (
            study_path
            / "input"
            / "st-storage"
            / "series"
            / "fr"
            / "battery"
            / "upper-rule-curve"
        )
        expected_storage_connections = [
            InputPortConnections(
                component1="battery",
                port1="injection_port",
                component2="fr",
                port2="balance_port",
            )
        ]
        expected_storage_component = [
            InputComponent(
                id="battery",
                model=f"{lib_id}.short-term-storage",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        id="efficiency_injection",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=1,
                    ),
                    InputComponentParameter(
                        id="initial_level",
                        time_dependent=False,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=0.5,
                    ),
                    InputComponentParameter(
                        id="reservoir_capacity",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=0.0,
                    ),
                    InputComponentParameter(
                        id="injection_nominal_capacity",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=10.0,
                    ),
                    InputComponentParameter(
                        id="withdrawal_nominal_capacity",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=10.0,
                    ),
                    InputComponentParameter(
                        id="inflows",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{inflows_path}",
                    ),
                    InputComponentParameter(
                        id="lower_rule_curve",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{lower_rule_curve_path}",
                    ),
                    InputComponentParameter(
                        id="p_max_injection_modulation",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{pmax_injection_path}",
                    ),
                    InputComponentParameter(
                        id="p_max_withdrawal_modulation",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{pmax_withdrawal_path}",
                    ),
                    InputComponentParameter(
                        id="upper_rule_curve",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{upper_rule_curve_path}",
                    ),
                ],
            )
        ]

        assert storage_components == expected_storage_component
        assert storage_connections == expected_storage_connections

    def test_convert_thermals_to_component(
        self,
        local_study_w_thermal: Study,
        create_csv_from_constant_value: Callable[..., None],
        lib_id: str,
    ):
        areas, converter = self._init_area_reading(local_study_w_thermal)
        study_path = converter.study_path
        # I just want to fill the modulation and series files
        modulation_timeseries = (
            study_path / "input" / "thermal" / "prepro" / "fr" / "gaz"
        )
        series_path = study_path / "input" / "thermal" / "series" / "fr" / "gaz"
        # We have to use a multiple of 168, to match with full weeks
        create_csv_from_constant_value(modulation_timeseries, "modulation", 840, 4)
        create_csv_from_constant_value(series_path, "series", 840)

        self._generate_tdp_instance_parameter(
            areas, study_path, create_dataframes=False
        )
        (
            thermals_components,
            thermals_connections,
        ) = converter._convert_thermal_to_component_list(areas, lib_id)

        study_path = converter.study_path
        p_max_timeserie = str(
            study_path / "input" / "thermal" / "series" / "fr" / "gaz" / "series"
        )
        p_min_cluster = str(
            study_path / "input" / "thermal" / "series" / "fr" / "gaz" / "p_min_cluster"
        )
        nb_units_min = str(
            study_path / "input" / "thermal" / "series" / "fr" / "gaz" / "nb_units_min"
        )
        nb_units_max = str(
            study_path / "input" / "thermal" / "series" / "fr" / "gaz" / "nb_units_max"
        )
        nb_units_max_variation_forward = str(
            study_path
            / "input"
            / "thermal"
            / "series"
            / "fr"
            / "gaz"
            / "nb_units_max_variation_forward"
        )
        nb_units_max_variation_backward = str(
            study_path
            / "input"
            / "thermal"
            / "series"
            / "fr"
            / "gaz"
            / "nb_units_max_variation_backward"
        )
        expected_thermals_connections = [
            InputPortConnections(
                component1="gaz",
                port1="balance_port",
                component2="fr",
                port2="balance_port",
            )
        ]
        expected_thermals_components = [
            InputComponent(
                id="gaz",
                model="antares-historic.thermal",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        id="p_min_cluster",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{p_min_cluster}",
                    ),
                    InputComponentParameter(
                        id="nb_units_min",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{nb_units_min}",
                    ),
                    InputComponentParameter(
                        id="nb_units_max",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{nb_units_max}",
                    ),
                    InputComponentParameter(
                        id="nb_units_max_variation_forward",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{nb_units_max_variation_forward}",
                    ),
                    InputComponentParameter(
                        id="nb_units_max_variation_backward",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{nb_units_max_variation_backward}",
                    ),
                    InputComponentParameter(
                        id="unit_count",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=1.0,
                    ),
                    InputComponentParameter(
                        id="p_min_unit",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=0.0,
                    ),
                    InputComponentParameter(
                        id="efficiency",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=100.0,
                    ),
                    InputComponentParameter(
                        id="p_max_unit",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=2.0,
                    ),
                    InputComponentParameter(
                        id="generation_cost",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=0.0,
                    ),
                    InputComponentParameter(
                        id="fixed_cost",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=0.0,
                    ),
                    InputComponentParameter(
                        id="startup_cost",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=0.0,
                    ),
                    InputComponentParameter(
                        id="d_min_up",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=1.0,
                    ),
                    InputComponentParameter(
                        id="d_min_down",
                        time_dependent=False,
                        scenario_dependent=False,
                        scenario_group=None,
                        value=1.0,
                    ),
                    InputComponentParameter(
                        id="p_max_cluster",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{p_max_timeserie}",
                    ),
                ],
            )
        ]
        print("ACTUAL:", thermals_components)
        print("EXPECTED:", expected_thermals_components)

        assert thermals_components == expected_thermals_components
        assert thermals_connections == expected_thermals_connections

    def test_convert_area_to_yaml(self, local_study_w_areas: Study, lib_id: str):
        areas, converter = self._init_area_reading(local_study_w_areas)
        area_components = converter._convert_area_to_component_list(areas, lib_id)
        input_study = InputSystem(nodes=area_components)

        # Dump model into yaml file
        yaml_path = converter.study_path / "study_path.yaml"
        transform_to_yaml(model=input_study, output_path=yaml_path)

        # Open yaml file to validate
        with open(yaml_path, "r", encoding="utf-8") as yaml_file:
            validated_data = parse_yaml_components(yaml_file)

        expected_validated_data = InputSystem(
            nodes=[
                InputComponent(
                    id="it",
                    model="antares-historic.area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            id="ens_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            scenario_group=None,
                            value=0.5,
                        ),
                        InputComponentParameter(
                            id="spillage_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            scenario_group=None,
                            value=1.0,
                        ),
                    ],
                ),
                InputComponent(
                    id="fr",
                    model="antares-historic.area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            id="ens_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            scenario_group=None,
                            value=0.5,
                        ),
                        InputComponentParameter(
                            id="spillage_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            scenario_group=None,
                            value=1.0,
                        ),
                    ],
                ),
            ],
            components=[],
            connections=[],
        )

        expected_validated_data.nodes.sort(key=lambda x: x.id)
        validated_data.nodes.sort(key=lambda x: x.id)
        assert validated_data == expected_validated_data

    def test_convert_solar_to_component(
        self, local_study_w_areas: Study, fr_solar: None, lib_id: str
    ):
        areas, converter = self._init_area_reading(local_study_w_areas)

        solar_components, solar_connection = converter._convert_solar_to_component_list(
            areas, lib_id
        )
        study_path = converter.study_path

        solar_timeseries = str(study_path / "input" / "solar" / "series" / "solar_fr")
        expected_solar_connection = [
            InputPortConnections(
                component1="solar",
                port1="balance_port",
                component2="fr",
                port2="balance_port",
            )
        ]
        expected_solar_components = InputComponent(
            id="fr",
            model="antares-historic.solar",
            scenario_group=None,
            parameters=[
                InputComponentParameter(
                    id="solar",
                    time_dependent=True,
                    scenario_dependent=True,
                    scenario_group=None,
                    value=f"{solar_timeseries}",
                ),
            ],
        )

        assert solar_components[0] == expected_solar_components
        assert solar_connection == expected_solar_connection

    def test_convert_load_to_component(
        self, local_study_w_areas: Study, fr_load: None, lib_id: str
    ):
        areas, converter = self._init_area_reading(local_study_w_areas)

        load_components, load_connection = converter._convert_load_to_component_list(
            areas, lib_id
        )
        study_path = converter.study_path

        load_timeseries = str(study_path / "input" / "load" / "series" / "load_fr")
        expected_load_connection = [
            InputPortConnections(
                component1="load",
                port1="balance_port",
                component2="fr",
                port2="balance_port",
            )
        ]
        expected_load_components = InputComponent(
            id="load",
            model="antares-historic.load",
            scenario_group=None,
            parameters=[
                InputComponentParameter(
                    id="load",
                    time_dependent=True,
                    scenario_dependent=True,
                    scenario_group=None,
                    value=f"{load_timeseries}",
                ),
            ],
        )

        assert load_components[0] == expected_load_components
        assert load_connection == expected_load_connection

    @pytest.mark.parametrize(
        "fr_wind",
        [
            [1, 1, 1],  # Dataframe filled with 1
        ],
        indirect=True,
    )
    def test_convert_wind_to_component_not_empty_file(
        self, local_study_w_areas: Study, fr_wind: int, lib_id: str
    ):
        areas, converter = self._init_area_reading(local_study_w_areas)

        wind_components, wind_connection = converter._convert_wind_to_component_list(
            areas, lib_id
        )
        study_path = converter.study_path

        wind_timeseries = str(study_path / "input" / "wind" / "series" / "wind_fr")
        expected_wind_connection = [
            InputPortConnections(
                component1="wind",
                port1="balance_port",
                component2="fr",
                port2="balance_port",
            )
        ]
        expected_wind_components = InputComponent(
            id="fr",
            model="antares-historic.wind",
            scenario_group=None,
            parameters=[
                InputComponentParameter(
                    id="wind",
                    time_dependent=True,
                    scenario_dependent=True,
                    scenario_group=None,
                    value=f"{wind_timeseries}",
                ),
            ],
        )

        assert wind_components[0] == expected_wind_components
        assert wind_connection == expected_wind_connection

    @pytest.mark.parametrize(
        "fr_wind",
        [
            [],  # DataFrame empty
        ],
        indirect=True,
    )
    def test_convert_wind_to_component_empty_file(
        self, local_study_w_areas: Study, fr_wind: object, lib_id: str
    ):
        areas, converter = self._init_area_reading(local_study_w_areas)

        wind_components, _ = converter._convert_wind_to_component_list(areas, lib_id)

        assert wind_components == []

    @pytest.mark.parametrize(
        "fr_wind",
        [
            [0, 0, 0],  # DataFrame full of 0
        ],
        indirect=True,
    )
    def test_convert_wind_to_component_zero_values(
        self, local_study_w_areas: Study, fr_wind: int, lib_id: str
    ):
        areas, converter = self._init_area_reading(local_study_w_areas)

        wind_components, _ = converter._convert_wind_to_component_list(areas, lib_id)

        assert wind_components == []

    def test_convert_links_to_component(self, local_study_w_links: Study, lib_id: str):
        _, converter = self._init_area_reading(local_study_w_links)
        study_path = converter.study_path
        (
            links_components,
            links_connections,
        ) = converter._convert_link_to_component_list(lib_id)

        fr_prefix_path = study_path / "input" / "links" / "fr" / "capacities"
        at_prefix_path = study_path / "input" / "links" / "at" / "capacities"
        fr_it_direct_links_timeseries = str(fr_prefix_path / "it_direct")
        fr_it_indirect_links_timeseries = str(fr_prefix_path / "it_indirect")
        at_fr_direct_links_timeseries = str(at_prefix_path / "fr_direct")
        at_fr_indirect_links_timeseries = str(at_prefix_path / "fr_indirect")
        at_it_direct_links_timeseries = str(at_prefix_path / "it_direct")
        at_it_indirect_links_timeseries = str(at_prefix_path / "it_indirect")
        expected_link_component = [
            InputComponent(
                id="fr / it",
                model="antares-historic.link",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        id="capacity_direct",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{fr_it_direct_links_timeseries}",
                    ),
                    InputComponentParameter(
                        id="capacity_indirect",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{fr_it_indirect_links_timeseries}",
                    ),
                ],
            ),
            InputComponent(
                id="at / fr",
                model="antares-historic.link",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        id="capacity_direct",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{at_fr_direct_links_timeseries}",
                    ),
                    InputComponentParameter(
                        id="capacity_indirect",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{at_fr_indirect_links_timeseries}",
                    ),
                ],
            ),
            InputComponent(
                id="at / it",
                model="antares-historic.link",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        id="capacity_direct",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{at_it_direct_links_timeseries}",
                    ),
                    InputComponentParameter(
                        id="capacity_indirect",
                        time_dependent=True,
                        scenario_dependent=True,
                        scenario_group=None,
                        value=f"{at_it_indirect_links_timeseries}",
                    ),
                ],
            ),
        ]
        expected_link_connections = [
            InputPortConnections(
                component1="at / fr",
                port1="in_port",
                component2="at",
                port2="balance_port",
            ),
            InputPortConnections(
                component1="at / fr",
                port1="out_port",
                component2="fr",
                port2="balance_port",
            ),
            InputPortConnections(
                component1="at / it",
                port1="in_port",
                component2="at",
                port2="balance_port",
            ),
            InputPortConnections(
                component1="at / it",
                port1="out_port",
                component2="it",
                port2="balance_port",
            ),
            InputPortConnections(
                component1="fr / it",
                port1="in_port",
                component2="fr",
                port2="balance_port",
            ),
            InputPortConnections(
                component1="fr / it",
                port1="out_port",
                component2="it",
                port2="balance_port",
            ),
        ]

        assert sorted(links_components, key=lambda x: x.id) == sorted(
            expected_link_component, key=lambda x: x.id
        )
        assert links_connections == expected_link_connections

    def _generate_tdp_instance_parameter(
        self, areas, study_path, create_dataframes: bool = True
    ):
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

    def _setup_test(self, local_study_w_thermal, filename):
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
        self, instance, process_method, expected_path, expected_values
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

    def _test_p_min_cluster(self, local_study_w_thermal):
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
