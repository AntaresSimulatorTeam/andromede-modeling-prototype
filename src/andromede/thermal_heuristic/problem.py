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
from typing import Dict, Iterable, List, Optional

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
from andromede.thermal_heuristic.model import (
    AccurateModelBuilder,
    FastModelBuilder,
    HeuristicAccurateModelBuilder,
    HeuristicFastModelBuilder,
)
from andromede.thermal_heuristic.workflow import ResolutionStep


class ThermalProblemBuilder:
    def __init__(
        self,
        number_hours: int,
        fast: bool,
        data_dir: Path,
        initial_thermal_model: Model,
        port_types: List[PortType],
        models: List[Model],
        number_week: int,
        number_scenario: int,
    ) -> None:
        lib = library(
            port_types=port_types,
            models=models,
        )
        self.number_week = number_week
        self.number_scenario = number_scenario
        self.network = get_network(data_dir / "components.yml", lib)
        self.number_hours = number_hours
        self.initial_thermal_model = initial_thermal_model
        self.database = self.get_database(
            data_dir,
            "components.yml",
            number_hours,
            fast,
            timesteps=number_hours * number_week,
            scenarios=number_scenario,
        )

    def get_main_resolution_step(self, week: int, scenario: int) -> ResolutionStep:
        main_resolution_step = ResolutionStep(
            timesteps=list(
                range(week * self.number_hours, (week + 1) * self.number_hours)
            ),
            scenarios=[scenario],
            database=self.database,
            network=self.network,
        )

        return main_resolution_step

    def update_database_accurate(
        self,
        output: OutputValues,
        week: int,
        scenario: int,
        list_cluster_id: Optional[list[str]],
    ) -> None:
        if list_cluster_id is None:
            list_cluster_id = self.get_milp_heuristic_components()
        for cluster in list_cluster_id:
            self.database.convert_to_time_scenario_series_data(
                ComponentParameterIndex(cluster, "nb_units_min"),
                self.number_hours * self.number_week,
                self.number_scenario,
            )
            nb_on = output.component(cluster).var("nb_on").value[0]  # type:ignore

            for i, t in enumerate(
                list(range(week * self.number_hours, (week + 1) * self.number_hours))
            ):
                self.database.edit_value(
                    ComponentParameterIndex(cluster, "nb_units_min"),
                    ceil(round(nb_on[i], 12)),  # type:ignore
                    t,
                    scenario,
                )

    def update_database_fast_before_heuristic(
        self, output: OutputValues, week: int, scenario: int
    ) -> None:
        for cluster in self.get_milp_heuristic_components():
            pmax = self.database.get_value(
                ComponentParameterIndex(cluster, "p_max"), 0, 0
            )
            nb_on_1 = output.component(cluster).var("generation").value[0]  # type: ignore

            self.database.add_data(cluster, "n_guide", ConstantData(0))
            self.database.convert_to_time_scenario_series_data(
                ComponentParameterIndex(cluster, "n_guide"),
                self.number_hours * self.number_week,
                self.number_scenario,
            )

            for i, t in enumerate(
                list(
                    range(
                        week * self.number_hours,
                        (week + 1) * self.number_hours,
                    )
                )
            ):
                self.database.edit_value(
                    ComponentParameterIndex(cluster, "n_guide"),
                    ceil(round(nb_on_1[i] / pmax, 12)),  # type: ignore
                    t,
                    scenario,
                )

    def update_database_fast_after_heuristic(
        self,
        output: OutputValues,
        week: int,
        scenario: int,
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
                    ComponentParameterIndex(cluster, "max_generating"), t, scenario
                )
                for t in range(week * self.number_hours, (week + 1) * self.number_hours)
            ]

            self.database.convert_to_time_scenario_series_data(
                ComponentParameterIndex(cluster, "min_generating"),
                self.number_hours * self.number_week,
                self.number_scenario,
            )

            min_gen = np.minimum(
                np.array(
                    output.component(cluster).var("n").value[0]  # type:ignore
                ).reshape((self.number_hours, 1))
                * pmin,
                np.array(pdispo).reshape((self.number_hours, 1)),
            ).reshape(self.number_hours)

            for i, t in enumerate(
                list(range(week * self.number_hours, (week + 1) * self.number_hours))
            ):
                self.database.edit_value(
                    ComponentParameterIndex(cluster, "min_generating"),
                    min_gen[i],
                    t,
                    scenario,
                )

    def get_resolution_step_heuristic(
        self, week: int, scenario: int, cluster_id: str, model: Model
    ) -> ResolutionStep:

        cluster = create_component(model=model, id=cluster_id)

        network = Network("test")
        network.add_component(cluster)

        resolution_step = ResolutionStep(
            timesteps=list(
                range(week * self.number_hours, (week + 1) * self.number_hours)
            ),
            scenarios=[scenario],
            database=self.database,
            network=network,
        )

        return resolution_step

    def compute_delta(self, thermal_cluster: str) -> int:
        delta = int(
            max(
                self.database.get_value(
                    ComponentParameterIndex(thermal_cluster, "d_min_up"), 0, 0
                ),
                self.database.get_value(
                    ComponentParameterIndex(thermal_cluster, "d_min_down"), 0, 0
                ),
            )
        )
        return delta

    def complete_database_for_fast_heuristic(
        self, database: DataBase, list_cluster_id: list[str], number_hours: int
    ) -> None:
        for cluster_id in list_cluster_id:
            delta = int(
                max(
                    database.get_value(
                        ComponentParameterIndex(cluster_id, "d_min_up"), 0, 0
                    ),
                    database.get_value(
                        ComponentParameterIndex(cluster_id, "d_min_down"), 0, 0
                    ),
                )
            )
            n_max = database.get_data(cluster_id, "nb_units_max").get_max_value()
            database.add_data(cluster_id, "n_max", ConstantData(int(n_max)))
            database.add_data(cluster_id, "delta", ConstantData(delta))

            for h in range(delta):
                start_ajust = self.number_hours - delta + h
                database.add_data(
                    cluster_id,
                    f"alpha_ajust_{h}",
                    TimeSeriesData(
                        {
                            TimeIndex(t): (
                                1
                                if (t % self.number_hours >= start_ajust)
                                or (t % self.number_hours < h)
                                else 0
                            )
                            for t in range(self.number_hours * self.number_week)
                        }
                    ),
                )
                for k in range(number_hours // delta):
                    start_k = k * delta + h
                    end_k = min(start_ajust, (k + 1) * delta + h)
                    database.add_data(
                        cluster_id,
                        f"alpha_{k}_{h}",
                        TimeSeriesData(
                            {
                                TimeIndex(t): (
                                    1
                                    if (t % self.number_hours >= start_k)
                                    and (t % self.number_hours < end_k)
                                    else 0
                                )
                                for t in range(self.number_hours * self.number_week)
                            }
                        ),
                    )

    def get_database(
        self,
        data_dir: Path,
        yml_file: str,
        hours_in_week: int,
        fast: bool,
        timesteps: int,
        scenarios: int,
    ) -> DataBase:
        components_file = get_input_components(data_dir / yml_file)
        database = build_data_base(components_file, data_dir)

        complete_database_with_cluster_parameters(
            database,
            list_cluster_id=self.get_milp_heuristic_components(),
            hours_in_week=hours_in_week,
            timesteps=timesteps,
            scenarios=scenarios,
        )

        if fast:
            self.complete_database_for_fast_heuristic(
                database, self.get_milp_heuristic_components(), hours_in_week
            )

        return database

    def get_milp_heuristic_components(self) -> list[str]:
        return [
            c.id
            for c in self.network.components
            if c.model.id == self.initial_thermal_model.id
        ]


def complete_database_with_cluster_parameters(
    database: DataBase,
    list_cluster_id: List[str],
    hours_in_week: int,
    timesteps: int,
    scenarios: int,
) -> None:
    for cluster_id in list_cluster_id:
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
                hours_in_week, database, cluster_id, timesteps, scenarios
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
    hours_in_week: int,
    database: DataBase,
    cluster_id: str,
    timesteps: int,
    scenarios: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    database.convert_to_time_scenario_series_data(
        ComponentParameterIndex(cluster_id, "max_generating"),
        timesteps=timesteps,
        scenarios=scenarios,
    )
    max_units = get_max_unit(
        database.get_value(ComponentParameterIndex(cluster_id, "p_max"), 0, 0),
        database.get_value(ComponentParameterIndex(cluster_id, "nb_units_max"), 0, 0),
        database.get_data(
            cluster_id, "max_generating"
        ).time_scenario_series,  # type:ignore
    )
    max_failures = get_max_failures(max_units, hours_in_week)
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
        hours_in_week,
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
