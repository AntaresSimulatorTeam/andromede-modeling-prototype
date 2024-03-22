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
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence, Union

import andromede.expression.port_operator
import andromede.expression.scenario_operator
import andromede.expression.time_operator


class Instances(enum.Enum):
    SIMPLE = "SIMPLE"
    MULTIPLE = "MULTIPLE"


@dataclass(frozen=True)
class ExpressionNode:
    """
    Base class for all nodes of the expression AST.

    Operators overloading is provided to help create expressions
    programmatically.

    Examples
        >>> expr = -var('x') + 5 / param('p')
    """

    instances: Instances = field(init=False, default=Instances.SIMPLE)

    def __neg__(self) -> "ExpressionNode":
        return NegationNode(self)

    def __add__(self, rhs: Any) -> "ExpressionNode":
        return _apply_if_node(rhs, lambda x: AdditionNode(self, x))

    def __radd__(self, lhs: Any) -> "ExpressionNode":
        return _apply_if_node(lhs, lambda x: AdditionNode(x, self))

    def __sub__(self, rhs: Any) -> "ExpressionNode":
        return _apply_if_node(rhs, lambda x: SubstractionNode(self, x))

    def __rsub__(self, lhs: Any) -> "ExpressionNode":
        return _apply_if_node(lhs, lambda x: SubstractionNode(x, self))

    def __mul__(self, rhs: Any) -> "ExpressionNode":
        return _apply_if_node(rhs, lambda x: MultiplicationNode(self, x))

    def __rmul__(self, lhs: Any) -> "ExpressionNode":
        return _apply_if_node(lhs, lambda x: MultiplicationNode(x, self))

    def __truediv__(self, rhs: Any) -> "ExpressionNode":
        return _apply_if_node(rhs, lambda x: DivisionNode(self, x))

    def __rtruediv__(self, lhs: Any) -> "ExpressionNode":
        return _apply_if_node(lhs, lambda x: DivisionNode(x, self))

    def __le__(self, rhs: Any) -> "ExpressionNode":
        return _apply_if_node(
            rhs, lambda x: ComparisonNode(self, x, Comparator.LESS_THAN)
        )

    def __ge__(self, rhs: Any) -> "ExpressionNode":
        return _apply_if_node(
            rhs, lambda x: ComparisonNode(self, x, Comparator.GREATER_THAN)
        )

    def __eq__(self, rhs: Any) -> "ExpressionNode":  # type: ignore
        return _apply_if_node(rhs, lambda x: ComparisonNode(self, x, Comparator.EQUAL))

    def sum(self) -> "ExpressionNode":
        if isinstance(self, TimeOperatorNode):
            return TimeAggregatorNode(self, "TimeSum", stay_roll=True)
        else:
            return _apply_if_node(
                self, lambda x: TimeAggregatorNode(x, "TimeSum", stay_roll=False)
            )

    def sum_connections(self) -> "ExpressionNode":
        if isinstance(self, PortFieldNode):
            return PortFieldAggregatorNode(self, aggregator="PortSum")
        raise ValueError(
            f"sum_connections() applies only for PortFieldNode, whereas the current node is of type {type(self)}."
        )

    def shift(
        self,
        expressions: Union[
            int, "ExpressionNode", List["ExpressionNode"], "ExpressionRange"
        ],
    ) -> "ExpressionNode":
        return _apply_if_node(
            self,
            lambda x: TimeOperatorNode(x, "TimeShift", InstancesTimeIndex(expressions)),
        )

    def eval(
        self,
        expressions: Union[
            int, "ExpressionNode", List["ExpressionNode"], "ExpressionRange"
        ],
    ) -> "ExpressionNode":
        return _apply_if_node(
            self,
            lambda x: TimeOperatorNode(
                x, "TimeEvaluation", InstancesTimeIndex(expressions)
            ),
        )

    def expec(self) -> "ExpressionNode":
        return _apply_if_node(self, lambda x: ScenarioOperatorNode(x, "Expectation"))

    def variance(self) -> "ExpressionNode":
        return _apply_if_node(self, lambda x: ScenarioOperatorNode(x, "Variance"))


def _wrap_in_node(obj: Any) -> ExpressionNode:
    if isinstance(obj, ExpressionNode):
        return obj
    elif isinstance(obj, float) or isinstance(obj, int):
        return LiteralNode(float(obj))
    raise TypeError(f"Unable to wrap {obj} into an expression node")


def _apply_if_node(
    obj: Any, func: Callable[["ExpressionNode"], "ExpressionNode"]
) -> "ExpressionNode":
    if as_node := _wrap_in_node(obj):
        return func(as_node)
    else:
        return NotImplemented


@dataclass(frozen=True, eq=False)
class VariableNode(ExpressionNode):
    name: str


def var(name: str) -> VariableNode:
    return VariableNode(name)


@dataclass(frozen=True, eq=False)
class PortFieldNode(ExpressionNode):
    """
    References a port field.
    """

    port_name: str
    field_name: str


def port_field(port_name: str, field_name: str) -> PortFieldNode:
    return PortFieldNode(port_name, field_name)


@dataclass(frozen=True, eq=False)
class ParameterNode(ExpressionNode):
    name: str


def param(name: str) -> ParameterNode:
    return ParameterNode(name)


@dataclass(frozen=True, eq=False)
class ComponentParameterNode(ExpressionNode):
    """
    Represents one parameter of one component.

    When building actual equations for a system,
    we need to associated each parameter to its
    actual component, at some point.
    """

    component_id: str
    name: str


def comp_param(component_id: str, name: str) -> ComponentParameterNode:
    return ComponentParameterNode(component_id, name)


@dataclass(frozen=True, eq=False)
class ComponentVariableNode(ExpressionNode):
    """
    Represents one variable of one component.

    When building actual equations for a system,
    we need to associated each variable to its
    actual component, at some point.
    """

    component_id: str
    name: str


def comp_var(component_id: str, name: str) -> ComponentVariableNode:
    return ComponentVariableNode(component_id, name)


@dataclass(frozen=True, eq=False)
class LiteralNode(ExpressionNode):
    value: float


def literal(value: float) -> LiteralNode:
    return LiteralNode(value)


def is_unbound(expr: ExpressionNode) -> bool:
    return isinstance(expr, LiteralNode) and (abs(expr.value) == float("inf"))


@dataclass(frozen=True, eq=False)
class UnaryOperatorNode(ExpressionNode):
    operand: ExpressionNode

    def __post_init__(self) -> None:
        object.__setattr__(self, "instances", self.operand.instances)


@dataclass(frozen=True, eq=False)
class PortFieldAggregatorNode(UnaryOperatorNode):
    aggregator: str

    def __post_init__(self) -> None:
        valid_names = [
            cls.__name__
            for _, cls in inspect.getmembers(
                andromede.expression.port_operator, inspect.isclass
            )
            if issubclass(cls, andromede.expression.port_operator.PortAggregator)
        ]
        if self.aggregator not in valid_names:
            raise NotImplementedError(
                f"{self.aggregator} is not a valid port aggregator, valid port aggregators are {valid_names}"
            )


@dataclass(frozen=True, eq=False)
class NegationNode(UnaryOperatorNode):
    pass


@dataclass(frozen=True, eq=False)
class BinaryOperatorNode(ExpressionNode):
    left: ExpressionNode
    right: ExpressionNode

    def __post_init__(self) -> None:
        binary_operator_post_init(self, "apply binary operation with")


def binary_operator_post_init(node: BinaryOperatorNode, operation: str) -> None:
    if node.left.instances != node.right.instances:
        raise ValueError(
            f"Cannot {operation} {node.left} and {node.right} as they do not have the same number of instances."
        )
    else:
        object.__setattr__(node, "instances", node.left.instances)


class Comparator(enum.Enum):
    LESS_THAN = "LESS_THAN"
    EQUAL = "EQUAL"
    GREATER_THAN = "GREATER_THAN"


@dataclass(frozen=True, eq=False)
class ComparisonNode(BinaryOperatorNode):
    comparator: Comparator

    def __post_init__(self) -> None:
        binary_operator_post_init(self, "compare")


@dataclass(frozen=True, eq=False)
class AdditionNode(BinaryOperatorNode):
    def __post_init__(self) -> None:
        binary_operator_post_init(self, "add")


@dataclass(frozen=True, eq=False)
class SubstractionNode(BinaryOperatorNode):
    def __post_init__(self) -> None:
        binary_operator_post_init(self, "substract")


@dataclass(frozen=True, eq=False)
class MultiplicationNode(BinaryOperatorNode):
    def __post_init__(self) -> None:
        binary_operator_post_init(self, "multiply")


@dataclass(frozen=True, eq=False)
class DivisionNode(BinaryOperatorNode):
    def __post_init__(self) -> None:
        binary_operator_post_init(self, "divide")


@dataclass(frozen=True, eq=False)
class ExpressionRange:
    start: ExpressionNode
    stop: ExpressionNode
    step: Optional[ExpressionNode] = None

    def __post_init__(self) -> None:
        for attribute in self.__dict__:
            value = getattr(self, attribute)
            object.__setattr__(
                self, attribute, _wrap_in_node(value) if value is not None else value
            )


IntOrExpr = Union[int, ExpressionNode]


def expression_range(
    start: IntOrExpr, stop: IntOrExpr, step: Optional[IntOrExpr] = None
) -> ExpressionRange:
    return ExpressionRange(
        start=_wrap_in_node(start),
        stop=_wrap_in_node(stop),
        step=None if step is None else _wrap_in_node(step),
    )


class InstancesTimeIndex:
    """
    Defines a set of time indices on which a time operator operates.

    In particular, it defines time indices created by the shift operator.

    The actual indices can either be defined as a time range defined by
    2 expression, or as a list of expressions.
    """

    expressions: Union[List[ExpressionNode], ExpressionRange]

    def __init__(
        self,
        expressions: Union[int, ExpressionNode, List[ExpressionNode], ExpressionRange],
    ) -> None:
        if not isinstance(expressions, (int, ExpressionNode, list, ExpressionRange)):
            raise TypeError(
                f"{expressions} must be of type among {{int, ExpressionNode, List[ExpressionNode], ExpressionRange}}"
            )
        if isinstance(expressions, list) and not all(
            isinstance(x, ExpressionNode) for x in expressions
        ):
            raise TypeError(
                f"All elements of {expressions} must be of type ExpressionNode"
            )

        if isinstance(expressions, (int, ExpressionNode)):
            self.expressions = [_wrap_in_node(expressions)]
        else:
            self.expressions = expressions

    def is_simple(self) -> bool:
        if isinstance(self.expressions, list):
            return len(self.expressions) == 1
        else:
            # TODO: We could also check that if a range only includes literal nodes, compute the length of the range, if it's one return True. This is more complicated, I do not know if we want to do this
            return False


@dataclass(frozen=True, eq=False)
class TimeOperatorNode(UnaryOperatorNode):
    name: str
    instances_index: InstancesTimeIndex

    def __post_init__(self) -> None:
        valid_names = [
            cls.__name__
            for _, cls in inspect.getmembers(
                andromede.expression.time_operator, inspect.isclass
            )
            if issubclass(cls, andromede.expression.time_operator.TimeOperator)
        ]
        if self.name not in valid_names:
            raise ValueError(
                f"{self.name} is not a valid time aggregator, valid time aggregators are {valid_names}"
            )
        if self.operand.instances == Instances.SIMPLE:
            if self.instances_index.is_simple():
                object.__setattr__(self, "instances", Instances.SIMPLE)
            else:
                object.__setattr__(self, "instances", Instances.MULTIPLE)
        else:
            raise ValueError(
                "Cannot apply time operator on an expression that already represents multiple instances"
            )


@dataclass(frozen=True, eq=False)
class TimeAggregatorNode(UnaryOperatorNode):
    name: str
    stay_roll: bool

    def __post_init__(self) -> None:
        valid_names = [
            cls.__name__
            for _, cls in inspect.getmembers(
                andromede.expression.time_operator, inspect.isclass
            )
            if issubclass(cls, andromede.expression.time_operator.TimeAggregator)
        ]
        if self.name not in valid_names:
            raise ValueError(
                f"{self.name} is not a valid time aggregator, valid time aggregators are {valid_names}"
            )
        object.__setattr__(self, "instances", Instances.SIMPLE)


@dataclass(frozen=True, eq=False)
class ScenarioOperatorNode(UnaryOperatorNode):
    name: str

    def __post_init__(self) -> None:
        valid_names = [
            cls.__name__
            for _, cls in inspect.getmembers(
                andromede.expression.scenario_operator, inspect.isclass
            )
            if issubclass(cls, andromede.expression.scenario_operator.ScenarioOperator)
        ]
        if self.name not in valid_names:
            raise ValueError(
                f"{self.name} is not a valid scenario operator, valid scenario operators are {valid_names}"
            )
        object.__setattr__(self, "instances", Instances.SIMPLE)


def sum_expressions(expressions: Sequence[ExpressionNode]) -> ExpressionNode:
    if len(expressions) == 0:
        return LiteralNode(0)
    if len(expressions) == 1:
        return expressions[0]
    return expressions[0] + sum_expressions(expressions[1:])
