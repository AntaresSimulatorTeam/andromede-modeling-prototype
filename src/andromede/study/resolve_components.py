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
from typing import Dict, List, Optional

import pandas as pd

from andromede.model import Model
from andromede.model.library import Library
from andromede.study import (
    Component,
    ConstantData,
    DataBase,
    Network,
    Node,
    PortRef,
    PortsConnection,
)
from andromede.study.data import (
    AbstractDataStructure,
    TimeScenarioIndex,
    TimeScenarioSeriesData,
)
from andromede.study.network_components import NetworkComponents, network_components
from andromede.study.parsing import (
    InputComponent,
    InputComponents,
    InputPortConnections,
)


def resolve_components_and_cnx(
    input_comp: InputComponents, library: Library
) -> NetworkComponents:
    """
    Resolves:
    - components to be used for study
    - connections between components"""
    components_list = [_resolve_component(library, m) for m in input_comp.components]
    nodes = [_resolve_component(library, n) for n in input_comp.nodes]
    all_components: List[Component] = components_list + nodes
    connections = []
    for cnx in input_comp.connections:
        resolved_cnx = _resolve_connections(cnx, all_components)
        connections.append(resolved_cnx)

    return network_components(components_list, nodes, connections)


def _resolve_component(library: Library, component: InputComponent) -> Component:
    model = library.models[component.model]

    return Component(
        model=model,
        id=component.id,
    )


def _resolve_connections(
    connection: InputPortConnections,
    all_components: List[Component],
) -> PortsConnection:
    cnx_component1 = connection.component1
    cnx_component2 = connection.component2
    port1 = connection.port_1
    port2 = connection.port_2

    component_1 = _get_component_by_id(all_components, cnx_component1)
    component_2 = _get_component_by_id(all_components, cnx_component2)
    assert component_1 is not None and component_2 is not None
    port_ref_1 = PortRef(component_1, port1)
    port_ref_2 = PortRef(component_2, port2)

    return PortsConnection(port_ref_1, port_ref_2)


def _get_component_by_id(
    all_components: List[Component], component_id: str
) -> Optional[Component]:
    components_dict = {component.id: component for component in all_components}
    return components_dict.get(component_id)


def consistency_check(
    input_components: Dict[str, Component], input_models: Dict[str, Model]
) -> bool:
    """
    Checks if all components in the Components instances have a valid model from the library.
    Returns True if all components are consistent, raises ValueError otherwise.
    """
    model_ids_set = input_models.keys()
    for component_id, component in input_components.items():
        if component.model.id not in model_ids_set:
            raise ValueError(
                f"Error: Component {component_id} has invalid model ID: {component.model.id}"
            )
    return True


def build_network(comp_network: NetworkComponents) -> Network:
    network = Network("study")

    for node_id, node in comp_network.nodes.items():
        node = Node(model=node.model, id=node_id)
        network.add_node(node)

    for component_id, component in comp_network.components.items():
        network.add_component(component)

    for connection in comp_network.connections:
        network.connect(connection.port1, connection.port2)
    return network


def build_data_base(input_comp: InputComponents) -> DataBase:
    database = DataBase()
    for comp in input_comp.components:
        for param in comp.parameters or []:
            param_value = _evaluate_param_type(
                param.type, param.value, param.timeseries
            )
            database.add_data(comp.id, param.name, param_value)

    return database


def _evaluate_param_type(
    param_type: str, param_value: Optional[float], timeseries: Optional[str]
) -> AbstractDataStructure:
    if param_type == "constant" and param_value is not None:
        return ConstantData(float(param_value))

    elif param_type == "timeseries":
        return TimeScenarioSeriesData(_evaluate_time_series(timeseries))

    raise ValueError(f"Data should be either constant or timeseries ")


def _evaluate_time_series(file_ts: Optional[str]) -> Dict[TimeScenarioIndex, float]:
    """Read time series .txt file delimited by tab"""
    time_series = {}
    try:
        if file_ts is not None:
            path = Path(file_ts)
            df = pd.read_csv(path, header=None)
            values = df.values
            arr_split = [x[0].split() for x in values]
            num_rows = len(arr_split)
            num_cols = len(arr_split[0])
            for time in range(num_rows):
                for scenario in range(num_cols):
                    index = TimeScenarioIndex(time=time, scenario=scenario)
                    time_series[index] = float(arr_split[time][scenario])
    except FileNotFoundError:
        print(f"Error: File {file_ts} does not exists")
    return time_series
