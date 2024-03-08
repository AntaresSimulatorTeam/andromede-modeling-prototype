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

import dataclasses
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from anytree import LevelOrderIter
from anytree import Node as TreeNode

from andromede.expression.expression import ExpressionNode
from andromede.model.constraint import Constraint
from andromede.model.model import Model, PortFieldDefinition, PortFieldId, model
from andromede.model.variable import Variable
from andromede.simulation.time_block import TimeBlock
from andromede.study.network import Component, Network, Node, create_component


@dataclass(frozen=True)
class InterDecisionTimeScenarioConfig:
    blocks: List[TimeBlock]
    scenarios: int


@dataclass(frozen=True)
class ConfiguredTree:
    node_to_config: Dict[TreeNode, InterDecisionTimeScenarioConfig]
    root: TreeNode = field(init=False)

    def __post_init__(self) -> None:
        # Stores the root, by getting it from any tree node
        object.__setattr__(self, "root", next(iter(self.node_to_config.keys())).root)


def create_single_node_decision_tree(
    blocks: List[TimeBlock], scenarios: int
) -> ConfiguredTree:
    time_scenario_config = InterDecisionTimeScenarioConfig(blocks, scenarios)

    root = TreeNode("root")
    configured_tree = ConfiguredTree(
        {
            root: time_scenario_config,
        },
    )

    return configured_tree


def _generate_tree_variables(
    variables: Dict[str, Variable], tree_node: TreeNode
) -> Iterable[Variable]:
    tree_variables = []
    for variable in variables.values():
        # Works as we do not allow variables in bounds, hence no problem to copy the corresponding expression nodes as is. If we had variables, we would have to replace the variable names by the ones with tree node information.
        tree_variables.append(
            dataclasses.replace(variable, name=f"{tree_node.name}_{variable.name}")
        )
    return tree_variables


def _generate_tree_constraints(
    constraints: Dict[str, Constraint], tree_node: TreeNode
) -> Iterable[Constraint]:
    # Goal is to replace variables in constraint, lower bound and upper bound with node variable
    raise NotImplementedError()


def _generate_tree_expression(
    expression: Optional[ExpressionNode], tree_node: TreeNode
) -> ExpressionNode:
    # Goal is to replace variables with node variable
    # Create a copy visitor to do so
    raise NotImplementedError()


def _generate_tree_port_field_definition(
    port_field_definition: Dict[PortFieldId, PortFieldDefinition], tree_node: TreeNode
) -> Iterable[PortFieldDefinition]:
    # Goal is to replace variables in the expression defining the port by node variable
    raise NotImplementedError()


def _generate_tree_model(
    tree_node: TreeNode,
    component: Component,
) -> Model:
    variables = _generate_tree_variables(
        component.model.variables,
        tree_node,
    )
    constraints = _generate_tree_constraints(component.model.constraints, tree_node)
    binding_constraints = _generate_tree_constraints(
        component.model.binding_constraints, tree_node
    )
    objective_operational_contribution = _generate_tree_expression(
        component.model.objective_operational_contribution, tree_node
    )
    objective_investment_contribution = _generate_tree_expression(
        component.model.objective_investment_contribution, tree_node
    )
    port_fields_definitions = _generate_tree_port_field_definition(
        component.model.port_fields_definitions, tree_node
    )
    tree_model = model(
        id=f"{tree_node.name}_{component.model.id}",
        constraints=constraints,
        binding_constraints=binding_constraints,
        parameters=component.model.parameters.values(),
        variables=variables,
        objective_operational_contribution=objective_operational_contribution,
        objective_investment_contribution=objective_investment_contribution,
        inter_block_dyn=component.model.inter_block_dyn,
        ports=component.model.ports.values(),
        port_fields_definitions=port_fields_definitions,
    )

    return tree_model


def _generate_network_on_node(network: Network, tree_node: TreeNode) -> Network:
    tree_node_network = Network(tree_node.name)

    for component in network.all_components:
        tree_node_model = _generate_tree_model(tree_node, component)

        # It would be nice to have the same treatment for nodes and components as they are actually the same thing...
        if isinstance(component, Node):
            network_node = Node(tree_node_model, id=f"{tree_node.name}_{component.id}")
            tree_node_network.add_node(network_node)
        else:
            tree_node_component = create_component(
                tree_node_model, id=f"{tree_node.name}_{component.id}"
            )
            tree_node_network.add_component(tree_node_component)

    for connection in network.connections:
        tree_node_network.connect(connection.port1, connection.port2)
    return tree_node_network


def create_network_on_tree(network: Network, tree: TreeNode) -> Dict[TreeNode, Network]:
    # On crée un gros modèle en dupliquant les variables; contraintes, etc à chaque noeud de l'arbre.
    # Pour le master on peut :
    #   - Utiliser uniquement les variables, contraintes, etc dont on va avoir besoin dans la construction du problème -> nécessite déjà d'avoir des infos sur la construction des problèmes alors qu'on agit au niveau modèle ici
    #   - Dupliquer tout le modèle, permet de mutualiser du code avec la partie composant par noeud et plus lisible. Seul inconvénient, modèle master un peu trop riche, pas besoin des infos "opérationnelles". Mais les modèles ne sont pas très "lourds" donc on peut se le permettre. C'est l'option choisie ici.
    if tree.size == 1:
        return {tree: network}
    else:
        node_to_network = {}
        for tree_node in LevelOrderIter(tree):
            node_to_network[tree_node] = _generate_network_on_node(network, tree_node)
        return node_to_network


def create_master_network(
    tree_node_to_network: Dict[TreeNode, Network],
    decision_coupling_model: Optional[Model],
) -> Network:
    # Current implementation so that tests pass for trees with one investment nodes (in test_xpansion)
    # The final implementation should gather all networks from tree nodes and connect the models with the decision coupling model (with ports)
    root = next(iter(tree_node_to_network.keys())).root
    return tree_node_to_network[root]
