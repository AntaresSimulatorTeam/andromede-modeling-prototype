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
from typing import Set

import pytest
from antlr4 import CommonTokenStream, InputStream

from andromede.expression import (
    AdditionNode,
    Comparator,
    ComparisonNode,
    ExpressionNode,
    literal,
    param,
    print_expr,
    var,
)
from andromede.expression.equality import expressions_equal
from andromede.expression.expression import PortFieldNode, port_field
from andromede.expression.serde.ExprLexer import ExprLexer
from andromede.expression.serde.ExprParser import ExprParser
from andromede.expression.serde.ExprVisitor import ExprVisitor


@dataclass(frozen=True)
class ModelIdentifiers:
    """
    Allows to distinguish between parameters and variables.
    """

    variables: Set[str]
    parameters: Set[str]

    def is_variable(self, identifier: str):
        return identifier in self.variables

    def is_parameter(self, identifier: str):
        return identifier in self.parameters


@dataclass(frozen=True)
class ExpressionNodeBuilderVisitor(ExprVisitor):
    identifiers: ModelIdentifiers

    # Visit a parse tree produced by ExprParser#division.
    def visitDivision(self, ctx: ExprParser.DivisionContext) -> ExpressionNode:
        left = ctx.expr(0).accept(self)
        right = ctx.expr(1).accept(self)
        return left / right

    # Visit a parse tree produced by ExprParser#number.
    def visitNumber(self, ctx: ExprParser.NumberContext) -> ExpressionNode:
        return literal(float(ctx.getText()))

    # Visit a parse tree produced by ExprParser#negation.
    def visitNegation(self, ctx: ExprParser.NegationContext) -> ExpressionNode:
        return -ctx.expr().accept(self)

    # Visit a parse tree produced by ExprParser#expression.
    def visitExpression(self, ctx: ExprParser.ExpressionContext) -> ExpressionNode:
        return ctx.expr().accept(self)

    # Visit a parse tree produced by ExprParser#identifier.
    def visitIdentifier(self, ctx: ExprParser.IdentifierContext):
        identifier = ctx.IDENTIFIER().getText()
        if self.identifiers.is_variable(identifier):
            return var(identifier)
        elif self.identifiers.is_parameter(identifier):
            return param(identifier)
        raise ValueError(f"{identifier} is not a valid variable or parameter name.")

    # Visit a parse tree produced by ExprParser#subtraction.
    def visitSubtraction(self, ctx: ExprParser.SubtractionContext) -> ExpressionNode:
        left = ctx.expr(0).accept(self)
        right = ctx.expr(1).accept(self)
        return left - right

    # Visit a parse tree produced by ExprParser#multiplication.
    def visitMultiplication(
        self, ctx: ExprParser.MultiplicationContext
    ) -> ExpressionNode:
        left = ctx.expr(0).accept(self)
        right = ctx.expr(1).accept(self)
        return left * right

    # Visit a parse tree produced by ExprParser#addition.
    def visitAddition(self, ctx: ExprParser.AdditionContext) -> ExpressionNode:
        left = ctx.expr(0).accept(self)
        right = ctx.expr(1).accept(self)
        return left + right

    # Visit a parse tree produced by ExprParser#portField.
    def visitPortField(self, ctx: ExprParser.PortFieldContext):
        return PortFieldNode(
            port_name=ctx.IDENTIFIER(0).getText(),
            field_name=ctx.IDENTIFIER(1).getText(),
        )

    # Visit a parse tree produced by ExprParser#comparison.
    def visitComparison(self, ctx: ExprParser.ComparisonContext):
        op = ctx.COMPARISON().getText()
        exp1 = ctx.expr(0).accept(self)
        exp2 = ctx.expr(1).accept(self)
        comp = {
            "=": Comparator.EQUAL,
            "<=": Comparator.LESS_THAN,
            ">=": Comparator.GREATER_THAN,
        }.get(op)
        return ComparisonNode(exp1, exp2, comp)


def parse_expression(expression: str, identifiers: ModelIdentifiers) -> ExpressionNode:
    input = InputStream(expression)
    lexer = ExprLexer(input)
    stream = CommonTokenStream(lexer)
    parser = ExprParser(stream)
    return ExpressionNodeBuilderVisitor(identifiers).visit(parser.expr())


@pytest.mark.parametrize(
    "expression_str, expected",
    [
        (
            "1 + 2 * x = p",
            literal(1) + 2 * var("x") == param("p"),
        ),
        (
            "port.f <= 0",
            port_field("port", "f") <= 0,
        ),
    ],
)
def test_parsing_visitor(expression_str: str, expected: ExpressionNode):
    identifiers = ModelIdentifiers(variables={"x"}, parameters={"p"})

    expr = parse_expression(expression_str, identifiers)

    assert expressions_equal(expr, expected)
