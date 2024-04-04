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
from typing import Dict, List, Optional

from andromede.model import Model
from andromede.model.library import Library
from andromede.model.parsing import InputModel
from andromede.model.resolve_library import _resolve_model_identifier
from andromede.study import Component, PortRef
from andromede.study.components import Components, components
from andromede.study.parsing import InputComponents, InputPortConnections


def resolve_components_and_cnx(input_comp: InputComponents) -> Components:
    """
    Resolves:
    - components to be used for study
    - connections between components"""
    components_list = [_resolve_component(m.model, m.id) for m in input_comp.components]
    components_list.extend(_resolve_component(n.model, n.id) for n in input_comp.nodes)
    connections = {}

    for cnx in input_comp.connections:
        resolved_cnx = _resolve_connections(cnx, components_list)
        connections.update(resolved_cnx)

    return components(components_list, connections)


def _resolve_component(model_for_component: InputModel, component_id: str) -> Component:
    return Component(
        model=_resolve_model_identifier(model_for_component), id=component_id
    )


def _resolve_connections(
    connection: InputPortConnections,
    components_list: List[Component],
) -> Dict[str, List[PortRef]]:
    cnx_component1 = connection.component1
    cnx_component2 = connection.component2
    port1 = connection.port_1
    port2 = connection.port_2

    component_1 = _get_component_by_id(components_list, cnx_component1)
    component_2 = _get_component_by_id(components_list, cnx_component2)
    assert component_1 is not None and component_2 is not None
    port_ref_1 = PortRef(component_1, port1)
    port_ref_2 = PortRef(component_2, port2)
    return {connection.id: [port_ref_1, port_ref_2]}


def _get_component_by_id(
    components_list: List[Component], component_id: str
) -> Optional[Component]:
    components_dict = {component.id: component for component in components_list}
    return components_dict.get(component_id)


def consistency_check(
    input_components: Dict[str, Component], input_models: Dict[str, Model]
) -> bool:
    """
    Checks if all components in the Components instances have a valid model from the library.
    Returns True if all components are consistent, raises ValueError otherwis.
    """
    model_ids_set = input_models.keys()
    for component_id, component in input_components.items():
        if component.model.id not in model_ids_set:
            raise ValueError(
                f"Error: Component {component_id} has invalid model ID: {component.model.id}"
            )
    return True
