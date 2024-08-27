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
Defines abstract base class for visitors of expressions.
"""
from abc import ABC, abstractmethod
from typing import Generic, Protocol, TypeVar

from .expression import (
    AdditionNode,
    ComparisonNode,
    ComponentParameterNode,
    DivisionNode,
    ExpressionNode,
    LiteralNode,
    MultiplicationNode,
    NegationNode,
    ParameterNode,
    PortFieldAggregatorNode,
    PortFieldNode,
    ScenarioOperatorNode,
    SubstractionNode,
    TimeAggregatorNode,
    TimeOperatorNode,
)

T = TypeVar("T")


class ExpressionVisitor(ABC, Generic[T]):
    """
    Abstract base class for visitors of expressions.

    Visitor can be implemented to carry out arbitrary kind
    of analysis over an expression, such as evaluation,
    manipulation ...
    """

    @abstractmethod
    def literal(self, node: LiteralNode) -> T:
        ...

    @abstractmethod
    def negation(self, node: NegationNode) -> T:
        ...

    @abstractmethod
    def addition(self, node: AdditionNode) -> T:
        ...

    @abstractmethod
    def substraction(self, node: SubstractionNode) -> T:
        ...

    @abstractmethod
    def multiplication(self, node: MultiplicationNode) -> T:
        ...

    @abstractmethod
    def division(self, node: DivisionNode) -> T:
        ...

    @abstractmethod
    def comparison(self, node: ComparisonNode) -> T:
        ...

    @abstractmethod
    def parameter(self, node: ParameterNode) -> T:
        ...

    @abstractmethod
    def comp_parameter(self, node: ComponentParameterNode) -> T:
        ...

    @abstractmethod
    def time_operator(self, node: TimeOperatorNode) -> T:
        ...

    @abstractmethod
    def time_aggregator(self, node: TimeAggregatorNode) -> T:
        ...

    @abstractmethod
    def scenario_operator(self, node: ScenarioOperatorNode) -> T:
        ...

    @abstractmethod
    def port_field(self, node: PortFieldNode) -> T:
        ...

    @abstractmethod
    def port_field_aggregator(self, node: PortFieldAggregatorNode) -> T:
        ...


def visit(root: ExpressionNode, visitor: ExpressionVisitor[T]) -> T:
    """
    Utility method to dispatch calls to the right method of a visitor.
    """
    if isinstance(root, LiteralNode):
        return visitor.literal(root)
    elif isinstance(root, NegationNode):
        return visitor.negation(root)
    elif isinstance(root, ParameterNode):
        return visitor.parameter(root)
    elif isinstance(root, ComponentParameterNode):
        return visitor.comp_parameter(root)
    elif isinstance(root, AdditionNode):
        return visitor.addition(root)
    elif isinstance(root, MultiplicationNode):
        return visitor.multiplication(root)
    elif isinstance(root, DivisionNode):
        return visitor.division(root)
    elif isinstance(root, SubstractionNode):
        return visitor.substraction(root)
    elif isinstance(root, ComparisonNode):
        return visitor.comparison(root)
    elif isinstance(root, TimeOperatorNode):
        return visitor.time_operator(root)
    elif isinstance(root, TimeAggregatorNode):
        return visitor.time_aggregator(root)
    elif isinstance(root, ScenarioOperatorNode):
        return visitor.scenario_operator(root)
    elif isinstance(root, PortFieldNode):
        return visitor.port_field(root)
    elif isinstance(root, PortFieldAggregatorNode):
        return visitor.port_field_aggregator(root)
    raise ValueError(f"Unknown expression node type {root.__class__}")


class SupportsOperations(Protocol[T]):
    """
    Defines a type which implements math operations +, -, *, /
    """

    @abstractmethod
    def __add__(self, other: T) -> T:
        pass

    @abstractmethod
    def __neg__(self) -> T:
        pass

    @abstractmethod
    def __sub__(self, other: T) -> T:
        pass

    @abstractmethod
    def __mul__(self, other: T) -> T:
        pass

    @abstractmethod
    def __truediv__(self, other: T) -> T:
        pass


T_op = TypeVar("T_op", bound=SupportsOperations)


class ExpressionVisitorOperations(ExpressionVisitor[T_op], ABC):
    """
    Provides default implementations of math operations
    based on (+, -, /, *) operations of type T.
    """

    def negation(self, node: NegationNode) -> T_op:
        return -visit(node.operand, self)

    def addition(self, node: AdditionNode) -> T_op:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return left_value + right_value

    def substraction(self, node: SubstractionNode) -> T_op:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return left_value - right_value

    def multiplication(self, node: MultiplicationNode) -> T_op:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return left_value * right_value

    def division(self, node: DivisionNode) -> T_op:
        left_value = visit(node.left, self)
        right_value = visit(node.right, self)
        return left_value / right_value
