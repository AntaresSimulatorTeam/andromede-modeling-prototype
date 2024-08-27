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
from antlr4.error.ErrorStrategy import BailErrorStrategy

from andromede.expression.equality import expressions_equal
from andromede.expression.expression import (
    Comparator,
    ComparisonNode,
    ExpressionRange,
    literal,
    param,
)
from andromede.expression.linear_expression import (
    LinearExpression,
    port_field,
    var,
    wrap_in_linear_expr,
)
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

    def visitFullexpr(self, ctx: ExprParser.FullexprContext) -> LinearExpression:
        return ctx.expr().accept(self)  # type: ignore

    # Visit a parse tree produced by ExprParser#number.
    def visitNumber(self, ctx: ExprParser.NumberContext) -> LinearExpression:
        return literal(float(ctx.NUMBER().getText()))  # type: ignore

    # Visit a parse tree produced by ExprParser#identifier.
    def visitIdentifier(self, ctx: ExprParser.IdentifierContext) -> LinearExpression:
        return self._convert_identifier(ctx.IDENTIFIER().getText())  # type: ignore

    # Visit a parse tree produced by ExprParser#division.
    def visitMuldiv(self, ctx: ExprParser.MuldivContext) -> LinearExpression:
        left = ctx.expr(0).accept(self)  # type: ignore
        right = ctx.expr(1).accept(self)  # type: ignore
        op = ctx.op.text  # type: ignore
        if op == "*":
            return left * right
        elif op == "/":
            return left / right
        raise ValueError(f"Invalid operator {op}")

    # Visit a parse tree produced by ExprParser#subtraction.
    def visitAddsub(self, ctx: ExprParser.AddsubContext) -> LinearExpression:
        left = ctx.expr(0).accept(self)  # type: ignore
        right = ctx.expr(1).accept(self)  # type: ignore
        op = ctx.op.text  # type: ignore
        if op == "+":
            return left + right
        elif op == "-":
            return left - right
        raise ValueError(f"Invalid operator {op}")

    # Visit a parse tree produced by ExprParser#negation.
    def visitNegation(self, ctx: ExprParser.NegationContext) -> LinearExpression:
        return -ctx.expr().accept(self)  # type: ignore

    # Visit a parse tree produced by ExprParser#expression.
    def visitExpression(self, ctx: ExprParser.ExpressionContext) -> LinearExpression:
        return ctx.expr().accept(self)  # type: ignore

    # Visit a parse tree produced by ExprParser#unsignedAtom.
    def visitUnsignedAtom(
        self, ctx: ExprParser.UnsignedAtomContext
    ) -> LinearExpression:
        return ctx.atom().accept(self)  # type: ignore

    def _convert_identifier(self, identifier: str) -> LinearExpression:
        if self.identifiers.is_variable(identifier):
            return var(identifier)
        elif self.identifiers.is_parameter(identifier):
            return param(identifier)
        raise ValueError(f"{identifier} is not a valid variable or parameter name.")

    # Visit a parse tree produced by ExprParser#portField.
    def visitPortField(self, ctx: ExprParser.PortFieldContext) -> LinearExpression:
        return port_field(
            port_name=ctx.IDENTIFIER(0).getText(),  # type: ignore
            field_name=ctx.IDENTIFIER(1).getText(),  # type: ignore
        )

    # Visit a parse tree produced by ExprParser#comparison.
    def visitComparison(self, ctx: ExprParser.ComparisonContext) -> LinearExpression:
        op = ctx.COMPARISON().getText()  # type: ignore
        exp1 = ctx.expr(0).accept(self)  # type: ignore
        exp2 = ctx.expr(1).accept(self)  # type: ignore
        comp = {
            "=": LinearExpression.__eq__,
            "<=": LinearExpression.__le__,
            ">=": LinearExpression.__ge__,
        }[op]
        return comp(exp1, exp2)

    # Visit a parse tree produced by ExprParser#timeShift.
    def visitTimeIndex(self, ctx: ExprParser.TimeIndexContext) -> LinearExpression:
        shifted_expr = self._convert_identifier(ctx.IDENTIFIER().getText())  # type: ignore
        time_shifts = [e.accept(self) for e in ctx.expr()]  # type: ignore
        return shifted_expr.eval(time_shifts)

    # Visit a parse tree produced by ExprParser#rangeTimeShift.
    def visitTimeRange(self, ctx: ExprParser.TimeRangeContext) -> LinearExpression:
        shifted_expr = self._convert_identifier(ctx.IDENTIFIER().getText())  # type: ignore
        expressions = [e.accept(self) for e in ctx.expr()]  # type: ignore
        # TODO: Is there a visitSum somewhere that is not needed ? Are the correct symbol parsed (sum(...) ?) ?
        return shifted_expr.sum(eval=ExpressionRange(expressions[0], expressions[1]))

    def visitTimeShift(self, ctx: ExprParser.TimeShiftContext) -> LinearExpression:
        shifted_expr = self._convert_identifier(ctx.IDENTIFIER().getText())  # type: ignore
        time_shifts = [s.accept(self) for s in ctx.shift()]  # type: ignore
        # specifics for x[t] ...
        if len(time_shifts) == 1 and expressions_equal(time_shifts[0], literal(0)):
            return shifted_expr
        return shifted_expr.sum(shift=time_shifts)

    def visitTimeShiftRange(
        self, ctx: ExprParser.TimeShiftRangeContext
    ) -> LinearExpression:
        shifted_expr = self._convert_identifier(ctx.IDENTIFIER().getText())  # type: ignore
        shift1 = ctx.shift1.accept(self)  # type: ignore
        shift2 = ctx.shift2.accept(self)  # type: ignore
        return shifted_expr.sum(shift=ExpressionRange(shift1, shift2))

    # Visit a parse tree produced by ExprParser#function.
    def visitFunction(self, ctx: ExprParser.FunctionContext) -> LinearExpression:
        function_name: str = ctx.IDENTIFIER().getText()  # type: ignore
        operand: LinearExpression = ctx.expr().accept(self)  # type: ignore
        fn = _FUNCTIONS.get(function_name, None)
        if fn is None:
            raise ValueError(f"Encountered invalid function name {function_name}")
        return fn(operand)

    # Visit a parse tree produced by ExprParser#shift.
    def visitShift(self, ctx: ExprParser.ShiftContext) -> LinearExpression:
        if ctx.shift_expr() is None:  # type: ignore
            return literal(0)
        shift = ctx.shift_expr().accept(self)  # type: ignore
        return shift

    # Visit a parse tree produced by ExprParser#shiftAddsub.
    def visitShiftAddsub(self, ctx: ExprParser.ShiftAddsubContext) -> LinearExpression:
        left = ctx.shift_expr().accept(self)  # type: ignore
        right = ctx.right_expr().accept(self)  # type: ignore
        op = ctx.op.text  # type: ignore
        if op == "+":
            return left + right
        elif op == "-":
            return left - right
        raise ValueError(f"Invalid operator {op}")

    # Visit a parse tree produced by ExprParser#shiftMuldiv.
    def visitShiftMuldiv(self, ctx: ExprParser.ShiftMuldivContext) -> LinearExpression:
        left = ctx.shift_expr().accept(self)  # type: ignore
        right = ctx.right_expr().accept(self)  # type: ignore
        op = ctx.op.text  # type: ignore
        if op == "*":
            return left * right
        elif op == "/":
            return left / right
        raise ValueError(f"Invalid operator {op}")

    # Visit a parse tree produced by ExprParser#signedExpression.
    def visitSignedExpression(
        self, ctx: ExprParser.SignedExpressionContext
    ) -> LinearExpression:
        if ctx.op.text == "-":  # type: ignore
            return -ctx.expr().accept(self)  # type: ignore
        else:
            return ctx.expr().accept(self)  # type: ignore

    # Visit a parse tree produced by ExprParser#signedAtom.
    def visitSignedAtom(self, ctx: ExprParser.SignedAtomContext) -> LinearExpression:
        if ctx.op.text == "-":  # type: ignore
            return -ctx.atom().accept(self)  # type: ignore
        else:
            return ctx.atom().accept(self)  # type: ignore

    # Visit a parse tree produced by ExprParser#rightExpression.
    def visitRightExpression(
        self, ctx: ExprParser.RightExpressionContext
    ) -> LinearExpression:
        return ctx.expr().accept(self)  # type: ignore

    # Visit a parse tree produced by ExprParser#rightMuldiv.
    def visitRightMuldiv(self, ctx: ExprParser.RightMuldivContext) -> LinearExpression:
        left = ctx.right_expr(0).accept(self)  # type: ignore
        right = ctx.right_expr(1).accept(self)  # type: ignore
        op = ctx.op.text  # type: ignore
        if op == "*":
            return left * right
        elif op == "/":
            return left / right
        raise ValueError(f"Invalid operator {op}")

    # Visit a parse tree produced by ExprParser#rightAtom.
    def visitRightAtom(self, ctx: ExprParser.RightAtomContext) -> LinearExpression:
        return ctx.atom().accept(self)  # type: ignore


_FUNCTIONS = {
    "sum": LinearExpression.sum,
    "sum_connections": LinearExpression.sum_connections,
    "expec": LinearExpression.expec,
}


class AntaresParseException(Exception):
    pass


def parse_expression(
    expression: str, identifiers: ModelIdentifiers
) -> LinearExpression:
    """
    Parses a string expression to create the corresponding AST representation.
    """
    try:
        input = InputStream(expression)
        lexer = ExprLexer(input)
        stream = CommonTokenStream(lexer)
        parser = ExprParser(stream)
        parser._errHandler = BailErrorStrategy()

        return ExpressionNodeBuilderVisitor(identifiers).visit(parser.fullexpr())  # type: ignore

    except ValueError as e:
        raise AntaresParseException(f"An error occurred during parsing: {e}") from e
    except Exception as e:
        raise AntaresParseException(
            f"An error occurred during parsing: {type(e).__name__}"
        ) from e
