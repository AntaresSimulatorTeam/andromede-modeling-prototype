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
import logging
from pathlib import Path
from typing import Optional, Union

from antares.craft.model.area import Area
from antares.craft.model.study import Study, read_study_local
from pandas import DataFrame

from andromede.input_converter.src.data_preprocessing.thermal import (
    ThermalDataPreprocessing,
)
from andromede.input_converter.src.utils import resolve_path, transform_to_yaml
from andromede.study.parsing import (
    InputComponent,
    InputComponentParameter,
    InputPortConnections,
    InputStudy,
)


class AntaresStudyConverter:
    def __init__(
        self,
        study_input: Union[Path, Study],
        logger: logging.Logger,
        output_path: Optional[Path] = None,
        period: Optional[int] = None,
    ):
        """
        Initialize processor
        """
        self.logger = logger
        self.period = period if period else 168

        if isinstance(study_input, Study):
            self.study = study_input
            self.study_path = study_input.service.config.study_path  # type: ignore
        elif isinstance(study_input, Path):
            self.study_path = resolve_path(study_input)
            self.study = read_study_local(self.study_path)
        else:
            raise TypeError("Invalid input type")

        self.output_path = (
            Path(output_path) if output_path else self.study_path / Path("output.yaml")
        )

    def _check_dataframe_validity(self, df: DataFrame) -> bool:
        """
        Check and validate the following conditions:
        1. The dataframe from this path is not empty.
        2. The dataframe does not contains only zero values.

        :param df: dataframe to validate.
        """
        if df.empty or (df == 0).all().all():
            return False

        return True

    def _convert_area_to_component_list(
        self, areas: list[Area]
    ) -> list[InputComponent]:
        components = []
        self.logger.info("Converting areas to component list...")
        for area in areas:
            components.append(
                InputComponent(
                    id=area.id,
                    model="area",
                    parameters=[
                        InputComponentParameter(
                            id="ens_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            value=area.properties.energy_cost_unsupplied,
                        ),
                        InputComponentParameter(
                            id="spillage_cost",
                            time_dependent=False,
                            scenario_dependent=False,
                            value=area.properties.energy_cost_spilled,
                        ),
                    ],
                )
            )
        return components

    def _convert_renewable_to_component_list(
        self, areas: list[Area]
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        components = []
        connections = []
        self.logger.info("Converting renewables to component list...")
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
                                id="unit_count",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=renewable.properties.unit_count,
                            ),
                            InputComponentParameter(
                                id="p_max_unit",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=renewable.properties.nominal_capacity,
                            ),
                            InputComponentParameter(
                                id="generation",
                                time_dependent=True,
                                scenario_dependent=True,
                                value=str(series_path).removesuffix(".txt"),
                            ),
                        ],
                    )
                )
                connections.append(
                    InputPortConnections(
                        component1=renewable.id,
                        port1="balance_port",
                        component2=area.id,
                        port2="balance_port",
                    )
                )

        return components, connections

    def _convert_thermal_to_component_list(
        self, areas: list[Area]
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        components = []
        connections = []
        self.logger.info("Converting thermals to component list...")
        # Add thermal components for each area

        for area in areas:
            thermals = area.read_thermal_clusters()
            for thermal in thermals:
                series_path = (
                    self.study_path
                    / "input"
                    / "thermal"
                    / "series"
                    / Path(thermal.area_id)
                    / Path(thermal.id)
                    / "series.txt"
                )
                tdp = ThermalDataPreprocessing(thermal, self.study_path)
                components.append(
                    InputComponent(
                        id=thermal.id,
                        model="thermal",
                        parameters=[
                            tdp.process_p_min_cluster(),
                            tdp.process_nb_units_min(),
                            tdp.process_nb_units_max(),
                            tdp.process_nb_units_max_variation_forward(self.period),
                            tdp.process_nb_units_max_variation_backward(self.period),
                            InputComponentParameter(
                                id="unit_count",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.unit_count,
                            ),
                            InputComponentParameter(
                                id="p_min_unit",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.min_stable_power,
                            ),
                            InputComponentParameter(
                                id="efficiency",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.efficiency,
                            ),
                            InputComponentParameter(
                                id="p_max_unit",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.nominal_capacity,
                            ),
                            InputComponentParameter(
                                id="generation_cost",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.marginal_cost,
                            ),
                            InputComponentParameter(
                                id="fixed_cost",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.fixed_cost,
                            ),
                            InputComponentParameter(
                                id="startup_cost",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.startup_cost,
                            ),
                            InputComponentParameter(
                                id="d_min_up",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.min_up_time,
                            ),
                            InputComponentParameter(
                                id="d_min_down",
                                time_dependent=False,
                                scenario_dependent=False,
                                value=thermal.properties.min_down_time,
                            ),
                            InputComponentParameter(
                                id="p_max_cluster",
                                time_dependent=True,
                                scenario_dependent=True,
                                value=str(series_path).removesuffix(".txt"),
                            ),
                        ],
                    )
                )

                connections.append(
                    InputPortConnections(
                        component1=thermal.id,
                        port1="balance_port",
                        component2=area.id,
                        port2="balance_port",
                    )
                )
        return components, connections

    def _convert_link_to_component_list(
        self,
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        components = []
        connections = []
        self.logger.info("Converting links to component list...")
        # Add links components for each area
        links = self.study.read_links()
        for link in links:
            capacity_direct_path = (
                self.study_path
                / "input"
                / "links"
                / Path(link.area_from_id)
                / "capacities"
                / f"{link.area_to_id}_direct"
            )
            capacity_indirect_path = (
                self.study_path
                / "input"
                / "links"
                / Path(link.area_from_id)
                / "capacities"
                / f"{link.area_to_id}_indirect"
            )
            components.append(
                InputComponent(
                    id=link.id,
                    model="link",
                    parameters=[
                        InputComponentParameter(
                            id="capacity_direct",
                            time_dependent=True,
                            scenario_dependent=True,
                            value=str(capacity_direct_path),
                        ),
                        InputComponentParameter(
                            id="capacity_indirect",
                            time_dependent=True,
                            scenario_dependent=True,
                            value=str(capacity_indirect_path),
                        ),
                    ],
                )
            )
            connections.append(
                InputPortConnections(
                    component1=link.id,
                    port1="in_port",
                    component2=link.area_from_id,
                    port2="balance_port",
                )
            )
            connections.append(
                InputPortConnections(
                    component1=link.id,
                    port1="out_port",
                    component2=link.area_to_id,
                    port2="balance_port",
                ),
            )
        return components, connections

    def _convert_wind_to_component_list(
        self, areas: list[Area]
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        components = []
        connections = []
        self.logger.info("Converting wind to component list...")
        for area in areas:
            series_path = (
                self.study_path / "input" / "wind" / "series" / f"wind_{area.id}.txt"
            )
            if series_path.exists():
                if self._check_dataframe_validity(area.get_wind_matrix()):
                    components.append(
                        InputComponent(
                            id=area.id,
                            model="wind",
                            parameters=[
                                InputComponentParameter(
                                    id="wind",
                                    time_dependent=True,
                                    scenario_dependent=True,
                                    value=str(series_path).removesuffix(".txt"),
                                )
                            ],
                        )
                    )
                    connections.append(
                        InputPortConnections(
                            component1="wind",
                            port1="balance_port",
                            component2=area.id,
                            port2="balance_port",
                        )
                    )

        return components, connections

    def _convert_solar_to_component_list(
        self, areas: list[Area]
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        components = []
        connections = []
        self.logger.info("Converting solar to component list...")
        for area in areas:
            series_path = (
                self.study_path / "input" / "solar" / "series" / f"solar_{area.id}.txt"
            )

            if series_path.exists():
                if self._check_dataframe_validity(area.get_solar_matrix()):
                    components.append(
                        InputComponent(
                            id=area.id,
                            model="solar",
                            parameters=[
                                InputComponentParameter(
                                    id="solar",
                                    time_dependent=True,
                                    scenario_dependent=True,
                                    value=str(series_path).removesuffix(".txt"),
                                )
                            ],
                        )
                    )
                    connections.append(
                        InputPortConnections(
                            component1="solar",
                            port1="balance_port",
                            component2=area.id,
                            port2="balance_port",
                        )
                    )

        return components, connections

    def _convert_load_to_component_list(
        self, areas: list[Area]
    ) -> tuple[list[InputComponent], list[InputPortConnections]]:
        components = []
        connections = []
        self.logger.info("Converting load to component list...")
        for area in areas:
            series_path = (
                self.study_path / "input" / "load" / "series" / f"load_{area.id}.txt"
            )
            if series_path.exists():
                if self._check_dataframe_validity(area.get_load_matrix()):
                    components.append(
                        InputComponent(
                            id="load",
                            model="load",
                            parameters=[
                                InputComponentParameter(
                                    id="load",
                                    time_dependent=True,
                                    scenario_dependent=True,
                                    value=str(series_path).removesuffix(".txt"),
                                )
                            ],
                        )
                    )
                    connections.append(
                        InputPortConnections(
                            component1="load",
                            port1="balance_port",
                            component2=area.id,
                            port2="balance_port",
                        )
                    )

        return components, connections

    def convert_study_to_input_study(self) -> InputStudy:
        areas = self.study.read_areas()
        area_components = self._convert_area_to_component_list(areas)

        list_components: list[InputComponent] = []
        list_connections: list[InputPortConnections] = []

        components, connections = self._convert_link_to_component_list()
        list_components.extend(components)
        list_connections.extend(connections)
        conversion_methods = [
            self._convert_renewable_to_component_list,
            self._convert_thermal_to_component_list,
            self._convert_load_to_component_list,
            self._convert_wind_to_component_list,
            self._convert_solar_to_component_list,
        ]

        for method in conversion_methods:
            components, connections = method(areas)
            list_components.extend(components)
            list_connections.extend(connections)

        self.logger.info(
            "Converting node, components and connections into Input study..."
        )
        return InputStudy(
            nodes=area_components,
            components=list_components,
            connections=list_connections,
        )

    def process_all(self) -> None:
        study = self.convert_study_to_input_study()
        self.logger.info("Converting input study into yaml file...")
        transform_to_yaml(model=study, output_path=self.output_path)
