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

from andromede.expression.equality import (
    expressions_equal,
    expressions_equal_if_present,
)
from andromede.expression.indexing_structure import IndexingStructure
from andromede.expression.linear_expression_efficient import LinearExpressionEfficient
from andromede.model.common import ProblemContext, ValueType


@dataclass
class Variable:
    """
    A decision variable of the model.
    """

    name: str
    data_type: ValueType
    lower_bound: Optional[LinearExpressionEfficient]
    upper_bound: Optional[LinearExpressionEfficient]
    structure: IndexingStructure
    context: ProblemContext

    def __post_init__(self) -> None:
        if self.lower_bound and not self.lower_bound.is_constant():
            raise ValueError("Lower bounds of variables must be constant")
        if self.upper_bound and not self.upper_bound.is_constant():
            raise ValueError("Upper bounds of variables must be constant")

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Variable):
            return False
        return (
            self.name == other.name
            and self.data_type == other.data_type
            and expressions_equal_if_present(self.lower_bound, other.lower_bound)
            and expressions_equal_if_present(self.upper_bound, other.upper_bound)
            and self.structure == other.structure
        )


def int_variable(
    name: str,
    lower_bound: Optional[LinearExpressionEfficient] = None,
    upper_bound: Optional[LinearExpressionEfficient] = None,
    structure: IndexingStructure = IndexingStructure(True, True),
    context: ProblemContext = ProblemContext.OPERATIONAL,
) -> Variable:
    return Variable(
        name, ValueType.INTEGER, lower_bound, upper_bound, structure, context
    )


def float_variable(
    name: str,
    lower_bound: Optional[LinearExpressionEfficient] = None,
    upper_bound: Optional[LinearExpressionEfficient] = None,
    structure: IndexingStructure = IndexingStructure(True, True),
    context: ProblemContext = ProblemContext.OPERATIONAL,
) -> Variable:
    return Variable(name, ValueType.FLOAT, lower_bound, upper_bound, structure, context)
