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


from andromede.input_converter.src.converter import StudyConverter
from andromede.study.parsing import InputComponent, InputComponents


class TestConverter:
    def test_convert_area_to_input_components(self, local_study_w_areas):
        converter = StudyConverter(study_path=None)
        converter.study = local_study_w_areas
        area_components = converter.convert_study_to_input_components()
        expected_area_components = InputComponents(
            nodes=[
                InputComponent(id="fr", model="area", parameters=None),
                InputComponent(id="it", model="area", parameters=None),
            ],
            components=[],
            connections=[],
        )
        # We add a sort because we want to check only presence and validity of area_components node.
        # Not position
        area_components.nodes.sort(key=lambda x: x.id)
        expected_area_components.nodes.sort(key=lambda x: x.id)

        assert area_components == expected_area_components
