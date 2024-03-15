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
from typing import Any, Optional

from andromede.expression import ExpressionNode
from andromede.expression.degree import is_constant
from andromede.expression.equality import expressions_equal
from andromede.expression.indexing_structure import IndexingStructure
from andromede.model.common import ProblemContext, ValueType


@dataclass
class Variable:
    """
    A decision variable of the model.
    """

    name: str
    data_type: ValueType
    lower_bound: Optional[ExpressionNode]
    upper_bound: Optional[ExpressionNode]
    structure: IndexingStructure
    context: ProblemContext

    def __post_init__(self) -> None:
        if self.lower_bound and not is_constant(self.lower_bound):
            raise ValueError("Lower bounds of variables must be constant")
        if self.upper_bound and not is_constant(self.upper_bound):
            raise ValueError("Upper bounds of variables must be constant")

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Variable):
            return False
        return (
            self.name == other.name
            and self.data_type == other.data_type
            and _expressions_equal_if_present(self.lower_bound, other.lower_bound)
            and _expressions_equal_if_present(self.upper_bound, other.upper_bound)
            and self.structure == other.structure
        )


def _expressions_equal_if_present(
    lhs: Optional[ExpressionNode], rhs: Optional[ExpressionNode]
) -> bool:
    if lhs is None and rhs is None:
        return True
    elif lhs is None or rhs is None:
        return False
    else:
        return expressions_equal(lhs, rhs)


def int_variable(
    name: str,
    lower_bound: Optional[ExpressionNode] = None,
    upper_bound: Optional[ExpressionNode] = None,
    structure: IndexingStructure = IndexingStructure(True, True),
    context: ProblemContext = ProblemContext.OPERATIONAL,
) -> Variable:
    return Variable(
        name, ValueType.INTEGER, lower_bound, upper_bound, structure, context
    )


def float_variable(
    name: str,
    lower_bound: Optional[ExpressionNode] = None,
    upper_bound: Optional[ExpressionNode] = None,
    structure: IndexingStructure = IndexingStructure(True, True),
    context: ProblemContext = ProblemContext.OPERATIONAL,
) -> Variable:
    return Variable(name, ValueType.FLOAT, lower_bound, upper_bound, structure, context)
