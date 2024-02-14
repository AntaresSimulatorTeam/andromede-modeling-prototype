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

from antlr4 import CommonTokenStream, InputStream

from andromede.expression import ExpressionNode, literal, param, var
from andromede.expression.expression import Comparator, ComparisonNode, PortFieldNode
from andromede.expression.parsing.antlr.ExprLexer import ExprLexer
from andromede.expression.parsing.antlr.ExprParser import ExprParser
from andromede.expression.parsing.antlr.ExprVisitor import ExprVisitor


@dataclass(frozen=True)
class ModelIdentifiers:
    """
    Allows to distinguish between parameters and variables.
    """

    variables: Set[str]
    parameters: Set[str]

    def is_variable(self, identifier: str) -> bool:
        return identifier in self.variables

    def is_parameter(self, identifier: str) -> bool:
        return identifier in self.parameters


@dataclass(frozen=True)
class ExpressionNodeBuilderVisitor(ExprVisitor):
    """
    Visits a tree created by ANTLR to create our AST representation.
    """

    identifiers: ModelIdentifiers

    # Visit a parse tree produced by ExprParser#division.
    def visitDivision(self, ctx: ExprParser.DivisionContext) -> ExpressionNode:
        left = ctx.expr(0).accept(self)  # type: ignore
        right = ctx.expr(1).accept(self)  # type: ignore
        return left / right

    # Visit a parse tree produced by ExprParser#number.
    def visitNumber(self, ctx: ExprParser.NumberContext) -> ExpressionNode:
        return literal(float(ctx.getText()))

    # Visit a parse tree produced by ExprParser#negation.
    def visitNegation(self, ctx: ExprParser.NegationContext) -> ExpressionNode:
        return -ctx.expr().accept(self)  # type: ignore

    # Visit a parse tree produced by ExprParser#expression.
    def visitExpression(self, ctx: ExprParser.ExpressionContext) -> ExpressionNode:
        return ctx.expr().accept(self)  # type: ignore

    # Visit a parse tree produced by ExprParser#identifier.
    def visitIdentifier(self, ctx: ExprParser.IdentifierContext) -> ExpressionNode:
        identifier = ctx.IDENTIFIER().getText()  # type: ignore
        if self.identifiers.is_variable(identifier):
            return var(identifier)
        elif self.identifiers.is_parameter(identifier):
            return param(identifier)
        raise ValueError(f"{identifier} is not a valid variable or parameter name.")

    # Visit a parse tree produced by ExprParser#subtraction.
    def visitSubtraction(self, ctx: ExprParser.SubtractionContext) -> ExpressionNode:
        left = ctx.expr(0).accept(self)  # type: ignore
        right = ctx.expr(1).accept(self)  # type: ignore
        return left - right

    # Visit a parse tree produced by ExprParser#multiplication.
    def visitMultiplication(
        self, ctx: ExprParser.MultiplicationContext
    ) -> ExpressionNode:
        left = ctx.expr(0).accept(self)  # type: ignore
        right = ctx.expr(1).accept(self)  # type: ignore
        return left * right

    # Visit a parse tree produced by ExprParser#addition.
    def visitAddition(self, ctx: ExprParser.AdditionContext) -> ExpressionNode:
        left = ctx.expr(0).accept(self)  # type: ignore
        right = ctx.expr(1).accept(self)  # type: ignore
        return left + right

    # Visit a parse tree produced by ExprParser#portField.
    def visitPortField(self, ctx: ExprParser.PortFieldContext) -> ExpressionNode:
        return PortFieldNode(
            port_name=ctx.IDENTIFIER(0).getText(),  # type: ignore
            field_name=ctx.IDENTIFIER(1).getText(),  # type: ignore
        )

    # Visit a parse tree produced by ExprParser#comparison.
    def visitComparison(self, ctx: ExprParser.ComparisonContext) -> ExpressionNode:
        op = ctx.COMPARISON().getText()  # type: ignore
        exp1 = ctx.expr(0).accept(self)  # type: ignore
        exp2 = ctx.expr(1).accept(self)  # type: ignore
        comp = {
            "=": Comparator.EQUAL,
            "<=": Comparator.LESS_THAN,
            ">=": Comparator.GREATER_THAN,
        }[op]
        return ComparisonNode(exp1, exp2, comp)

    # Visit a parse tree produced by ExprParser#sum.
    def visitSum(self, ctx: ExprParser.SumContext) -> ExpressionNode:
        return ctx.expr().accept(self).sum()  # type: ignore

    # Visit a parse tree produced by ExprParser#sumConnections.
    def visitSumConnections(
        self, ctx: ExprParser.SumConnectionsContext
    ) -> ExpressionNode:
        return ctx.expr().accept(self).sum_connections()  # type: ignore

    # Visit a parse tree produced by ExprParser#timeShift.
    def visitTimeShift(self, ctx: ExprParser.TimeShiftContext) -> ExpressionNode:
        shifted_expr = ctx.expr(0).accept(self)  # type: ignore
        time_expr = ctx.expr(1).accept(self)  # type: ignore
        return shifted_expr.shift(time_expr)


def parse_expression(expression: str, identifiers: ModelIdentifiers) -> ExpressionNode:
    """
    Parses a string expression to create the corresponding AST representation.
    """
    input = InputStream(expression)
    lexer = ExprLexer(input)
    stream = CommonTokenStream(lexer)
    parser = ExprParser(stream)
    return ExpressionNodeBuilderVisitor(identifiers).visit(parser.expr())
