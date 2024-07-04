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
from typing import Dict, Iterable, List, Optional

import numpy as np
import ortools.linear_solver.pywraplp as pywraplp
import pandas as pd

from andromede.model import Model, PortType
from andromede.model.library import Library, library
from andromede.simulation import (
    BlockBorderManagement,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.simulation.optimization import OptimizationProblem
from andromede.study import (
    ConstantData,
    DataBase,
    Network,
    TimeIndex,
    TimeScenarioSeriesData,
    TimeSeriesData,
    create_component,
)
from andromede.study.data import AbstractDataStructure, ComponentParameterIndex
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


def library_thermal_problem(
    port_types: Iterable[PortType],
    models: List[Model],
    lp_relaxation: bool,
    fast: bool,
    initial_thermal_model: Model,
) -> Library:
    thermal_model = edit_thermal_model(lp_relaxation, fast, initial_thermal_model)
    lib = library(
        port_types=port_types,
        models=models + [thermal_model],
    )
    return lib


class ThermalProblemBuilder:
    def __init__(
        self,
        number_hours: int,
        lp_relaxation: bool,
        fast: bool,
        data_dir: Path,
        initial_thermal_model: Model,
        port_types: List[PortType],
        models: List[Model],
        number_week: int,
        list_scenario: List[int],
    ) -> None:
        lib = library_thermal_problem(
            port_types, models, lp_relaxation, fast, initial_thermal_model
        )
        self.number_week = number_week
        self.list_scenario = list_scenario
        self.network = get_network(data_dir / "components.yml", lib)
        self.number_hours = number_hours
        self.database = self.get_database(
            data_dir,
            "components.yml",
            get_cluster_id(self.network, initial_thermal_model.id),
            number_hours,
            fast,
        )
        self.initial_thermal_model = initial_thermal_model

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
            list_cluster_id = get_cluster_id(
                self.network, self.initial_thermal_model.id
            )
        for cluster in list_cluster_id:
            nb_on = np.zeros(
                (self.number_hours * self.number_week, len(self.list_scenario))
            )
            nb_on[
                range(week * self.number_hours, (week + 1) * self.number_hours),
                scenario,
            ] = np.ceil(
                np.round(
                    output.component(cluster).var("nb_on").value[0],  # type:ignore
                    12,
                )
            )
            for s in self.list_scenario:
                if s != scenario:
                    for t in range(self.number_week * self.number_hours):
                        if t not in list(
                            range(
                                week * self.number_hours, (week + 1) * self.number_hours
                            )
                        ):
                            nb_on[t, s] = self.database.get_value(
                                ComponentParameterIndex(cluster, "nb_units_min"), t, s
                            )
            nb_on_min = TimeScenarioSeriesData(
                pd.DataFrame(
                    nb_on,
                    index=[list(range(self.number_week * self.number_hours))],
                    columns=self.list_scenario,
                )
            )

            self.database.add_data(cluster, "nb_units_min", nb_on_min)

    def update_database_fast_before_heuristic(
        self, output: OutputValues, week: int
    ) -> None:
        for cluster in get_cluster_id(self.network, self.initial_thermal_model.id):
            pmax = self.database.get_value(
                ComponentParameterIndex(cluster, "p_max"), 0, 0
            )
            nb_on_1 = np.ceil(
                np.round(
                    np.array(output.component(cluster).var("generation").value[0])  # type: ignore
                    / pmax,
                    12,
                )
            )

            self.database.add_data(
                cluster,
                "n_guide",
                TimeSeriesData(
                    {
                        TimeIndex(i + week * self.number_hours): nb_on_1[i]
                        for i in range(self.number_hours)
                    }
                ),
            )

    def update_database_fast_after_heuristic(
        self,
        output: OutputValues,
        week: int,
        scenario: int,
        list_cluster_id: Optional[list[str]],
    ) -> None:
        if list_cluster_id is None:
            list_cluster_id = get_cluster_id(
                self.network, self.initial_thermal_model.id
            )
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

            min_gen = np.zeros(
                (self.number_hours * self.number_week, len(self.list_scenario))
            )
            min_gen[
                range(week * self.number_hours, (week + 1) * self.number_hours),
                scenario,
            ] = np.minimum(
                np.array(
                    output.component(cluster).var("n").value[0]  # type:ignore
                ).reshape((self.number_hours, 1))
                * pmin,
                np.array(pdispo).reshape((self.number_hours, 1)),
            ).reshape(
                self.number_hours
            )

            for s in self.list_scenario:
                if s != scenario:
                    for t in range(self.number_week * self.number_hours):
                        if t not in list(
                            range(
                                week * self.number_hours, (week + 1) * self.number_hours
                            )
                        ):
                            min_gen[t, s] = self.database.get_value(
                                ComponentParameterIndex(cluster, "min_generating"), t, s
                            )
            min_gen_df = TimeScenarioSeriesData(
                pd.DataFrame(
                    min_gen,
                    index=[list(range(self.number_week * self.number_hours))],
                    columns=self.list_scenario,
                )
            )
            self.database.add_data(cluster, "min_generating", min_gen_df)

    def get_resolution_step_accurate_heuristic(
        self,
        week: int,
        scenario: int,
        cluster_id: str,
    ) -> ResolutionStep:
        thermal_model_builder = HeuristicAccurateModelBuilder(
            self.initial_thermal_model
        )

        cluster = create_component(model=thermal_model_builder.model, id=cluster_id)

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

    def get_resolution_step_fast_heuristic(
        self,
        thermal_cluster: str,
        week: int,
        scenario: int,
    ) -> ResolutionStep:
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

        network = self.get_network_fast_heuristic(
            delta, self.number_hours // delta, thermal_cluster
        )

        resolution_step = ResolutionStep(
            network=network,
            database=self.database,
            timesteps=list(
                range(week * self.number_hours, (week + 1) * self.number_hours)
            ),
            scenarios=[scenario],
        )

        return resolution_step

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

    def get_network_fast_heuristic(
        self, delta: int, number_blocks: int, cluster_id: str
    ) -> Network:
        block = create_component(
            model=HeuristicFastModelBuilder(number_blocks, delta=delta).model,
            id=cluster_id,
        )

        network = Network("test")
        network.add_component(block)
        return network

    def get_database(
        self,
        data_dir: Path,
        yml_file: str,
        cluster_id: List[str],
        hours_in_week: int,
        fast: bool,
    ) -> DataBase:
        components_file = get_input_components(data_dir / yml_file)
        database = build_data_base(components_file, data_dir)

        complete_database_with_cluster_parameters(
            database,
            list_cluster_id=cluster_id,
            dir_path=data_dir,
            hours_in_week=hours_in_week,
        )

        if fast:
            self.complete_database_for_fast_heuristic(
                database, cluster_id, hours_in_week
            )

        return database


def complete_database_with_cluster_parameters(
    database: DataBase, list_cluster_id: List[str], dir_path: Path, hours_in_week: int
) -> None:
    for cluster_id in list_cluster_id:
        data = get_data(
            dir_path,
            "components.yml",
            cluster_id,
        )

        if type(data["max_generating"]) is float:
            database.add_data(
                cluster_id,
                "max_failure",
                ConstantData(0),
            )
            database.add_data(
                cluster_id,
                "nb_units_max_min_down_time",
                ConstantData(data["nb_units_max"]),
            )

        else:
            (
                max_units,
                max_failures,
                nb_units_max_min_down_time,
            ) = compute_cluster_parameters(hours_in_week, data)
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
    hours_in_week: int, data: Dict
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    max_generating_shape = data["max_generating"].shape
    if len(max_generating_shape) == 1:
        max_generating = pd.DataFrame(
            data["max_generating"].reshape((max_generating_shape[0], 1))
        )
    else:
        max_generating = pd.DataFrame(data["max_generating"])
    max_units = get_max_unit(data["p_max"], data["nb_units_max"], max_generating)
    max_failures = get_max_failures(max_units, hours_in_week)
    nb_units_max_min_down_time = get_max_unit_for_min_down_time(
        int(max(data["d_min_up"], data["d_min_down"])), max_units, hours_in_week
    )

    return max_units, max_failures, nb_units_max_min_down_time


def get_cluster_id(network: Network, cluster_model_id: str) -> list[str]:
    return [c.id for c in network.components if c.model.id == cluster_model_id]


def get_network(compo_file: Path, lib: Library) -> Network:
    components_file = get_input_components(compo_file)
    components_input = resolve_components_and_cnx(components_file, lib)
    network = build_network(components_input)
    return network


def get_input_components(compo_file: Path) -> InputComponents:
    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    return components_file


def edit_thermal_model(
    lp_relaxation: bool, fast: bool, initial_thermal_model: Model
) -> Model:
    if fast:
        thermal_model = FastModelBuilder(initial_thermal_model).model
    elif lp_relaxation:
        thermal_model = AccurateModelBuilder(initial_thermal_model).model
    else:
        thermal_model = initial_thermal_model
    return thermal_model


def get_data(
    data_dir: Path,
    yml_file: str,
    id_cluster: str,
) -> Dict:
    compo_file = data_dir / yml_file

    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    cluster = [c for c in components_file.components if c.id == id_cluster][0]
    parameters = {
        p.name: (
            p.value
            if p.value is not None
            else np.loadtxt(data_dir / (p.timeseries + ".txt"))  # type:ignore
        )
        for p in cluster.parameters  # type:ignore
    }
    return parameters  # type:ignore
