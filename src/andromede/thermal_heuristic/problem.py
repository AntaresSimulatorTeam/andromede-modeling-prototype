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
from typing import Callable, List, Optional

from andromede.model import Model, PortType
from andromede.model.library import library
from andromede.simulation import (
    BlockBorderManagement,
    OptimizationProblem,
    OutputValues,
    TimeBlock,
    build_problem,
)
from andromede.study import ConstantData, DataBase, Network, create_component
from andromede.study.data import ComponentParameterIndex
from andromede.study.parsing import InputComponents, parse_yaml_components
from andromede.study.resolve_components import (
    build_data_base,
    build_network,
    resolve_components_and_cnx,
)
from andromede.thermal_heuristic.cluster_parameter import (
    complete_database_for_fast_heuristic,
    complete_database_with_cluster_parameters,
)
from andromede.thermal_heuristic.time_scenario_parameter import (
    BlockScenarioIndex,
    TimeScenarioHourParameter,
    timesteps,
)


class ThermalProblemBuilder:
    def __init__(
        self,
        time_scenario_hour_parameter: TimeScenarioHourParameter,
        network: Network,
        database: DataBase,
    ) -> None:
        self.time_scenario_hour_parameter = time_scenario_hour_parameter
        self.database = database
        self.network = network

    def main_resolution_step(
        self,
        index: BlockScenarioIndex,
    ) -> OptimizationProblem:
        problem = build_problem(
            self.network,
            self.database,
            TimeBlock(1, timesteps(index, self.time_scenario_hour_parameter)),
            [index.scenario],
            border_management=BlockBorderManagement.CYCLE,
        )

        return problem

    def update_database_heuristic(
        self,
        output: OutputValues,
        index: BlockScenarioIndex,
        list_cluster_id: List[str],
        param_to_update: List[List[str]],
        var_to_read: List[str],
        fn_to_apply: Callable,
        version: Optional[str] = None,
        option: Optional[str] = None,
        param_needed_to_compute: Optional[List[str]] = None,
        param_node_needed_to_compute : Optional[List[str]] = None,
    ) -> None:
        for cluster in list_cluster_id:
            for list_param_update in param_to_update:
                for param_update in list_param_update:
                    if (
                        ComponentParameterIndex(cluster, param_update)
                        not in self.database.__dict__.keys()
                    ):
                        self.database.add_data(cluster, param_update, ConstantData(0))
                    self.database.convert_to_time_scenario_series_data(
                        ComponentParameterIndex(cluster, param_update),
                        self.time_scenario_hour_parameter.hour
                        * self.time_scenario_hour_parameter.week,
                        self.time_scenario_hour_parameter.scenario,
                    )
            sol = {}
            for variable in var_to_read:
                sol[variable] = output.component(cluster).var(variable).value[0] # type:ignore

            param = {}
            if param_needed_to_compute is not None:
                for p in param_needed_to_compute:
                    param[p] = [
                        self.database.get_value(
                            ComponentParameterIndex(cluster, p),
                            t,
                            index.scenario,
                        )
                        for t in timesteps(index, self.time_scenario_hour_parameter)
                    ]
            if param_node_needed_to_compute is not None:
                list_connections = self.network._connections
                print(list_connections)
                node = None
                for connection in list_connections:
                    if connection.port1.component.id == cluster:
                        node = connection.port2.component.id
                    if connection.port2.component.id == cluster:
                        node = connection.port1.component.id
                for p in param_node_needed_to_compute:
                    param[p] = [self.database.get_data(node,p).value
                                for t in timesteps(index, self.time_scenario_hour_parameter)]   

            if version is not None:
                if option is not None:
                    result_heuristic = fn_to_apply(version, option, [i for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter))],
                                           [s for s in sol.values()], [p for p in param.values()])
                else:
                    result_heuristic = fn_to_apply(version, [i for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter))],
                                           [s for s in sol.values()], [p for p in param.values()])
            elif option is not None:
                result_heuristic = fn_to_apply(option, [i for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter))],
                                           [s for s in sol.values()], [p for p in param.values()]) 
            else:
                result_heuristic = fn_to_apply( [i for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter))],
                                           [s for s in sol.values()], [p for p in param.values()])            

            for i, t in enumerate(timesteps(index, self.time_scenario_hour_parameter)):
                results_heuristic = result_heuristic[i]
                for p,list_param_update in enumerate(param_to_update):
                    for param_update in list_param_update:
                        self.database.set_value(
                            ComponentParameterIndex(cluster, param_update),
                            results_heuristic[p],  # type:ignore
                            t,
                            index.scenario,
                        )



    def heuristic_resolution_step(
        self,
        index: BlockScenarioIndex,
        id_component: str,
        model: Model,
    ) -> OptimizationProblem:
        cluster = create_component(model=model, id=id_component)

        network = Network("test")
        network.add_component(cluster)

        problem = build_problem(
            network,
            self.database,
            TimeBlock(1, timesteps(index, self.time_scenario_hour_parameter)),
            [index.scenario],
            border_management=BlockBorderManagement.CYCLE,
        )

        return problem


def get_database(
    components_file: InputComponents,
    data_dir: Path,
    fast: bool,
    cluster: List[str],
    time_scenario_hour_parameter: TimeScenarioHourParameter,
) -> DataBase:
    database = build_data_base(components_file, data_dir)

    complete_database_with_cluster_parameters(
        database, cluster, time_scenario_hour_parameter
    )

    if fast:
        complete_database_for_fast_heuristic(
            database, cluster, time_scenario_hour_parameter
        )

    return database


def get_heuristic_components(
    components_file: InputComponents, id_heuristic_model: str
) -> List[str]:
    return [c.id for c in components_file.components if c.model == id_heuristic_model]


def get_network(
    components_file: InputComponents, port_types: List[PortType], models: List[Model]
) -> Network:
    lib = library(
        port_types=port_types,
        models=models,
    )
    components_input = resolve_components_and_cnx(components_file, lib)
    network = build_network(components_input)
    return network


def get_input_components(compo_file: Path) -> InputComponents:
    with compo_file.open() as c:
        components_file = parse_yaml_components(c)
    return components_file
