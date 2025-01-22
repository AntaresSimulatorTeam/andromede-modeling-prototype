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
import pytest

from andromede.input_converter.src.converter import AntaresStudyConverter
from andromede.input_converter.src.logger import Logger
from andromede.input_converter.src.utils import transform_to_yaml
from andromede.study.parsing import (
    InputComponent,
    InputComponentParameter,
    InputPortConnections,
    InputStudy,
    parse_yaml_components,
)


class TestConverter:
    def _init_area_reading(self, local_study):
        logger = Logger(__name__, local_study.service.config.study_path)
        converter = AntaresStudyConverter(study_input=local_study, logger=logger)
        areas = converter.study.read_areas()
        return areas, converter

    def test_convert_study_to_input_study(self, local_study_w_areas):
        logger = Logger(__name__, local_study_w_areas.service.config.study_path)
        converter = AntaresStudyConverter(study_input=local_study_w_areas, logger=logger)
        input_study = converter.convert_study_to_input_study()
        expected_input_study = InputStudy(
            nodes=[
                InputComponent(
                    id="fr",
                    model="area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            name="energy_cost_unsupplied",
                            type="constant",
                            scenario_group=None,
                            value=0.5,
                            timeseries=None,
                        ),
                        InputComponentParameter(
                            name="energy_cost_spilled",
                            type="constant",
                            scenario_group=None,
                            value=1.0,
                            timeseries=None,
                        ),
                    ],
                ),
                InputComponent(
                    id="it",
                    model="area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            name="energy_cost_unsupplied",
                            type="constant",
                            scenario_group=None,
                            value=0.5,
                            timeseries=None,
                        ),
                        InputComponentParameter(
                            name="energy_cost_spilled",
                            type="constant",
                            scenario_group=None,
                            value=1.0,
                            timeseries=None,
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

    def test_convert_area_to_component(self, local_study_w_areas):
        areas, converter = self._init_area_reading(local_study_w_areas)
        area_components = converter._convert_area_to_component_list(areas)

        expected_area_components = [
            InputComponent(
                id="fr",
                model="area",
                parameters=[
                    InputComponentParameter(
                        name="energy_cost_unsupplied",
                        type="constant",
                        scenario_group=None,
                        value=0.5,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="energy_cost_spilled",
                        type="constant",
                        scenario_group=None,
                        value=1.0,
                        timeseries=None,
                    ),
                ],
            ),
            InputComponent(
                id="it",
                model="area",
                parameters=[
                    InputComponentParameter(
                        name="energy_cost_unsupplied",
                        type="constant",
                        scenario_group=None,
                        value=0.5,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="energy_cost_spilled",
                        type="constant",
                        scenario_group=None,
                        value=1.0,
                        timeseries=None,
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

    def test_convert_renewables_to_component(self, local_study_with_renewable):
        areas, converter = self._init_area_reading(local_study_with_renewable)
        study_path = converter.study_path
        (
            renewables_components,
            renewable_connections,
        ) = converter._convert_renewable_to_component_list(areas)

        timeserie_path = str(
            study_path
            / "input"
            / "renewables"
            / "series"
            / "fr"
            / "generation"
            / "series.txt"
        )
        expected_renewable_connections = [
            InputPortConnections(
                component1="generation",
                port_1="balance_port",
                component2="fr",
                port_2="balance_port",
            )
        ]
        expected_renewable_component = [
            InputComponent(
                id="generation",
                model="renewable",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        name="unit_count",
                        type="constant",
                        scenario_group=None,
                        value=1.0,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="nominal_capacity",
                        type="constant",
                        scenario_group=None,
                        value=0.0,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="generation",
                        type="timeseries",
                        scenario_group=None,
                        value=None,
                        timeseries=f"{timeserie_path}",
                    ),
                ],
            )
        ]
        assert renewables_components == expected_renewable_component
        assert renewable_connections == expected_renewable_connections

    def test_convert_thermals_to_component(self, local_study_w_thermal):
        areas, converter = self._init_area_reading(local_study_w_thermal)

        (
            thermals_components,
            thermals_connections,
        ) = converter._convert_thermal_to_component_list(areas)

        study_path = converter.study_path
        p_max_timeserie = str(
            study_path / "input" / "thermal" / "series" / "fr" / "gaz" / "series.txt"
        )
        expected_thermals_connections = [
            InputPortConnections(
                component1="gaz",
                port_1="balance_port",
                component2="fr",
                port_2="balance_port",
            )
        ]
        expected_thermals_components = [
            InputComponent(
                id="gaz",
                model="thermal",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        name="unit_count",
                        type="constant",
                        scenario_group=None,
                        value=1.0,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="efficiency",
                        type="constant",
                        scenario_group=None,
                        value=100.0,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="nominal_capacity",
                        type="constant",
                        scenario_group=None,
                        value=0.0,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="marginal_cost",
                        type="constant",
                        scenario_group=None,
                        value=0.0,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="fixed_cost",
                        type="constant",
                        scenario_group=None,
                        value=0.0,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="startup_cost",
                        type="constant",
                        scenario_group=None,
                        value=0.0,
                        timeseries=None,
                    ),
                    InputComponentParameter(
                        name="p_max_cluster",
                        type="timeseries",
                        scenario_group=None,
                        value=None,
                        timeseries=f"{p_max_timeserie}",
                    ),
                ],
            )
        ]
        assert thermals_components == expected_thermals_components
        assert thermals_connections == expected_thermals_connections

    def test_convert_area_to_yaml(self, local_study_w_areas):
        areas, converter = self._init_area_reading(local_study_w_areas)
        area_components = converter._convert_area_to_component_list(areas)
        input_study = InputStudy(nodes=area_components)

        # Dump model into yaml file
        yaml_path = converter.study_path / "study_path.yaml"
        transform_to_yaml(model=input_study, output_path=yaml_path)

        # Open yaml file to validate
        with open(yaml_path, "r", encoding="utf-8") as yaml_file:
            validated_data = parse_yaml_components(yaml_file)

        expected_validated_data = InputStudy(
            nodes=[
                InputComponent(
                    id="it",
                    model="area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            name="energy_cost_unsupplied",
                            type="constant",
                            scenario_group=None,
                            value=0.5,
                            timeseries=None,
                        ),
                        InputComponentParameter(
                            name="energy_cost_spilled",
                            type="constant",
                            scenario_group=None,
                            value=1.0,
                            timeseries=None,
                        ),
                    ],
                ),
                InputComponent(
                    id="fr",
                    model="area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            name="energy_cost_unsupplied",
                            type="constant",
                            scenario_group=None,
                            value=0.5,
                            timeseries=None,
                        ),
                        InputComponentParameter(
                            name="energy_cost_spilled",
                            type="constant",
                            scenario_group=None,
                            value=1.0,
                            timeseries=None,
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

    def test_convert_solar_to_component(self, local_study_w_areas, fr_solar):
        areas, converter = self._init_area_reading(local_study_w_areas)

        solar_components, solar_connection = converter._convert_solar_to_component_list(
            areas
        )
        study_path = converter.study_path

        solar_timeseries = str(
            study_path / "input" / "solar" / "series" / f"solar_fr.txt"
        )
        expected_solar_connection = [
            InputPortConnections(
                component1="solar",
                port_1="balance_port",
                component2="fr",
                port_2="balance_port",
            )
        ]
        expected_solar_components = InputComponent(
            id="fr",
            model="solar",
            scenario_group=None,
            parameters=[
                InputComponentParameter(
                    name="solar",
                    type="timeseries",
                    scenario_group=None,
                    value=None,
                    timeseries=f"{solar_timeseries}",
                ),
            ],
        )

        assert solar_components[0] == expected_solar_components
        assert solar_connection == expected_solar_connection

    def test_convert_load_to_component(self, local_study_w_areas, fr_load):
        areas, converter = self._init_area_reading(local_study_w_areas)

        load_components, load_connection = converter._convert_load_to_component_list(
            areas
        )
        study_path = converter.study_path

        load_timeseries = str(study_path / "input" / "load" / "series" / f"load_fr.txt")
        expected_load_connection = [
            InputPortConnections(
                component1="load",
                port_1="balance_port",
                component2="fr",
                port_2="balance_port",
            )
        ]
        expected_load_components = InputComponent(
            id="fr",
            model="load",
            scenario_group=None,
            parameters=[
                InputComponentParameter(
                    name="load",
                    type="timeseries",
                    scenario_group=None,
                    value=None,
                    timeseries=f"{load_timeseries}",
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
        self, local_study_w_areas, fr_wind
    ):
        areas, converter = self._init_area_reading(local_study_w_areas)

        wind_components, wind_connection = converter._convert_wind_to_component_list(
            areas
        )
        study_path = converter.study_path

        wind_timeseries = str(study_path / "input" / "wind" / "series" / f"wind_fr.txt")
        expected_wind_connection = [
            InputPortConnections(
                component1="wind",
                port_1="balance_port",
                component2="fr",
                port_2="balance_port",
            )
        ]
        expected_wind_components = InputComponent(
            id="fr",
            model="wind",
            scenario_group=None,
            parameters=[
                InputComponentParameter(
                    name="wind",
                    type="timeseries",
                    scenario_group=None,
                    value=None,
                    timeseries=f"{wind_timeseries}",
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
    def test_convert_wind_to_component_empty_file(self, local_study_w_areas, fr_wind):
        areas, converter = self._init_area_reading(local_study_w_areas)

        wind_components, _ = converter._convert_wind_to_component_list(areas)

        assert wind_components == []

    @pytest.mark.parametrize(
        "fr_wind",
        [
            [0, 0, 0],  # DataFrame full of 0
        ],
        indirect=True,
    )
    def test_convert_wind_to_component_zero_values(self, local_study_w_areas, fr_wind):
        areas, converter = self._init_area_reading(local_study_w_areas)

        wind_components, _ = converter._convert_wind_to_component_list(areas)

        assert wind_components == []

    def test_convert_links_to_component(self, local_study_w_links):
        _, converter = self._init_area_reading(local_study_w_links)
        study_path = converter.study_path
        (
            links_components,
            links_connections,
        ) = converter._convert_link_to_component_list()

        fr_prefix_path = study_path / "input" / "links" / "fr" / "capacities"
        at_prefix_path = study_path / "input" / "links" / "at" / "capacities"
        fr_it_direct_links_timeseries = str(fr_prefix_path / "it_direct.txt")
        fr_it_indirect_links_timeseries = str(fr_prefix_path / "it_indirect.txt")
        at_fr_direct_links_timeseries = str(at_prefix_path / "fr_direct.txt")
        at_fr_indirect_links_timeseries = str(at_prefix_path / "fr_indirect.txt")
        at_it_direct_links_timeseries = str(at_prefix_path / "it_direct.txt")
        at_it_indirect_links_timeseries = str(at_prefix_path / "it_indirect.txt")
        expected_link_component = [
            InputComponent(
                id="fr / it",
                model="link",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        name="capacity_direct",
                        type="timeseries",
                        scenario_group=None,
                        value=None,
                        timeseries=f"{fr_it_direct_links_timeseries}",
                    ),
                    InputComponentParameter(
                        name="capacity_indirect",
                        type="timeseries",
                        scenario_group=None,
                        value=None,
                        timeseries=f"{fr_it_indirect_links_timeseries}",
                    ),
                ],
            ),
            InputComponent(
                id="at / fr",
                model="link",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        name="capacity_direct",
                        type="timeseries",
                        scenario_group=None,
                        value=None,
                        timeseries=f"{at_fr_direct_links_timeseries}",
                    ),
                    InputComponentParameter(
                        name="capacity_indirect",
                        type="timeseries",
                        scenario_group=None,
                        value=None,
                        timeseries=f"{at_fr_indirect_links_timeseries}",
                    ),
                ],
            ),
            InputComponent(
                id="at / it",
                model="link",
                scenario_group=None,
                parameters=[
                    InputComponentParameter(
                        name="capacity_direct",
                        type="timeseries",
                        scenario_group=None,
                        value=None,
                        timeseries=f"{at_it_direct_links_timeseries}",
                    ),
                    InputComponentParameter(
                        name="capacity_indirect",
                        type="timeseries",
                        scenario_group=None,
                        value=None,
                        timeseries=f"{at_it_indirect_links_timeseries}",
                    ),
                ],
            ),
        ]
        expected_link_connections = [
            InputPortConnections(
                component1="fr / it",
                port_1="in_port",
                component2="fr",
                port_2="balance_port",
            ),
            InputPortConnections(
                component1="fr / it",
                port_1="out_port",
                component2="it",
                port_2="balance_port",
            ),
            InputPortConnections(
                component1="at / fr",
                port_1="in_port",
                component2="at",
                port_2="balance_port",
            ),
            InputPortConnections(
                component1="at / fr",
                port_1="out_port",
                component2="fr",
                port_2="balance_port",
            ),
            InputPortConnections(
                component1="at / it",
                port_1="in_port",
                component2="at",
                port_2="balance_port",
            ),
            InputPortConnections(
                component1="at / it",
                port_1="out_port",
                component2="it",
                port_2="balance_port",
            ),
        ]

        assert links_components == expected_link_component
        assert links_connections == expected_link_connections
