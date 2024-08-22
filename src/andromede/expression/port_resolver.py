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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List

from andromede.expression import CopyVisitor, literal, sum_expressions, visit
from andromede.expression.expression import (
    ExpressionNode,
    OptionalPortFieldNode,
    PortFieldAggregatorNode,
    PortFieldNode,
)
from andromede.model.port import PortFieldId


@dataclass(eq=True, frozen=True)
class PortFieldKey:
    """
    Identifies the expression node for one component and one port variable.
    """

    component_id: str
    port_variable_id: PortFieldId


@dataclass(frozen=True)
class PortResolver(CopyVisitor):
    """
    Duplicates the AST with replacement of port field nodes by
    their corresponding expression.
    """

    component_id: str
    ports_expressions: Dict[PortFieldKey, List[ExpressionNode]]

    def port_field(self, node: PortFieldNode) -> ExpressionNode:
        key = PortFieldKey(
            self.component_id, PortFieldId(node.port_name, node.field_name)
        )

        try:
            expressions = self.ports_expressions[key]
        except KeyError as err:
            raise KeyError(f"Key {key} not in registered port expressions") from err

        if len(expressions) != 1:
            raise ValueError(
                f"Invalid number of expression for port : {node.port_name}"
            )
        else:
            return expressions[0]

    def optional_port_field(self, node: OptionalPortFieldNode) -> ExpressionNode:
        optional_key = PortFieldKey(
            self.component_id, PortFieldId(node.port_name, node.field_name)
        )

        if optional_key in self.ports_expressions:
            return visit(PortFieldNode(node.port_name, node.field_name), self)
        else:
            return literal(node.value)

    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> ExpressionNode:
        if node.aggregator != "PortSum":
            raise NotImplementedError("Only PortSum is supported.")
        port_field_node = node.operand
        if not isinstance(port_field_node, PortFieldNode):
            raise ValueError(f"Should be a portFieldNode : {port_field_node}")

        expressions = self.ports_expressions.get(
            PortFieldKey(
                self.component_id,
                PortFieldId(port_field_node.port_name, port_field_node.field_name),
            ),
            [],
        )
        return sum_expressions(expressions)


def resolve_port(
    expression: ExpressionNode,
    component_id: str,
    ports_expressions: Dict[PortFieldKey, List[ExpressionNode]],
) -> ExpressionNode:
    return visit(expression, PortResolver(component_id, ports_expressions))
