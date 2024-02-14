# Generated from /home/leclercsyl/sources/antares/andromede-modeling-prototype/grammar/Expr.g4 by ANTLR 4.13.1
# encoding: utf-8
import sys
from io import StringIO

from antlr4 import *

if sys.version_info[1] > 5:
    from typing import TextIO
else:
    from typing.io import TextIO


def serializedATN():
    return [
        4,
        1,
        14,
        46,
        2,
        0,
        7,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        3,
        0,
        15,
        8,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        1,
        0,
        5,
        0,
        41,
        8,
        0,
        10,
        0,
        12,
        0,
        44,
        9,
        0,
        1,
        0,
        0,
        1,
        0,
        1,
        0,
        0,
        0,
        56,
        0,
        14,
        1,
        0,
        0,
        0,
        2,
        3,
        6,
        0,
        -1,
        0,
        3,
        4,
        5,
        4,
        0,
        0,
        4,
        15,
        3,
        0,
        0,
        9,
        5,
        15,
        5,
        12,
        0,
        0,
        6,
        7,
        5,
        12,
        0,
        0,
        7,
        8,
        5,
        9,
        0,
        0,
        8,
        15,
        5,
        12,
        0,
        0,
        9,
        15,
        5,
        11,
        0,
        0,
        10,
        11,
        5,
        10,
        0,
        0,
        11,
        12,
        3,
        0,
        0,
        0,
        12,
        13,
        5,
        8,
        0,
        0,
        13,
        15,
        1,
        0,
        0,
        0,
        14,
        2,
        1,
        0,
        0,
        0,
        14,
        5,
        1,
        0,
        0,
        0,
        14,
        6,
        1,
        0,
        0,
        0,
        14,
        9,
        1,
        0,
        0,
        0,
        14,
        10,
        1,
        0,
        0,
        0,
        15,
        42,
        1,
        0,
        0,
        0,
        16,
        17,
        10,
        13,
        0,
        0,
        17,
        18,
        5,
        1,
        0,
        0,
        18,
        41,
        3,
        0,
        0,
        14,
        19,
        20,
        10,
        12,
        0,
        0,
        20,
        21,
        5,
        2,
        0,
        0,
        21,
        41,
        3,
        0,
        0,
        13,
        22,
        23,
        10,
        11,
        0,
        0,
        23,
        24,
        5,
        3,
        0,
        0,
        24,
        41,
        3,
        0,
        0,
        12,
        25,
        26,
        10,
        10,
        0,
        0,
        26,
        27,
        5,
        4,
        0,
        0,
        27,
        41,
        3,
        0,
        0,
        11,
        28,
        29,
        10,
        8,
        0,
        0,
        29,
        30,
        5,
        13,
        0,
        0,
        30,
        41,
        3,
        0,
        0,
        9,
        31,
        32,
        10,
        7,
        0,
        0,
        32,
        41,
        5,
        5,
        0,
        0,
        33,
        34,
        10,
        6,
        0,
        0,
        34,
        41,
        5,
        6,
        0,
        0,
        35,
        36,
        10,
        5,
        0,
        0,
        36,
        37,
        5,
        7,
        0,
        0,
        37,
        38,
        3,
        0,
        0,
        0,
        38,
        39,
        5,
        8,
        0,
        0,
        39,
        41,
        1,
        0,
        0,
        0,
        40,
        16,
        1,
        0,
        0,
        0,
        40,
        19,
        1,
        0,
        0,
        0,
        40,
        22,
        1,
        0,
        0,
        0,
        40,
        25,
        1,
        0,
        0,
        0,
        40,
        28,
        1,
        0,
        0,
        0,
        40,
        31,
        1,
        0,
        0,
        0,
        40,
        33,
        1,
        0,
        0,
        0,
        40,
        35,
        1,
        0,
        0,
        0,
        41,
        44,
        1,
        0,
        0,
        0,
        42,
        40,
        1,
        0,
        0,
        0,
        42,
        43,
        1,
        0,
        0,
        0,
        43,
        1,
        1,
        0,
        0,
        0,
        44,
        42,
        1,
        0,
        0,
        0,
        3,
        14,
        40,
        42,
    ]


class ExprParser(Parser):
    grammarFileName = "Expr.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [DFA(ds, i) for i, ds in enumerate(atn.decisionToState)]

    sharedContextCache = PredictionContextCache()

    literalNames = [
        "<INVALID>",
        "'*'",
        "'/'",
        "'+'",
        "'-'",
        "'.sum()'",
        "'.sum_connections()'",
        "'.shift('",
        "')'",
        "'.'",
        "'('",
    ]

    symbolicNames = [
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "NUMBER",
        "IDENTIFIER",
        "COMPARISON",
        "WS",
    ]

    RULE_expr = 0

    ruleNames = ["expr"]

    EOF = Token.EOF
    T__0 = 1
    T__1 = 2
    T__2 = 3
    T__3 = 4
    T__4 = 5
    T__5 = 6
    T__6 = 7
    T__7 = 8
    T__8 = 9
    T__9 = 10
    NUMBER = 11
    IDENTIFIER = 12
    COMPARISON = 13
    WS = 14

    def __init__(self, input: TokenStream, output: TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.1")
        self._interp = ParserATNSimulator(
            self, self.atn, self.decisionsToDFA, self.sharedContextCache
        )
        self._predicates = None

    class ExprContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return ExprParser.RULE_expr

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class IdentifierContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IDENTIFIER(self):
            return self.getToken(ExprParser.IDENTIFIER, 0)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitIdentifier"):
                return visitor.visitIdentifier(self)
            else:
                return visitor.visitChildren(self)

    class NegationContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext, 0)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitNegation"):
                return visitor.visitNegation(self)
            else:
                return visitor.visitChildren(self)

    class ExpressionContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext, 0)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitExpression"):
                return visitor.visitExpression(self)
            else:
                return visitor.visitChildren(self)

    class ComparisonContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext, i)

        def COMPARISON(self):
            return self.getToken(ExprParser.COMPARISON, 0)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitComparison"):
                return visitor.visitComparison(self)
            else:
                return visitor.visitChildren(self)

    class SubtractionContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext, i)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitSubtraction"):
                return visitor.visitSubtraction(self)
            else:
                return visitor.visitChildren(self)

    class SumContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext, 0)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitSum"):
                return visitor.visitSum(self)
            else:
                return visitor.visitChildren(self)

    class PortFieldContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IDENTIFIER(self, i: int = None):
            if i is None:
                return self.getTokens(ExprParser.IDENTIFIER)
            else:
                return self.getToken(ExprParser.IDENTIFIER, i)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitPortField"):
                return visitor.visitPortField(self)
            else:
                return visitor.visitChildren(self)

    class DivisionContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext, i)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitDivision"):
                return visitor.visitDivision(self)
            else:
                return visitor.visitChildren(self)

    class NumberContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NUMBER(self):
            return self.getToken(ExprParser.NUMBER, 0)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitNumber"):
                return visitor.visitNumber(self)
            else:
                return visitor.visitChildren(self)

    class SumConnectionsContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext, 0)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitSumConnections"):
                return visitor.visitSumConnections(self)
            else:
                return visitor.visitChildren(self)

    class TimeShiftContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext, i)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitTimeShift"):
                return visitor.visitTimeShift(self)
            else:
                return visitor.visitChildren(self)

    class MultiplicationContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext, i)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitMultiplication"):
                return visitor.visitMultiplication(self)
            else:
                return visitor.visitChildren(self)

    class AdditionContext(ExprContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext, i)

        def accept(self, visitor: ParseTreeVisitor):
            if hasattr(visitor, "visitAddition"):
                return visitor.visitAddition(self)
            else:
                return visitor.visitChildren(self)

    def expr(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = ExprParser.ExprContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 0
        self.enterRecursionRule(localctx, 0, self.RULE_expr, _p)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 14
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 0, self._ctx)
            if la_ == 1:
                localctx = ExprParser.NegationContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 3
                self.match(ExprParser.T__3)
                self.state = 4
                self.expr(9)
                pass

            elif la_ == 2:
                localctx = ExprParser.IdentifierContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 5
                self.match(ExprParser.IDENTIFIER)
                pass

            elif la_ == 3:
                localctx = ExprParser.PortFieldContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 6
                self.match(ExprParser.IDENTIFIER)
                self.state = 7
                self.match(ExprParser.T__8)
                self.state = 8
                self.match(ExprParser.IDENTIFIER)
                pass

            elif la_ == 4:
                localctx = ExprParser.NumberContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 9
                self.match(ExprParser.NUMBER)
                pass

            elif la_ == 5:
                localctx = ExprParser.ExpressionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 10
                self.match(ExprParser.T__9)
                self.state = 11
                self.expr(0)
                self.state = 12
                self.match(ExprParser.T__7)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 42
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 2, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 40
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 1, self._ctx)
                    if la_ == 1:
                        localctx = ExprParser.MultiplicationContext(
                            self, ExprParser.ExprContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_expr
                        )
                        self.state = 16
                        if not self.precpred(self._ctx, 13):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 13)"
                            )
                        self.state = 17
                        self.match(ExprParser.T__0)
                        self.state = 18
                        self.expr(14)
                        pass

                    elif la_ == 2:
                        localctx = ExprParser.DivisionContext(
                            self, ExprParser.ExprContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_expr
                        )
                        self.state = 19
                        if not self.precpred(self._ctx, 12):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 12)"
                            )
                        self.state = 20
                        self.match(ExprParser.T__1)
                        self.state = 21
                        self.expr(13)
                        pass

                    elif la_ == 3:
                        localctx = ExprParser.AdditionContext(
                            self, ExprParser.ExprContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_expr
                        )
                        self.state = 22
                        if not self.precpred(self._ctx, 11):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 11)"
                            )
                        self.state = 23
                        self.match(ExprParser.T__2)
                        self.state = 24
                        self.expr(12)
                        pass

                    elif la_ == 4:
                        localctx = ExprParser.SubtractionContext(
                            self, ExprParser.ExprContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_expr
                        )
                        self.state = 25
                        if not self.precpred(self._ctx, 10):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 10)"
                            )
                        self.state = 26
                        self.match(ExprParser.T__3)
                        self.state = 27
                        self.expr(11)
                        pass

                    elif la_ == 5:
                        localctx = ExprParser.ComparisonContext(
                            self, ExprParser.ExprContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_expr
                        )
                        self.state = 28
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 29
                        self.match(ExprParser.COMPARISON)
                        self.state = 30
                        self.expr(9)
                        pass

                    elif la_ == 6:
                        localctx = ExprParser.SumContext(
                            self, ExprParser.ExprContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_expr
                        )
                        self.state = 31
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 32
                        self.match(ExprParser.T__4)
                        pass

                    elif la_ == 7:
                        localctx = ExprParser.SumConnectionsContext(
                            self, ExprParser.ExprContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_expr
                        )
                        self.state = 33
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 34
                        self.match(ExprParser.T__5)
                        pass

                    elif la_ == 8:
                        localctx = ExprParser.TimeShiftContext(
                            self, ExprParser.ExprContext(self, _parentctx, _parentState)
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_expr
                        )
                        self.state = 35
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 36
                        self.match(ExprParser.T__6)
                        self.state = 37
                        self.expr(0)
                        self.state = 38
                        self.match(ExprParser.T__7)
                        pass

                self.state = 44
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 2, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    def sempred(self, localctx: RuleContext, ruleIndex: int, predIndex: int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[0] = self.expr_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def expr_sempred(self, localctx: ExprContext, predIndex: int):
        if predIndex == 0:
            return self.precpred(self._ctx, 13)

        if predIndex == 1:
            return self.precpred(self._ctx, 12)

        if predIndex == 2:
            return self.precpred(self._ctx, 11)

        if predIndex == 3:
            return self.precpred(self._ctx, 10)

        if predIndex == 4:
            return self.precpred(self._ctx, 8)

        if predIndex == 5:
            return self.precpred(self._ctx, 7)

        if predIndex == 6:
            return self.precpred(self._ctx, 6)

        if predIndex == 7:
            return self.precpred(self._ctx, 5)
