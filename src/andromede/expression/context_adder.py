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

from dataclasses import dataclass

from . import CopyVisitor
from .expression import (
    ComponentParameterNode,
    ComponentVariableNode,
    DecisionTreeParameterNode,
    DecisionTreeVariableNode,
    ExpressionNode,
    ParameterNode,
    VariableNode,
)
from .visitor import visit


@dataclass(frozen=True)
class ContextAdder(CopyVisitor):
    """
    Simply copies the whole AST but associates all variables and parameters
    to the provided context's ID.
    """

    def dt_variable(self, node: DecisionTreeVariableNode) -> ExpressionNode:
        raise NotImplementedError()

    def dt_parameter(self, node: DecisionTreeParameterNode) -> ExpressionNode:
        raise NotImplementedError()


@dataclass(frozen=True)
class ComponentAdder(ContextAdder):
    """
    A ContextAdder where the context is the component's ID
    """

    component_id: str

    def variable(self, node: VariableNode) -> ExpressionNode:
        return ComponentVariableNode(self.component_id, node.name)

    def parameter(self, node: ParameterNode) -> ExpressionNode:
        return ComponentParameterNode(self.component_id, node.name)

    def comp_variable(self, node: ComponentVariableNode) -> ExpressionNode:
        raise ValueError(
            "This expression has already been associated to another component."
        )

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNode:
        raise ValueError(
            "This expression has already been associated to another component."
        )


def add_component_context(id: str, expression: ExpressionNode) -> ExpressionNode:
    return visit(expression, ComponentAdder(id))


@dataclass(frozen=True)
class DecisionTreeAdder(ContextAdder):
    """
    A ContextAdder where the context is the decision tree's ID
    """

    decision_tree_id: str

    def variable(self, node: VariableNode) -> ExpressionNode:
        raise ValueError("This expression must first be associated to a component.")

    def parameter(self, node: ParameterNode) -> ExpressionNode:
        raise ValueError("This expression must first be associated to a component.")

    def comp_variable(self, node: ComponentVariableNode) -> ExpressionNode:
        return DecisionTreeVariableNode(
            self.decision_tree_id, node.component_id, node.name
        )

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNode:
        return DecisionTreeParameterNode(
            self.decision_tree_id, node.component_id, node.name
        )


def add_decision_tree_context(id: str, expression: ExpressionNode) -> ExpressionNode:
    return visit(expression, DecisionTreeAdder(id))
