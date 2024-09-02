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
import typing
from abc import ABC, abstractmethod
from typing import Generic, Protocol, TypeVar

from andromede.expression.expression import (
    AdditionNode,
    ComparisonNode,
    ComponentParameterNode,
    ComponentVariableNode,
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
    VariableNode,
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
    def variable(self, node: VariableNode) -> T:
        ...

    @abstractmethod
    def parameter(self, node: ParameterNode) -> T:
        ...

    @abstractmethod
    def comp_parameter(self, node: ComponentParameterNode) -> T:
        ...

    @abstractmethod
    def comp_variable(self, node: ComponentVariableNode) -> T:
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
    TYPES = {
        LiteralNode: "literal",
        NegationNode: "negation",
        VariableNode: "variable",
        ParameterNode: "parameter",
        ComponentParameterNode: "comp_parameter",
        ComponentVariableNode: "comp_variable",
        AdditionNode: "addition",
        MultiplicationNode: "multiplication",
        DivisionNode: "division",
        SubstractionNode: "substraction",
        ComparisonNode: "comparison",
        TimeOperatorNode: "time_operator",
        TimeAggregatorNode: "time_aggregator",
        ScenarioOperatorNode: "scenario_operator",
        PortFieldNode: "port_field",
        PortFieldAggregatorNode: "port_field_aggregator",
    }
    if type(root) in TYPES:
        return getattr(visitor, TYPES[type(root)])(root)
    else:
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
