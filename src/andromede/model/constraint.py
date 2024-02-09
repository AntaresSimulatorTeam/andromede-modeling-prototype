from typing import Optional

from andromede.expression.degree import is_constant
from andromede.expression.expression import (
    Comparator,
    ComparisonNode,
    ExpressionNode,
    literal,
)
from andromede.expression.print import print_expr


class Constraint:
    """
    A constraint linking variables and parameters of a model together.

    No variable is expected on the right hand side of the constraint.
    """

    name: str
    expression: ExpressionNode
    lower_bound: ExpressionNode
    upper_bound: ExpressionNode

    def __init__(
        self,
        name: str,
        expression: ExpressionNode,
        lower_bound: Optional[ExpressionNode] = None,
        upper_bound: Optional[ExpressionNode] = None,
    ) -> None:
        self.name = name
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
