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

from andromede.input_converter.src.converter import AntaresStudyConverter
from andromede.input_converter.src.utils import transform_to_yaml
from andromede.study.parsing import (InputComponent, InputComponentParameter,
                                     InputStudy, parse_yaml_components)


class TestConverter:
    def _init_area_reading(self, local_study):
        converter = AntaresStudyConverter(study_input=local_study)
        areas = converter.study.read_areas()
        return areas, converter

    def test_convert_study_to_input_study(self, local_study_w_thermal):
        converter = AntaresStudyConverter(study_input=local_study_w_thermal)
        input_study = converter.convert_study_to_input_study()

        p_max_thermal_timeserie = str(
            converter.study_path
            / "input"
            / "thermal"
            / "series"
            / "fr"
            / "gaz"
            / "series.txt"
        )
        expected_input_study = InputStudy(
            nodes=[
                InputComponent(
                    id="fr",
                    model="area",
                    parameters=[
                        InputComponentParameter(
                            name="energy_cost_unsupplied",
                            type="constant",
                            scenario_group=None,
                            value=1.5,
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
                            value=1.5,
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
                    id="at",
                    model="area",
                    scenario_group=None,
                    parameters=[
                        InputComponentParameter(
                            name="energy_cost_unsupplied",
                            type="constant",
                            scenario_group=None,
                            value=0.0,
                            timeseries=None,
                        ),
                        InputComponentParameter(
                            name="energy_cost_spilled",
                            type="constant",
                            scenario_group=None,
                            value=0.0,
                            timeseries=None,
                        ),
                    ],
                ),
            ],
            components=[
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
                            timeseries=f"{p_max_thermal_timeserie}",
                        ),
                    ],
                )
            ],
            connections=[],
        )

        # To ensure that the comparison between the actual and expected results is not affected by the order of the nodes,
        # both the area_components.nodes and expected_area_components.nodes lists are sorted by the id attribute of each node.
        # This sorting step ensures that the test checks only the presence and validity of the nodes, not their order.
        input_study.nodes.sort(key=lambda x: x.id)
        expected_input_study.nodes.sort(key=lambda x: x.id)

        assert input_study == expected_input_study

    def test_convert_area_to_component(self, local_study_w_areas):
        converter, areas = self._init_area_reading(local_study_w_areas)
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
                        value=1.5,
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
                        value=1.5,
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

    def test_convert_renewables_to_input_study(self, local_study_with_renewable):
        areas, converter = self._init_area_reading(local_study_with_renewable)
        study_path = converter.study_path
        renewables_components = converter._convert_renewable_to_component_list(areas)

        timeserie_path = str(
            study_path
            / "input"
            / "renewables"
            / "series"
            / "fr"
            / "generation"
            / "series.txt"
        )
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

    def test_convert_thermals_to_input_study(self, local_study_w_thermal):
        areas, converter = self._init_area_reading(local_study_w_thermal)

        thermals_components = converter._convert_thermal_to_component_list(areas)

        study_path = converter.study_path
        p_max_timeserie = str(
            study_path / "input" / "thermal" / "series" / "fr" / "gaz" / "series.txt"
        )
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
                            value=1.5,
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
                            value=1.5,
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
        assert validated_data == expected_validated_data
