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
from .expression_efficient import (
    ComponentParameterNode,
    ExpressionNodeEfficient,
    ParameterNode,
)
from .visitor import visit


@dataclass(frozen=True)
class ContextAdder(CopyVisitor):
    """
    Simply copies the whole AST but associates all variables and parameters
    to the provided component ID.
    """

    component_id: str

    # def variable(self, node: VariableNode) -> ExpressionNodeEfficient:
    #     return ComponentVariableNode(self.component_id, node.name)

    def parameter(self, node: ParameterNode) -> ExpressionNodeEfficient:
        return ComponentParameterNode(self.component_id, node.name)

    # def comp_variable(self, node: ComponentVariableNode) -> ExpressionNodeEfficient:
    #     raise ValueError(
    #         "This expression has already been associated to another component."
    #     )

    def comp_parameter(self, node: ComponentParameterNode) -> ExpressionNodeEfficient:
        raise ValueError(
            "This expression has already been associated to another component."
        )


def add_component_context(
    id: str, expression: ExpressionNodeEfficient
) -> ExpressionNodeEfficient:
    return visit(expression, ContextAdder(id))
