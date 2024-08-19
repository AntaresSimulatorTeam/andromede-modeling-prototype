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

"""
Defines the model for generic expressions.
"""
import enum
import math
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Union

EPS = 10 ** (-16)


@dataclass(frozen=True)
class ExpressionNodeEfficient:
    """
    Base class for all nodes of the expression AST.

    Operators overloading is provided to help create expressions
    programmatically.

    Examples
        >>> expr = -var('x') + 5 / param('p')
    """

    def __neg__(self) -> "ExpressionNodeEfficient":
        return _negate_node(self)

    def __add__(self, rhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(rhs, lambda x: _add_node(self, x))

    def __radd__(self, lhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(lhs, lambda x: _add_node(x, self))

    def __sub__(self, rhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(rhs, lambda x: _substract_node(self, x))

    def __rsub__(self, lhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(lhs, lambda x: _substract_node(x, self))

    def __mul__(self, rhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(rhs, lambda x: _multiply_node(self, x))

    def __rmul__(self, lhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(lhs, lambda x: _multiply_node(x, self))

    def __truediv__(self, rhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(rhs, lambda x: _divide_node(self, x))

    def __rtruediv__(self, lhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(lhs, lambda x: _divide_node(x, self))

    def __le__(self, rhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(
            rhs, lambda x: ComparisonNode(self, x, Comparator.LESS_THAN)
        )

    def __ge__(self, rhs: Any) -> "ExpressionNodeEfficient":
        return _apply_if_node(
            rhs, lambda x: ComparisonNode(self, x, Comparator.GREATER_THAN)
        )

    def __eq__(self, rhs: Any) -> "ExpressionNodeEfficient":  # type: ignore
        return _apply_if_node(rhs, lambda x: ComparisonNode(self, x, Comparator.EQUAL))

    def sum(self) -> "ExpressionNodeEfficient":
        if isinstance(self, TimeOperatorNode):
            return TimeAggregatorNode(self, TimeAggregatorName.TIME_SUM, stay_roll=True)
        else:
            return _apply_if_node(
                self,
                lambda x: TimeAggregatorNode(
                    x, TimeAggregatorName.TIME_SUM, stay_roll=False
                ),
            )

    def sum_connections(self) -> "ExpressionNodeEfficient":
        if isinstance(self, PortFieldNode):
            return PortFieldAggregatorNode(
                self, aggregator=PortFieldAggregatorName.PORT_SUM
            )
        raise ValueError(
            f"sum_connections() applies only for PortFieldNode, whereas the current node is of type {type(self)}."
        )

    def shift(
        self,
        expressions: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
        ],
    ) -> "ExpressionNodeEfficient":
        return _apply_if_node(
            self,
            lambda x: TimeOperatorNode(
                x, TimeOperatorName.SHIFT, InstancesTimeIndex(expressions)
            ),
        )

    def eval(
        self,
        expressions: Union[
            int,
            "ExpressionNodeEfficient",
            List["ExpressionNodeEfficient"],
            "ExpressionRange",
        ],
    ) -> "ExpressionNodeEfficient":
        return _apply_if_node(
            self,
            lambda x: TimeOperatorNode(
                x, TimeOperatorName.EVALUATION, InstancesTimeIndex(expressions)
            ),
        )

    def expec(self) -> "ExpressionNodeEfficient":
        return _apply_if_node(
            self, lambda x: ScenarioOperatorNode(x, ScenarioOperatorName.EXPECTATION)
        )

    def variance(self) -> "ExpressionNodeEfficient":
        return _apply_if_node(
            self, lambda x: ScenarioOperatorNode(x, ScenarioOperatorName.Variance)
        )


def wrap_in_node(obj: Any) -> ExpressionNodeEfficient:
    if isinstance(obj, ExpressionNodeEfficient):
        return obj
    elif isinstance(obj, float) or isinstance(obj, int):
        return LiteralNode(float(obj))
    # Do not raise excpetion so that we can return NotImplemented in _apply_if_node
    # raise TypeError(f"Unable to wrap {obj} into an expression node")


def _apply_if_node(
    obj: Any, func: Callable[["ExpressionNodeEfficient"], "ExpressionNodeEfficient"]
) -> "ExpressionNodeEfficient":
    if as_node := wrap_in_node(obj):
        return func(as_node)
    else:
        return NotImplemented


def is_zero(node: ExpressionNodeEfficient) -> bool:
    # Faster implementation than expressions equal for this particular cases
    return isinstance(node, LiteralNode) and math.isclose(node.value, 0, abs_tol=EPS)


def is_one(node: ExpressionNodeEfficient) -> bool:
    # Faster implementation than expressions equal for this particular cases
    return isinstance(node, LiteralNode) and math.isclose(node.value, 1)


def is_minus_one(node: ExpressionNodeEfficient) -> bool:
    # Faster implementation than expressions equal for this particular cases
    return isinstance(node, LiteralNode) and math.isclose(node.value, -1)


def _negate_node(node: ExpressionNodeEfficient) -> ExpressionNodeEfficient:
    if isinstance(node, LiteralNode):
        return LiteralNode(-node.value)
    elif isinstance(node, NegationNode):
        return node.operand
    else:
        return NegationNode(node)


def _add_node(
    lhs: ExpressionNodeEfficient, rhs: ExpressionNodeEfficient
) -> ExpressionNodeEfficient:
    if is_zero(lhs):
        return rhs
    if is_zero(rhs):
        return lhs
    # TODO: How can we use the equality visitor here (simple import -> circular import), copy code here ?
    if expressions_equal(lhs, -rhs):
        return LiteralNode(0)
    if isinstance(lhs, LiteralNode) and isinstance(rhs, LiteralNode):
        return LiteralNode(lhs.value + rhs.value)
    if _are_parameter_nodes_equal(lhs, rhs):
        return MultiplicationNode(LiteralNode(2), lhs)
    if (lhs_is_param := isinstance(lhs, ParameterNode)) or (
        rhs_is_param := isinstance(rhs, ParameterNode)
    ):
        if lhs_is_param:
            param_node = lhs
            other = rhs
        elif rhs_is_param:
            param_node = rhs
            other = lhs

        if isinstance(other, MultiplicationNode):
            if _are_parameter_nodes_equal(param_node, other.left):
                return MultiplicationNode(
                    _add_node(LiteralNode(1), other.right), param_node
                )
            elif _are_parameter_nodes_equal(param_node, other.right):
                return MultiplicationNode(
                    _add_node(LiteralNode(1), other.left), param_node
                )

    if isinstance(lhs, MultiplicationNode) and isinstance(rhs, MultiplicationNode):
        if _are_parameter_nodes_equal(lhs.left, rhs.left):
            return MultiplicationNode(_add_node(lhs.right, rhs.right), lhs.left)
        elif _are_parameter_nodes_equal(lhs.left, rhs.right):
            return MultiplicationNode(_add_node(lhs.right, rhs.left), lhs.left)
        elif _are_parameter_nodes_equal(lhs.right, rhs.left):
            return MultiplicationNode(_add_node(lhs.left, rhs.right), lhs.right)
        elif _are_parameter_nodes_equal(lhs.right, rhs.right):
            return MultiplicationNode(_add_node(lhs.left, rhs.left), lhs.right)
    else:
        return AdditionNode(lhs, rhs)


# Better if we could use equality visitor
def _are_parameter_nodes_equal(
    lhs: ExpressionNodeEfficient, rhs: ExpressionNodeEfficient
) -> bool:
    return (
        isinstance(lhs, ParameterNode)
        and isinstance(rhs, ParameterNode)
        and lhs.name == rhs.name
    )


# def _is_parameter_multiplication(node: ExpressionNodeEfficient, name: str):
#     return isinstance(node, MultiplicationNode) and ((isinstance(node.left, ParameterNode) and node.left.name == name) or


def _substract_node(
    lhs: ExpressionNodeEfficient, rhs: ExpressionNodeEfficient
) -> ExpressionNodeEfficient:
    if is_zero(lhs):
        return -rhs
    if is_zero(rhs):
        return lhs
    # TODO: How can we use the equality visitor here (simple import -> circular import), copy code here ?
    if expressions_equal(lhs, rhs):
        return LiteralNode(0)
    if isinstance(lhs, LiteralNode) and isinstance(rhs, LiteralNode):
        return LiteralNode(lhs.value - rhs.value)
    if _are_parameter_nodes_equal(lhs, -rhs):
        return MultiplicationNode(LiteralNode(2), lhs)
    if (lhs_is_param := isinstance(lhs, ParameterNode)) or (
        rhs_is_param := isinstance(rhs, ParameterNode)
    ):
        if lhs_is_param:
            param_node = lhs
            other = rhs
        elif rhs_is_param:
            param_node = rhs
            other = lhs

        if isinstance(other, MultiplicationNode):
            if _are_parameter_nodes_equal(param_node, other.left):
                if lhs_is_param:
                    return MultiplicationNode(
                        _substract_node(LiteralNode(1), other.right), param_node
                    )
                elif rhs_is_param:
                    return MultiplicationNode(
                        _substract_node(other.right, LiteralNode(1)), param_node
                    )
            elif _are_parameter_nodes_equal(param_node, other.right):
                if lhs_is_param:
                    return MultiplicationNode(
                        _substract_node(LiteralNode(1), other.left), param_node
                    )
                elif rhs_is_param:
                    return MultiplicationNode(
                        _substract_node(other.left, LiteralNode(1)), param_node
                    )

    if isinstance(lhs, MultiplicationNode) and isinstance(rhs, MultiplicationNode):
        if _are_parameter_nodes_equal(lhs.left, rhs.left):
            return MultiplicationNode(_substract_node(lhs.right, rhs.right), lhs.left)
        elif _are_parameter_nodes_equal(lhs.left, rhs.right):
            return MultiplicationNode(_substract_node(lhs.right, rhs.left), lhs.left)
        elif _are_parameter_nodes_equal(lhs.right, rhs.left):
            return MultiplicationNode(_substract_node(lhs.left, rhs.right), lhs.right)
        elif _are_parameter_nodes_equal(lhs.right, rhs.right):
            return MultiplicationNode(_substract_node(lhs.left, rhs.left), lhs.right)
    else:
        return SubstractionNode(lhs, rhs)


def _multiply_node(
    lhs: ExpressionNodeEfficient, rhs: ExpressionNodeEfficient
) -> ExpressionNodeEfficient:
    if is_zero(lhs) or is_zero(rhs):
        return LiteralNode(0)
    if is_one(lhs):
        return rhs
    if is_one(rhs):
        return lhs
    if is_minus_one(lhs):
        return -rhs
    if is_minus_one(rhs):
        return -lhs
    if isinstance(lhs, LiteralNode) and isinstance(rhs, LiteralNode):
        return LiteralNode(lhs.value * rhs.value)
    else:
        return MultiplicationNode(lhs, rhs)


def _divide_node(
    lhs: ExpressionNodeEfficient, rhs: ExpressionNodeEfficient
) -> ExpressionNodeEfficient:
    if is_one(rhs):
        return lhs
    if is_minus_one(rhs):
        return -lhs
    if isinstance(lhs, LiteralNode) and isinstance(rhs, LiteralNode):
        # This could raise division by 0 error
        return LiteralNode(lhs.value / rhs.value)

    else:
        return DivisionNode(lhs, rhs)


@dataclass(frozen=True, eq=False)
class PortFieldNode(ExpressionNodeEfficient):
    """
    References a port field.
    """

    port_name: str
    field_name: str


@dataclass(frozen=True, eq=False)
class ParameterNode(ExpressionNodeEfficient):
    name: str


@dataclass(frozen=True, eq=False)
class ComponentParameterNode(ExpressionNodeEfficient):
    """
    Represents one parameter of one component.

    When building actual equations for a system,
    we need to associated each parameter to its
    actual component, at some point.
    """

    component_id: str
    name: str


def param(name: str) -> ExpressionNodeEfficient:
    return ParameterNode(name)


def comp_param(component_id: str, name: str) -> ExpressionNodeEfficient:
    return ComponentParameterNode(component_id, name)


@dataclass(frozen=True, eq=False)
class LiteralNode(ExpressionNodeEfficient):
    value: float


def literal(value: float) -> ExpressionNodeEfficient:
    return LiteralNode(value)


def is_unbound(expr: ExpressionNodeEfficient) -> bool:
    return isinstance(expr, LiteralNode) and (abs(expr.value) == float("inf"))


@dataclass(frozen=True, eq=False)
class UnaryOperatorNode(ExpressionNodeEfficient):
    operand: ExpressionNodeEfficient


class PortFieldAggregatorName(enum.Enum):
    # String value of enum must match the name of the PortAggregator class in port_operator.py
    PORT_SUM = "PortSum"


@dataclass(frozen=True, eq=False)
class PortFieldAggregatorNode(UnaryOperatorNode):
    aggregator: PortFieldAggregatorName

    def __post_init__(self) -> None:
        if not isinstance(self.aggregator, PortFieldAggregatorName):
            raise TypeError(
                f"PortFieldAggregatorNode.name should of class PortFieldAggregatorName, but {self.aggregator} of type {type(self.aggregator)} was given"
            )


@dataclass(frozen=True, eq=False)
class NegationNode(UnaryOperatorNode):
    pass


@dataclass(frozen=True, eq=False)
class BinaryOperatorNode(ExpressionNodeEfficient):
    left: ExpressionNodeEfficient
    right: ExpressionNodeEfficient


class Comparator(enum.Enum):
    LESS_THAN = "LESS_THAN"
    EQUAL = "EQUAL"
    GREATER_THAN = "GREATER_THAN"


@dataclass(frozen=True, eq=False)
class ComparisonNode(BinaryOperatorNode):
    comparator: Comparator


@dataclass(frozen=True, eq=False)
class AdditionNode(BinaryOperatorNode):
    pass


@dataclass(frozen=True, eq=False)
class SubstractionNode(BinaryOperatorNode):
    pass


@dataclass(frozen=True, eq=False)
class MultiplicationNode(BinaryOperatorNode):
    pass


@dataclass(frozen=True, eq=False)
class DivisionNode(BinaryOperatorNode):
    pass


@dataclass(frozen=True, eq=False)
class ExpressionRange:
    start: ExpressionNodeEfficient
    stop: ExpressionNodeEfficient
    step: Optional[ExpressionNodeEfficient] = None

    def __post_init__(self) -> None:
        for attribute in self.__dict__:
            value = getattr(self, attribute)
            object.__setattr__(
                self, attribute, wrap_in_node(value) if value is not None else value
            )


IntOrExpr = Union[int, ExpressionNodeEfficient]


def expression_range(
    start: IntOrExpr, stop: IntOrExpr, step: Optional[IntOrExpr] = None
) -> ExpressionRange:
    return ExpressionRange(
        start=wrap_in_node(start),
        stop=wrap_in_node(stop),
        step=None if step is None else wrap_in_node(step),
    )


@dataclass(frozen=True)
class InstancesTimeIndex:
    """
    Defines a set of time indices on which a time operator operates.

    In particular, it defines time indices created by the shift operator.

    The actual indices can either be defined as a time range defined by
    2 expression, or as a list of expressions.
    """

    expressions: Union[List[ExpressionNodeEfficient], ExpressionRange]

    def __init__(
        self,
        expressions: Union[
            int, ExpressionNodeEfficient, List[ExpressionNodeEfficient], ExpressionRange
        ],
    ) -> None:
        if not isinstance(
            expressions, (int, ExpressionNodeEfficient, list, ExpressionRange)
        ):
            raise TypeError(
                f"{expressions} must be of type among {{int, ExpressionNodeEfficient, List[ExpressionNodeEfficient], ExpressionRange}}"
            )
        if isinstance(expressions, list) and not all(
            isinstance(x, ExpressionNodeEfficient) for x in expressions
        ):
            raise TypeError(
                f"All elements of {expressions} must be of type ExpressionNodeEfficient"
            )

        if isinstance(expressions, (int, ExpressionNodeEfficient)):
            object.__setattr__(self, "expressions", [wrap_in_node(expressions)])
        else:
            object.__setattr__(self, "expressions", expressions)

    def __hash__(self) -> int:
        # Maybe if/else not needed and always using the tuple works ?
        if isinstance(self.expressions, list):
            return hash(tuple(self.expressions))
        else:
            return hash(self.expressions)

    def is_simple(self) -> bool:
        if isinstance(self.expressions, list):
            return len(self.expressions) == 1
        else:
            # TODO: We could also check that if a range only includes literal nodes, compute the length of the range, if it's one return True. This is more complicated, I do not know if we want to do this
            return False


class TimeOperatorName(enum.Enum):
    # String value of enum must match the name of the TimeOperator class in time_operator.py
    SHIFT = "TimeShift"
    EVALUATION = "TimeEvaluation"


class TimeAggregatorName(enum.Enum):
    # String value of enum must match the name of the TimeAggregator class in time_operator.py
    TIME_SUM = "TimeSum"


@dataclass(frozen=True, eq=False)
class TimeOperatorNode(UnaryOperatorNode):
    name: TimeOperatorName
    instances_index: InstancesTimeIndex

    def __post_init__(self) -> None:
        if not isinstance(self.name, TimeOperatorName):
            raise TypeError(
                f"TimeOperatorNode.name should of class TimeOperatorName, but {self.name} of type {type(self.name)} was given"
            )


@dataclass(frozen=True, eq=False)
class TimeAggregatorNode(UnaryOperatorNode):
    name: TimeAggregatorName
    stay_roll: bool  # TODO: Is it still useful ?

    def __post_init__(self) -> None:
        if not isinstance(self.name, TimeAggregatorName):
            raise TypeError(
                f"TimeAggregatorNode.name should of class TimeAggregatorName, but {self.name} of type {type(self.name)} was given"
            )


class ScenarioOperatorName(enum.Enum):
    # String value of enum must match the name of the ScenarioOperator class in scenario_operator.py
    EXPECTATION = "Expectation"
    VARIANCE = "Variance"


@dataclass(frozen=True, eq=False)
class ScenarioOperatorNode(UnaryOperatorNode):
    name: ScenarioOperatorName

    def __post_init__(self) -> None:
        if not isinstance(self.name, ScenarioOperatorName):
            raise TypeError(
                f"ScenarioOperatorNode.name should of class ScenarioOperatorName, but {self.name} of type {type(self.name)} was given"
            )


@dataclass(frozen=True)
class EqualityVisitor:
    abs_tol: float = 0
    rel_tol: float = 0

    def __post_init__(self) -> None:
        if self.abs_tol < 0:
            raise ValueError(
                f"Absolute comparison tolerance must be >= 0, got {self.abs_tol}"
            )
        if self.rel_tol < 0:
            raise ValueError(
                f"Relative comparison tolerance must be >= 0, got {self.rel_tol}"
            )

    def visit(
        self, left: ExpressionNodeEfficient, right: ExpressionNodeEfficient
    ) -> bool:
        if left.__class__ != right.__class__:
            return False
        if isinstance(left, LiteralNode) and isinstance(right, LiteralNode):
            return self.literal(left, right)
        if isinstance(left, NegationNode) and isinstance(right, NegationNode):
            return self.negation(left, right)
        if isinstance(left, AdditionNode) and isinstance(right, AdditionNode):
            return self.addition(left, right)
        if isinstance(left, SubstractionNode) and isinstance(right, SubstractionNode):
            return self.substraction(left, right)
        if isinstance(left, DivisionNode) and isinstance(right, DivisionNode):
            return self.division(left, right)
        if isinstance(left, MultiplicationNode) and isinstance(
            right, MultiplicationNode
        ):
            return self.multiplication(left, right)
        if isinstance(left, ComparisonNode) and isinstance(right, ComparisonNode):
            return self.comparison(left, right)
        # if isinstance(left, VariableNode) and isinstance(right, VariableNode):
        #     return self.variable(left, right)
        if isinstance(left, ParameterNode) and isinstance(right, ParameterNode):
            return self.parameter(left, right)
        if isinstance(left, ComponentParameterNode) and isinstance(
            right, ComponentParameterNode
        ):
            return self.comp_parameter(left, right)
        if isinstance(left, TimeOperatorNode) and isinstance(right, TimeOperatorNode):
            return self.time_operator(left, right)
        if isinstance(left, TimeAggregatorNode) and isinstance(
            right, TimeAggregatorNode
        ):
            return self.time_aggregator(left, right)
        if isinstance(left, ScenarioOperatorNode) and isinstance(
            right, ScenarioOperatorNode
        ):
            return self.scenario_operator(left, right)
        if isinstance(left, PortFieldNode) and isinstance(right, PortFieldNode):
            return self.port_field(left, right)
        if isinstance(left, PortFieldAggregatorNode) and isinstance(
            right, PortFieldAggregatorNode
        ):
            return self.port_field_aggregator(left, right)
        raise NotImplementedError(f"Equality not implemented for {left.__class__}")

    def literal(self, left: LiteralNode, right: LiteralNode) -> bool:
        return math.isclose(
            left.value, right.value, abs_tol=self.abs_tol, rel_tol=self.rel_tol
        )

    def _visit_operands(
        self, left: BinaryOperatorNode, right: BinaryOperatorNode
    ) -> bool:
        return self.visit(left.left, right.left) and self.visit(left.right, right.right)

    def negation(self, left: NegationNode, right: NegationNode) -> bool:
        return self.visit(left.operand, right.operand)

    def addition(self, left: AdditionNode, right: AdditionNode) -> bool:
        # TODO: Commutativty ??? Cannot detect that a+b == b+a
        return self._visit_operands(left, right)

    def substraction(self, left: SubstractionNode, right: SubstractionNode) -> bool:
        return self._visit_operands(left, right)

    def multiplication(
        self, left: MultiplicationNode, right: MultiplicationNode
    ) -> bool:
        return self._visit_operands(left, right)

    def division(self, left: DivisionNode, right: DivisionNode) -> bool:
        return self._visit_operands(left, right)

    def comparison(self, left: ComparisonNode, right: ComparisonNode) -> bool:
        return left.comparator == right.comparator and self._visit_operands(left, right)

    # def variable(self, left: VariableNode, right: VariableNode) -> bool:
    #     return left.name == right.name

    def parameter(self, left: ParameterNode, right: ParameterNode) -> bool:
        return left.name == right.name

    def comp_parameter(
        self, left: ComponentParameterNode, right: ComponentParameterNode
    ) -> bool:
        return left.component_id == right.component_id and left.name == right.name

    def expression_range(self, left: ExpressionRange, right: ExpressionRange) -> bool:
        if not self.visit(left.start, right.start):
            return False
        if not self.visit(left.stop, right.stop):
            return False
        if left.step is not None and right.step is not None:
            return self.visit(left.step, right.step)
        return left.step is None and right.step is None

    def instances_index(self, lhs: InstancesTimeIndex, rhs: InstancesTimeIndex) -> bool:
        if isinstance(lhs.expressions, ExpressionRange) and isinstance(
            rhs.expressions, ExpressionRange
        ):
            return self.expression_range(lhs.expressions, rhs.expressions)
        if isinstance(lhs.expressions, list) and isinstance(rhs.expressions, list):
            return len(lhs.expressions) == len(rhs.expressions) and all(
                self.visit(l, r) for l, r in zip(lhs.expressions, rhs.expressions)
            )
        return False

    def time_operator(self, left: TimeOperatorNode, right: TimeOperatorNode) -> bool:
        return (
            left.name == right.name
            and self.instances_index(left.instances_index, right.instances_index)
            and self.visit(left.operand, right.operand)
        )

    def time_aggregator(
        self, left: TimeAggregatorNode, right: TimeAggregatorNode
    ) -> bool:
        return (
            left.name == right.name
            and left.stay_roll == right.stay_roll
            and self.visit(left.operand, right.operand)
        )

    def scenario_operator(
        self, left: ScenarioOperatorNode, right: ScenarioOperatorNode
    ) -> bool:
        return left.name == right.name and self.visit(left.operand, right.operand)

    def port_field(self, left: PortFieldNode, right: PortFieldNode) -> bool:
        return left.port_name == right.port_name and left.field_name == right.field_name

    def port_field_aggregator(
        self, left: PortFieldAggregatorNode, right: PortFieldAggregatorNode
    ) -> bool:
        return left.aggregator == right.aggregator and self.visit(
            left.operand, right.operand
        )


def expressions_equal(
    left: ExpressionNodeEfficient,
    right: ExpressionNodeEfficient,
    abs_tol: float = 0,
    rel_tol: float = 0,
) -> bool:
    """
    True if both expression nodes are equal. Literal values may be compared with absolute or relative tolerance.
    """
    return EqualityVisitor(abs_tol, rel_tol).visit(left, right)


def expressions_equal_if_present(
    lhs: Optional[ExpressionNodeEfficient], rhs: Optional[ExpressionNodeEfficient]
) -> bool:
    if lhs is None and rhs is None:
        return True
    elif lhs is None or rhs is None:
        return False
    else:
        return expressions_equal(lhs, rhs)
