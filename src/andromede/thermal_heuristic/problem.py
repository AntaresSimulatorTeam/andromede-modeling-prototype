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
import ortools.linear_solver.pywraplp as pywraplp

import numpy as np
import pandas as pd

from andromede.model import Model, PortType
from andromede.model.library import Library, library
from andromede.simulation import OutputValues
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
    create_component,
)
from andromede.study.data import ComponentParameterIndex
from andromede.study.parsing import InputComponents, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    resolve_components_and_cnx,
)
from andromede.thermal_heuristic.data import (
    get_max_failures,
    get_max_unit,
    get_max_unit_for_min_down_time,
)
from andromede.thermal_heuristic.time_scenario_parameter import (
    TimeScenarioHourParameter,
    timesteps,
    WeekScenarioIndex,
)
from andromede.thermal_heuristic.workflow import ResolutionStep


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
        self.network = get_network(data_dir / "components.yml", lib)
        self.id_thermal_cluster_model = id_thermal_cluster_model
        self.database = self.get_database(data_dir, "components.yml", fast)

    def get_main_resolution_step(
        self,
        index: WeekScenarioIndex,
        solver_parameters: pywraplp.MPSolverParameters = pywraplp.MPSolverParameters(),
        expected_status: str = pywraplp.Solver.OPTIMAL,
    ) -> ResolutionStep:
        main_resolution_step = ResolutionStep(
            timesteps=timesteps(index, self.time_scenario_hour_parameter),
            scenarios=[index.scenario],
            database=self.database,
            network=self.network,
        )

        main_resolution_step.solve(solver_parameters, expected_status)

        return main_resolution_step

    def update_database_accurate(
        self,
        output: OutputValues,
        index: WeekScenarioIndex,
        list_cluster_id: Optional[list[str]],
    ) -> None:
        if list_cluster_id is None:
            list_cluster_id = self.get_milp_heuristic_components()
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
        for cluster in self.get_milp_heuristic_components():
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
            list_cluster_id = self.get_milp_heuristic_components()
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

    def get_resolution_step_heuristic(
        self,
        index: WeekScenarioIndex,
        id: str,
        model: Model,
        solver_parameters: pywraplp.MPSolverParameters = pywraplp.MPSolverParameters(),
        expected_status: str = pywraplp.Solver.OPTIMAL,
    ) -> ResolutionStep:
        cluster = create_component(model=model, id=id)

        network = Network("test")
        network.add_component(cluster)

        resolution_step = ResolutionStep(
            timesteps=timesteps(index, self.time_scenario_hour_parameter),
            scenarios=[index.scenario],
            database=self.database,
            network=network,
        )

        resolution_step.solve(solver_parameters, expected_status)
        return resolution_step

    def compute_delta(
        self, thermal_cluster: str, database: Optional[DataBase] = None
    ) -> int:
        if database is None:
            database = self.database
        delta = int(
            max(
                database.get_value(
                    ComponentParameterIndex(thermal_cluster, "d_min_up"), 0, 0
                ),
                database.get_value(
                    ComponentParameterIndex(thermal_cluster, "d_min_down"), 0, 0
                ),
            )
        )
        return delta

    def complete_database_for_fast_heuristic(
        self, database: DataBase, list_cluster_id: list[str]
    ) -> None:
        for cluster_id in list_cluster_id:
            delta = self.compute_delta(cluster_id, database)
            n_max = database.get_data(cluster_id, "nb_units_max").get_max_value()
            database.add_data(cluster_id, "n_max", ConstantData(int(n_max)))
            database.add_data(cluster_id, "delta", ConstantData(delta))

            for h in range(delta):
                start_ajust = self.time_scenario_hour_parameter.hour - delta + h
                database.add_data(
                    cluster_id,
                    f"alpha_ajust_{h}",
                    TimeSeriesData(
                        {
                            TimeIndex(t): (
                                1
                                if (
                                    t % self.time_scenario_hour_parameter.hour
                                    >= start_ajust
                                )
                                or (t % self.time_scenario_hour_parameter.hour < h)
                                else 0
                            )
                            for t in range(
                                self.time_scenario_hour_parameter.hour
                                * self.time_scenario_hour_parameter.week
                            )
                        }
                    ),
                )
                for k in range(self.time_scenario_hour_parameter.hour // delta):
                    start_k = k * delta + h
                    end_k = min(start_ajust, (k + 1) * delta + h)
                    database.add_data(
                        cluster_id,
                        f"alpha_{k}_{h}",
                        TimeSeriesData(
                            {
                                TimeIndex(t): (
                                    1
                                    if (
                                        t % self.time_scenario_hour_parameter.hour
                                        >= start_k
                                    )
                                    and (
                                        t % self.time_scenario_hour_parameter.hour
                                        < end_k
                                    )
                                    else 0
                                )
                                for t in range(
                                    self.time_scenario_hour_parameter.hour
                                    * self.time_scenario_hour_parameter.week
                                )
                            }
                        ),
                    )

    def get_database(
        self,
        data_dir: Path,
        yml_file: str,
        fast: bool,
    ) -> DataBase:
        components_file = get_input_components(data_dir / yml_file)
        database = build_data_base(components_file, data_dir)

        self.complete_database_with_cluster_parameters(database)

        if fast:
            self.complete_database_for_fast_heuristic(
                database,
                self.get_milp_heuristic_components(),
            )

        return database

    def get_milp_heuristic_components(self) -> list[str]:
        return [
            c.id
            for c in self.network.components
            if c.model.id == self.id_thermal_cluster_model
        ]

    def complete_database_with_cluster_parameters(self, database: DataBase) -> None:
        for cluster_id in self.get_milp_heuristic_components():
            if type(database.get_data(cluster_id, "max_generating")) is ConstantData:
                database.add_data(
                    cluster_id,
                    "max_failure",
                    ConstantData(0),
                )
                database.add_data(
                    cluster_id,
                    "nb_units_max_min_down_time",
                    database.get_data(cluster_id, "nb_units_max"),
                )

            else:
                (
                    max_units,
                    max_failures,
                    nb_units_max_min_down_time,
                ) = compute_cluster_parameters(
                    database,
                    cluster_id,
                    self.time_scenario_hour_parameter,
                )
                database.add_data(
                    cluster_id,
                    "nb_units_max",
                    TimeScenarioSeriesData(max_units),
                )
                database.add_data(
                    cluster_id,
                    "max_failure",
                    TimeScenarioSeriesData(max_failures),
                )
                database.add_data(
                    cluster_id,
                    "nb_units_max_min_down_time",
                    TimeScenarioSeriesData(nb_units_max_min_down_time),
                )


def compute_cluster_parameters(
    database: DataBase,
    cluster_id: str,
    time_scenario_hour_parameter: TimeScenarioHourParameter,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    database.convert_to_time_scenario_series_data(
        ComponentParameterIndex(cluster_id, "max_generating"),
        timesteps=time_scenario_hour_parameter.hour * time_scenario_hour_parameter.week,
        scenarios=time_scenario_hour_parameter.scenario,
    )
    max_units = get_max_unit(
        database.get_value(ComponentParameterIndex(cluster_id, "p_max"), 0, 0),
        database.get_value(ComponentParameterIndex(cluster_id, "nb_units_max"), 0, 0),
        database.get_data(
            cluster_id, "max_generating"
        ).time_scenario_series,  # type:ignore
    )
    max_failures = get_max_failures(max_units, time_scenario_hour_parameter.hour)
    nb_units_max_min_down_time = get_max_unit_for_min_down_time(
        int(
            max(
                database.get_value(
                    ComponentParameterIndex(cluster_id, "d_min_up"), 0, 0
                ),
                database.get_value(
                    ComponentParameterIndex(cluster_id, "d_min_down"), 0, 0
                ),
            )
        ),
        max_units,
        time_scenario_hour_parameter.hour,
    )

    return max_units, max_failures, nb_units_max_min_down_time


def get_network(compo_file: Path, lib: Library) -> Network:
    components_file = get_input_components(compo_file)
    components_input = resolve_components_and_cnx(components_file, lib)
    network = build_network(components_input)
    return network


def get_input_components(compo_file: Path) -> InputComponents:
    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    return components_file
