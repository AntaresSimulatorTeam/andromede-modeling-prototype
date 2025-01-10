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
from pathlib import Path
from typing import Union

from antares.craft.model.area import Area
from antares.craft.model.study import Study, read_study_local

from andromede.input_converter.src.utils import resolve_path
from andromede.study.parsing import InputComponent, InputComponentParameter, InputStudy


class AntaresStudyConverter:
    def __init__(self, study_input: Union[Path, Study]):
        """
        Initialize processor
        """
        if isinstance(study_input, Study):
            self.study = study_input
            self.study_path = study_input.service.config.study_path  # type: ignore
        elif isinstance(study_input, Path):
            self.study_path = resolve_path(study_input)
            self.study = read_study_local(self.study_path)
        else:
            raise TypeError("Invalid input type")

    def _convert_area_to_component_list(
        self, areas: list[Area]
    ) -> list[InputComponent]:
        components = []
        for area in areas:
            components.append(
                InputComponent(
                    id=area.id,
                    model="area",
                    parameters=[
                        InputComponentParameter(
                            name="energy_cost_unsupplied",
                            type="constant",
                            value=area.properties.energy_cost_unsupplied,
                        ),
                        InputComponentParameter(
                            name="energy_cost_spilled",
                            type="constant",
                            value=area.properties.energy_cost_spilled,
                        ),
                    ],
                )
            )
        return components

    def _convert_renewable_to_component_list(
        self, areas: list[Area]
    ) -> list[InputComponent]:
        components = []
        for area in areas:
            renewables = area.read_renewables()
            for renewable in renewables:
                series_path = (
                    self.study_path
                    / "input"
                    / "renewables"
                    / "series"
                    / Path(area.id)
                    / Path(renewable.id)
                    / "series.txt"
                )
                components.append(
                    InputComponent(
                        id=renewable.id,
                        model="renewable",
                        parameters=[
                            InputComponentParameter(
                                name="unit_count",
                                type="constant",
                                value=renewable.properties.unit_count,
                            ),
                            InputComponentParameter(
                                name="nominal_capacity",
                                type="constant",
                                value=renewable.properties.nominal_capacity,
                            ),
                            InputComponentParameter(
                                name="generation",
                                type="timeseries",
                                timeseries=str(series_path),
                            ),
                        ],
                    )
                )

        return components

    def _convert_thermal_to_component_list(
        self, areas: list[Area]
    ) -> list[InputComponent]:
        components = []
        # Add thermal components for each area
        for area in areas:
            thermals = area.read_thermal_clusters()
            for thermal in thermals:
                # TODO tous les objets thermal ici sont connectés à l'area area.id
                series_path = (
                    self.study_path
                    / "input"
                    / "thermal"
                    / "series"
                    / Path(area.id)
                    / Path(thermal.name)
                    / "series.txt"
                )
                components.append(
                    InputComponent(
                        id=thermal.id,
                        model="thermal",
                        parameters=[
                            InputComponentParameter(
                                name="unit_count",
                                type="constant",
                                value=thermal.properties.unit_count,
                            ),
                            InputComponentParameter(
                                name="efficiency",
                                type="constant",
                                value=thermal.properties.efficiency,
                            ),
                            InputComponentParameter(
                                name="nominal_capacity",
                                type="constant",
                                value=thermal.properties.nominal_capacity,
                            ),
                            InputComponentParameter(
                                name="marginal_cost",
                                type="constant",
                                value=thermal.properties.marginal_cost,
                            ),
                            InputComponentParameter(
                                name="fixed_cost",
                                type="constant",
                                value=thermal.properties.fixed_cost,
                            ),
                            InputComponentParameter(
                                name="startup_cost",
                                type="constant",
                                value=thermal.properties.startup_cost,
                            ),
                            InputComponentParameter(
                                name="p_max_cluster",
                                type="timeseries",
                                timeseries=str(series_path),
                            ),
                        ],
                    )
                )
        return components

    def _convert_wind_to_component_list(
        self, areas: list[Area]
    ) -> list[InputComponent]:
        components = []

        for area in areas:
            try:
                if area.get_wind_matrix().any:
                    series_path = (
                        self.study_path
                        / "input"
                        / "wind"
                        / "series"
                        / f"wind_{area.id}.txt"
                    )

                    components.append(
                        InputComponent(
                            id=area.id,
                            model="wind",
                            parameters=[
                                InputComponentParameter(
                                    name="wind",
                                    type="timeseries",
                                    timeseries=str(series_path),
                                )
                            ],
                        )
                    )
            except FileNotFoundError:
                pass

        return components

    def _convert_solar_to_component_list(
        self, areas: list[Area]
    ) -> list[InputComponent]:
        components = []

        for area in areas:
            try:
                if area.get_solar_matrix().any:
                    series_path = (
                        self.study_path
                        / "input"
                        / "solar"
                        / "series"
                        / f"solar_{area.id}.txt"
                    )
                    components.extend(
                        [
                            InputComponent(
                                id=area.id,
                                model="solar",
                                parameters=[
                                    InputComponentParameter(
                                        name="solar",
                                        type="timeseries",
                                        timeseries=str(series_path),
                                    )
                                ],
                            )
                        ]
                    )
            except FileNotFoundError:
                pass

        return components

    def _convert_load_to_component_list(
        self, areas: list[Area]
    ) -> list[InputComponent]:
        components = []
        for area in areas:
            try:
                if area.get_load_matrix().any:
                    series_path = (
                        self.study_path
                        / "input"
                        / "load"
                        / "series"
                        / f"load_{area.id}.txt"
                    )
                    components.extend(
                        [
                            InputComponent(
                                id=area.id,
                                model="load",
                                parameters=[
                                    InputComponentParameter(
                                        name="load",
                                        type="timeseries",
                                        timeseries=str(series_path),
                                    )
                                ],
                            )
                        ]
                    )
            except FileNotFoundError:
                pass

        return components

    def convert_study_to_input_study(self) -> InputStudy:
        areas = self.study.read_areas()
        area_components = self._convert_area_to_component_list(areas)
        list_components = []
        list_components.extend(self._convert_renewable_to_component_list(areas))
        list_components.extend(self._convert_thermal_to_component_list(areas))
        list_components.extend(self._convert_load_to_component_list(areas))
        list_components.extend(self._convert_wind_to_component_list(areas))
        list_components.extend(self._convert_solar_to_component_list(areas))

        return InputStudy(nodes=area_components, components=list_components)

    def process_all(self) -> None:
        raise NotImplementedError
