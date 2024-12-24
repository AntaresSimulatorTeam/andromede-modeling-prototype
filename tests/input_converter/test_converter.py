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
from andromede.input_converter.src.utils import (
    convert_area_to_component_list,
    convert_renewable_to_component_list,
)
from andromede.study.parsing import InputComponent, InputStudy, parse_yaml_components


class TestConverter:
    def test_convert_area_to_input_study(self, local_study_w_areas):
        converter = AntaresStudyConverter(study_path=None)
        converter.study = local_study_w_areas
        areas = converter.study.read_areas()
        area_components = convert_area_to_component_list(areas)
        input_study = InputStudy(nodes=area_components)
        expected_area_components = InputStudy(
            nodes=[
                InputComponent(id="fr", model="area", parameters=None),
                InputComponent(id="it", model="area", parameters=None),
            ],
            components=[],
            connections=[],
        )
        # To ensure that the comparison between the actual and expected results is not affected by the order of the nodes,
        # both the area_components.nodes and expected_area_components.nodes lists are sorted by the id attribute of each node.
        # This sorting step ensures that the test checks only the presence and validity of the nodes, not their order.
        input_study.nodes.sort(key=lambda x: x.id)
        expected_area_components.nodes.sort(key=lambda x: x.id)

        assert input_study == expected_area_components

    def test_convert_area_to_yaml(self, local_study_w_areas):
        converter = AntaresStudyConverter(study_path=None)

        converter.study = local_study_w_areas
        areas = converter.study.read_areas()
        area_components = convert_area_to_component_list(areas)
        input_study = InputStudy(nodes=area_components)

        # Dump model into yaml file
        yaml_path = local_study_w_areas.service.config.study_path / "study_path.yaml"
        converter.transform_to_yaml(model=input_study, output_path=yaml_path)

        # Open yaml file to validate
        with open(yaml_path, "r") as yaml_file:
            validated_data = parse_yaml_components(yaml_file)

        assert isinstance(
            validated_data, InputStudy
        ), "Validated datas don't match InputStudy model"
        assert len(validated_data.nodes) == 2, "Yaml file must contain 2 nodes"

    def test_convert_renewables_to_input_study(self, local_study_with_renewable):
        converter = AntaresStudyConverter(study_path=None)

        converter.study = local_study_with_renewable
        areas = converter.study.read_areas()
        area_components = convert_area_to_component_list(areas)
        study_path = local_study_with_renewable.service.config.study_path

        renewables_components = convert_renewable_to_component_list(areas, study_path)

        input_study = InputStudy(
            nodes=area_components, components=renewables_components
        )
        expected_area_components = InputStudy(
            nodes=[
                InputComponent(id="fr", model="area", parameters=None),
                InputComponent(id="it", model="area", parameters=None),
                InputComponent(id="at", model="area", parameters=None),
            ],
            components=[],
            connections=[],
        )
        timeserie_path = str(
            study_path
            / "input"
            / "renewables"
            / "series"
            / "fr"
            / "renewable cluster"
            / "series.txt"
        )

        assert renewables_components[0].id == "renewable cluster"
        assert renewables_components[0].parameters[0].name == "unit_count"
        assert renewables_components[0].parameters[1].name == "nominal_capacity"
        assert renewables_components[0].parameters[1].type == "constant"
        assert renewables_components[0].parameters[2].name == "renewable cluster"
        assert renewables_components[0].parameters[2].type == "timeseries"
        assert renewables_components[0].parameters[2].timeseries == timeserie_path
        # To ensure that the comparison between the actual and expected results is not affected by the order of the nodes,
        # both the area_components.nodes and expected_area_components.nodes lists are sorted by the id attribute of each node.
        # This sorting step ensures that the test checks only the presence and validity of the nodes, not their order.
        input_study.nodes.sort(key=lambda x: x.id)
        expected_area_components.nodes.sort(key=lambda x: x.id)

        assert input_study.nodes == expected_area_components.nodes
