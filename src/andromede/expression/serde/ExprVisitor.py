# Generated from /home/leclercsyl/sources/antares/andromede-modeling-prototype/grammar/Expr.g4 by ANTLR 4.13.1
from antlr4 import *

if "." in __name__:
    from .ExprParser import ExprParser
else:
    from ExprParser import ExprParser

# This class defines a complete generic visitor for a parse tree produced by ExprParser.


class ExprVisitor(ParseTreeVisitor):
    # Visit a parse tree produced by ExprParser#division.
    def visitDivision(self, ctx: ExprParser.DivisionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#identifier.
    def visitIdentifier(self, ctx: ExprParser.IdentifierContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#number.
    def visitNumber(self, ctx: ExprParser.NumberContext):
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

    # Visit a parse tree produced by ExprParser#subtraction.
    def visitSubtraction(self, ctx: ExprParser.SubtractionContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#multiplication.
    def visitMultiplication(self, ctx: ExprParser.MultiplicationContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#portField.
    def visitPortField(self, ctx: ExprParser.PortFieldContext):
        return self.visitChildren(ctx)

    # Visit a parse tree produced by ExprParser#addition.
    def visitAddition(self, ctx: ExprParser.AdditionContext):
        return self.visitChildren(ctx)


del ExprParser
