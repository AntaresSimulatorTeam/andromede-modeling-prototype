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

from andromede.expression.degree import is_constant
from andromede.expression.equality import (
    expressions_equal,
    expressions_equal_if_present,
)
from andromede.expression.expression import (
    Comparator,
    ComparisonNode,
    ExpressionNode,
    literal,
)
from andromede.expression.print import print_expr
from andromede.model.common import ProblemContext


@dataclass
class Constraint:
    """
    A constraint linking variables and parameters of a model together.

    No variable is expected on the right hand side of the constraint.
    """

    name: str
    expression: ExpressionNode
    lower_bound: ExpressionNode
    upper_bound: ExpressionNode
    context: ProblemContext

    def __init__(
        self,
        name: str,
        expression: ExpressionNode,
        lower_bound: Optional[ExpressionNode] = None,
        upper_bound: Optional[ExpressionNode] = None,
        context: ProblemContext = ProblemContext.OPERATIONAL,
    ) -> None:
        self.name = name
        self.context = context

        if isinstance(expression, ComparisonNode):
            if lower_bound is not None or upper_bound is not None:
                raise ValueError(
                    "Both comparison between two expressions and a bound are specfied, set either only a comparison between expressions or a single linear expression with bounds."
                )

            merged_expr = expression.left - expression.right
            self.expression = merged_expr

            if expression.comparator == Comparator.LESS_THAN:
                # lhs - rhs <= 0
                self.upper_bound = literal(0)
                self.lower_bound = literal(-float("inf"))
            elif expression.comparator == Comparator.GREATER_THAN:
                # lhs - rhs >= 0
                self.lower_bound = literal(0)
                self.upper_bound = literal(float("inf"))
            else:  # lhs - rhs == 0
                self.lower_bound = literal(0)
                self.upper_bound = literal(0)
        else:
            for bound in [lower_bound, upper_bound]:
                if bound is not None and not is_constant(bound):
                    raise ValueError(
                        f"The bounds of a constraint should not contain variables, {print_expr(bound)} was given."
                    )

            self.expression = expression
            if lower_bound is not None:
                self.lower_bound = lower_bound
            else:
                self.lower_bound = literal(-float("inf"))

            if upper_bound is not None:
                self.upper_bound = upper_bound
            else:
                self.upper_bound = literal(float("inf"))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Constraint):
            return False
        return (
            self.name == other.name
            and expressions_equal(self.expression, other.expression)
            and expressions_equal_if_present(self.lower_bound, other.lower_bound)
            and expressions_equal_if_present(self.upper_bound, other.upper_bound)
        )
