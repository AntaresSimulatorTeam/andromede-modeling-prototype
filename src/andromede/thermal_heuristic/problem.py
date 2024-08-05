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

from math import ceil
from pathlib import Path
from typing import List, Optional

import numpy as np

from andromede.model import Model, PortType
from andromede.model.library import Library, library
from andromede.simulation import OutputValues
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    create_component,
)
from andromede.study.data import ComponentParameterIndex
from andromede.study.parsing import InputComponents, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    resolve_components_and_cnx,
)
from andromede.thermal_heuristic.time_scenario_parameter import (
    TimeScenarioHourParameter,
    timesteps,
    WeekScenarioIndex,
)
from andromede.thermal_heuristic.workflow import ResolutionStep, SolvingParameters

from andromede.thermal_heuristic.cluster_parameter import (
    complete_database_for_fast_heuristic,
    complete_database_with_cluster_parameters,
)


class ThermalProblemBuilder:
    def __init__(
        self,
        fast: bool,
        data_dir: Path,
        id_thermal_cluster_model: str,
        port_types: List[PortType],
        models: List[Model],
        time_scenario_hour_parameter: TimeScenarioHourParameter,
    ) -> None:
        lib = library(
            port_types=port_types,
            models=models,
        )
        self.time_scenario_hour_parameter = time_scenario_hour_parameter
        self.id_thermal_cluster_model = id_thermal_cluster_model

        input_components = get_input_components(data_dir / "components.yml")
        self.network = get_network(input_components, lib)
        self.database = self.get_database(input_components, data_dir, fast)

    def main_resolution_step(
        self,
        index: WeekScenarioIndex,
        solving_parameters: SolvingParameters = SolvingParameters(),
    ) -> ResolutionStep:
        main_resolution_step = ResolutionStep(
            timesteps=timesteps(index, self.time_scenario_hour_parameter),
            scenarios=[index.scenario],
            database=self.database,
            network=self.network,
        )

        main_resolution_step.solve(solving_parameters)

        return main_resolution_step

    def update_database_accurate(
        self,
        output: OutputValues,
        index: WeekScenarioIndex,
        list_cluster_id: Optional[list[str]],
    ) -> None:
        if list_cluster_id is None:
            list_cluster_id = self.heuristic_components()
        for cluster in list_cluster_id:
            self.database.convert_to_time_scenario_series_data(
                ComponentParameterIndex(cluster, "nb_units_min"),
                self.time_scenario_hour_parameter.hour
                * self.time_scenario_hour_parameter.week,
                self.time_scenario_hour_parameter.scenario,
            )
            nb_on = output.component(cluster).var("nb_on").value[0]  # type:ignore

            for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter)):
                self.database.edit_value(
                    ComponentParameterIndex(cluster, "nb_units_min"),
                    ceil(round(nb_on[i], 12)),  # type:ignore
                    t,
                    index.scenario,
                )

    def update_database_fast_before_heuristic(
        self, output: OutputValues, index: WeekScenarioIndex
    ) -> None:
        for cluster in self.heuristic_components():
            pmax = self.database.get_value(
                ComponentParameterIndex(cluster, "p_max"), 0, 0
            )
            nb_on_1 = output.component(cluster).var("generation").value[0]  # type: ignore

            self.database.add_data(cluster, "n_guide", ConstantData(0))
            self.database.convert_to_time_scenario_series_data(
                ComponentParameterIndex(cluster, "n_guide"),
                self.time_scenario_hour_parameter.hour
                * self.time_scenario_hour_parameter.week,
                self.time_scenario_hour_parameter.scenario,
            )

            for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter)):
                self.database.edit_value(
                    ComponentParameterIndex(cluster, "n_guide"),
                    ceil(round(nb_on_1[i] / pmax, 12)),  # type: ignore
                    t,
                    index.scenario,
                )

    def update_database_fast_after_heuristic(
        self,
        output: OutputValues,
        index: WeekScenarioIndex,
        list_cluster_id: Optional[list[str]],
    ) -> None:
        if list_cluster_id is None:
            list_cluster_id = self.heuristic_components()
        for cluster in list_cluster_id:
            pmin = self.database.get_value(
                ComponentParameterIndex(cluster, "p_min"), 0, 0
            )
            pdispo = [
                self.database.get_value(
                    ComponentParameterIndex(cluster, "max_generating"),
                    t,
                    index.scenario,
                )
                for t in timesteps(index, self.time_scenario_hour_parameter)
            ]

            self.database.convert_to_time_scenario_series_data(
                ComponentParameterIndex(cluster, "min_generating"),
                self.time_scenario_hour_parameter.hour
                * self.time_scenario_hour_parameter.week,
                self.time_scenario_hour_parameter.scenario,
            )

            min_gen = np.minimum(
                np.array(
                    output.component(cluster).var("n").value[0]  # type:ignore
                ).reshape((self.time_scenario_hour_parameter.hour, 1))
                * pmin,
                np.array(pdispo).reshape((self.time_scenario_hour_parameter.hour, 1)),
            ).reshape(self.time_scenario_hour_parameter.hour)

            for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter)):
                self.database.edit_value(
                    ComponentParameterIndex(cluster, "min_generating"),
                    min_gen[i],
                    t,
                    index.scenario,
                )

    def heuristic_resolution_step(
        self,
        index: WeekScenarioIndex,
        id_component: str,
        model: Model,
        solving_parameters: SolvingParameters = SolvingParameters(),
    ) -> ResolutionStep:
        cluster = create_component(model=model, id=id_component)

        network = Network("test")
        network.add_component(cluster)

        resolution_step = ResolutionStep(
            timesteps=timesteps(index, self.time_scenario_hour_parameter),
            scenarios=[index.scenario],
            database=self.database,
            network=network,
        )

        resolution_step.solve(solving_parameters)
        return resolution_step

    def get_database(
        self,
        components_file: InputComponents,
        data_dir: Path,
        fast: bool,
    ) -> DataBase:

        database = build_data_base(components_file, data_dir)

        complete_database_with_cluster_parameters(
            database, self.heuristic_components(), self.time_scenario_hour_parameter
        )

        if fast:
            complete_database_for_fast_heuristic(
                database, self.heuristic_components(), self.time_scenario_hour_parameter
            )

        return database

    def heuristic_components(self) -> list[str]:
        return [
            c.id
            for c in self.network.components
            if c.model.id == self.id_thermal_cluster_model
        ]


def get_network(components_file: InputComponents, lib: Library) -> Network:
    components_input = resolve_components_and_cnx(components_file, lib)
    network = build_network(components_input)
    return network


def get_input_components(compo_file: Path) -> InputComponents:
    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    return components_file
