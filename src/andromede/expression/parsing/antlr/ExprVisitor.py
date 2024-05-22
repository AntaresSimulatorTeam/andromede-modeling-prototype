# Generated from Expr.g4 by ANTLR 4.13.1
from antlr4 import *

if "." in __name__:
    from .ExprParser import ExprParser
else:
    from ExprParser import ExprParser

# This class defines a complete generic visitor for a parse tree produced by ExprParser.


class ExprVisitor(ParseTreeVisitor):
    # Visit a parse tree produced by ExprParser#fullexpr.
    def visitFullexpr(self, ctx: ExprParser.FullexprContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#shift.
    def visitShift(self, ctx: ExprParser.ShiftContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#identifier.
    def visitIdentifier(self, ctx: ExprParser.IdentifierContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#negation.
    def visitNegation(self, ctx: ExprParser.NegationContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#expression.
    def visitExpression(self, ctx: ExprParser.ExpressionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#comparison.
    def visitComparison(self, ctx: ExprParser.ComparisonContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#addsub.
    def visitAddsub(self, ctx: ExprParser.AddsubContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#portField.
    def visitPortField(self, ctx: ExprParser.PortFieldContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#muldiv.
    def visitMuldiv(self, ctx: ExprParser.MuldivContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#signedIdentifier.
    def visitSignedIdentifier(self, ctx: ExprParser.SignedIdentifierContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#number.
    def visitNumber(self, ctx: ExprParser.NumberContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#timeIndex.
    def visitTimeIndex(self, ctx: ExprParser.TimeIndexContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#timeShift.
    def visitTimeShift(self, ctx: ExprParser.TimeShiftContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#signedNumber.
    def visitSignedNumber(self, ctx: ExprParser.SignedNumberContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#function.
    def visitFunction(self, ctx: ExprParser.FunctionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#timeShiftRange.
    def visitTimeShiftRange(self, ctx: ExprParser.TimeShiftRangeContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#timeRange.
    def visitTimeRange(self, ctx: ExprParser.TimeRangeContext):
        return self.visitChildren(ctx)


del ExprParser
