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


from andromede.input_converter.src.utils import convert_area_to_components
from andromede.study.parsing import InputComponent, InputComponents


class TestConverter:
    def test_convert_area_to_input_components(self, local_study_w_areas):
        areas = local_study_w_areas.read_areas()
        area_components = convert_area_to_components(areas)
        expected_area_components = InputComponents(
        nodes=[
            InputComponent(id="it", model="area", parameters=None),
            InputComponent(id="fr", model="area", parameters=None),
        ],
        components=[],
        connections=[]
        )
        assert area_components == expected_area_components

