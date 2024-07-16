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
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from andromede.expression.degree import is_constant
from andromede.expression.equality import (
    expressions_equal,
    expressions_equal_if_present,
)

# from andromede.expression.expression import (
#     Comparator,
#     ComparisonNode,
#     ExpressionNode,
#     literal,
# )
from andromede.expression.expression_efficient import Comparator, ComparisonNode, is_unbound
from andromede.expression.linear_expression_efficient import (
    LinearExpressionEfficient,
    StandaloneConstraint,
    linear_expressions_equal,
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
    expression: LinearExpressionEfficient
    lower_bound: LinearExpressionEfficient = field(default=literal(-float("inf")))
    upper_bound: LinearExpressionEfficient = field(default=literal(float("inf")))
    context: ProblemContext = field(default=ProblemContext.OPERATIONAL)

    def __post_init__(
        self,
    ) -> None:
        if isinstance(self.expression, StandaloneConstraint):
            # Case where constraint is initialized with something like Constraint(var("x") <= var("y"))
            if not self.lower_bound.is_unbound() or not self.upper_bound.is_unbound():
                raise ValueError(
                    "Both comparison between two expressions and a bound are specfied, set either only a comparison between expressions or a single linear expression with bounds."
                )

            self.lower_bound = self.expression.lower_bound
            self.upper_bound = self.expression.upper_bound
            self.expression = self.expression.expression

        else:
            for bound in [self.lower_bound, self.upper_bound]:
                if not bound.is_constant():
                    raise ValueError(
                        f"The bounds of a constraint should not contain variables, {str(bound)} was given."
                    )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Constraint):
            return False
        return (
            self.name == other.name
            and linear_expressions_equal(self.expression, other.expression)
            and linear_expressions_equal(self.lower_bound, other.lower_bound)
            and linear_expressions_equal(self.upper_bound, other.upper_bound)
        )

    def __str__(self) -> str:
        return f"{str(self.lower_bound)} <= {str(self.expression)} <= {str(self.upper_bound)}"
