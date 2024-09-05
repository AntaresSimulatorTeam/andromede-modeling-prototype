# Generated from Expr.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,17,129,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,1,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
        1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
        1,1,1,1,1,1,1,1,1,1,1,3,1,52,8,1,1,1,1,1,3,1,56,8,1,1,1,1,1,3,1,
        60,8,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,5,1,71,8,1,10,1,12,1,
        74,9,1,1,2,1,2,3,2,78,8,2,1,3,1,3,1,3,1,3,1,4,1,4,1,4,1,4,1,5,1,
        5,3,5,90,8,5,1,6,1,6,1,6,1,6,1,6,1,6,1,6,1,6,3,6,100,8,6,1,6,1,6,
        1,6,1,6,1,6,1,6,5,6,108,8,6,10,6,12,6,111,9,6,1,7,1,7,1,7,1,7,1,
        7,1,7,3,7,119,8,7,1,7,1,7,1,7,5,7,124,8,7,10,7,12,7,127,9,7,1,7,
        0,3,2,12,14,8,0,2,4,6,8,10,12,14,0,2,1,0,5,6,2,0,2,2,7,7,141,0,16,
        1,0,0,0,2,59,1,0,0,0,4,77,1,0,0,0,6,79,1,0,0,0,8,83,1,0,0,0,10,87,
        1,0,0,0,12,99,1,0,0,0,14,118,1,0,0,0,16,17,3,2,1,0,17,18,5,0,0,1,
        18,1,1,0,0,0,19,20,6,1,-1,0,20,60,3,4,2,0,21,22,5,14,0,0,22,23,5,
        1,0,0,23,60,5,14,0,0,24,25,5,2,0,0,25,60,3,2,1,9,26,27,5,3,0,0,27,
        28,3,2,1,0,28,29,5,4,0,0,29,60,1,0,0,0,30,31,5,14,0,0,31,32,5,3,
        0,0,32,33,3,2,1,0,33,34,5,4,0,0,34,60,1,0,0,0,35,36,5,14,0,0,36,
        37,5,8,0,0,37,38,3,10,5,0,38,39,5,9,0,0,39,60,1,0,0,0,40,41,5,14,
        0,0,41,42,5,8,0,0,42,43,3,2,1,0,43,44,5,9,0,0,44,60,1,0,0,0,45,46,
        5,16,0,0,46,55,5,3,0,0,47,52,3,2,1,0,48,52,3,10,5,0,49,52,3,6,3,
        0,50,52,3,8,4,0,51,47,1,0,0,0,51,48,1,0,0,0,51,49,1,0,0,0,51,50,
        1,0,0,0,52,53,1,0,0,0,53,54,5,10,0,0,54,56,1,0,0,0,55,51,1,0,0,0,
        55,56,1,0,0,0,56,57,1,0,0,0,57,58,5,14,0,0,58,60,5,4,0,0,59,19,1,
        0,0,0,59,21,1,0,0,0,59,24,1,0,0,0,59,26,1,0,0,0,59,30,1,0,0,0,59,
        35,1,0,0,0,59,40,1,0,0,0,59,45,1,0,0,0,60,72,1,0,0,0,61,62,10,7,
        0,0,62,63,7,0,0,0,63,71,3,2,1,8,64,65,10,6,0,0,65,66,7,1,0,0,66,
        71,3,2,1,7,67,68,10,5,0,0,68,69,5,15,0,0,69,71,3,2,1,6,70,61,1,0,
        0,0,70,64,1,0,0,0,70,67,1,0,0,0,71,74,1,0,0,0,72,70,1,0,0,0,72,73,
        1,0,0,0,73,3,1,0,0,0,74,72,1,0,0,0,75,78,5,12,0,0,76,78,5,14,0,0,
        77,75,1,0,0,0,77,76,1,0,0,0,78,5,1,0,0,0,79,80,3,10,5,0,80,81,5,
        11,0,0,81,82,3,10,5,0,82,7,1,0,0,0,83,84,3,2,1,0,84,85,5,11,0,0,
        85,86,3,2,1,0,86,9,1,0,0,0,87,89,5,13,0,0,88,90,3,12,6,0,89,88,1,
        0,0,0,89,90,1,0,0,0,90,11,1,0,0,0,91,92,6,6,-1,0,92,93,7,1,0,0,93,
        100,3,4,2,0,94,95,7,1,0,0,95,96,5,3,0,0,96,97,3,2,1,0,97,98,5,4,
        0,0,98,100,1,0,0,0,99,91,1,0,0,0,99,94,1,0,0,0,100,109,1,0,0,0,101,
        102,10,4,0,0,102,103,7,0,0,0,103,108,3,14,7,0,104,105,10,3,0,0,105,
        106,7,1,0,0,106,108,3,14,7,0,107,101,1,0,0,0,107,104,1,0,0,0,108,
        111,1,0,0,0,109,107,1,0,0,0,109,110,1,0,0,0,110,13,1,0,0,0,111,109,
        1,0,0,0,112,113,6,7,-1,0,113,114,5,3,0,0,114,115,3,2,1,0,115,116,
        5,4,0,0,116,119,1,0,0,0,117,119,3,4,2,0,118,112,1,0,0,0,118,117,
        1,0,0,0,119,125,1,0,0,0,120,121,10,3,0,0,121,122,7,0,0,0,122,124,
        3,14,7,4,123,120,1,0,0,0,124,127,1,0,0,0,125,123,1,0,0,0,125,126,
        1,0,0,0,126,15,1,0,0,0,127,125,1,0,0,0,12,51,55,59,70,72,77,89,99,
        107,109,118,125
    ]

class ExprParser ( Parser ):

    grammarFileName = "Expr.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'.'", "'-'", "'('", "')'", "'/'", "'*'", 
                     "'+'", "'['", "']'", "','", "'..'", "<INVALID>", "'t'", 
                     "<INVALID>", "<INVALID>", "'sum'" ]

    symbolicNames = [ "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                      "NUMBER", "TIME", "IDENTIFIER", "COMPARISON", "TIME_SUM", 
                      "WS" ]

    RULE_fullexpr = 0
    RULE_expr = 1
    RULE_atom = 2
    RULE_timeShiftRange = 3
    RULE_timeRange = 4
    RULE_shift = 5
    RULE_shift_expr = 6
    RULE_right_expr = 7

    ruleNames =  [ "fullexpr", "expr", "atom", "timeShiftRange", "timeRange", 
                   "shift", "shift_expr", "right_expr" ]

    EOF = Token.EOF
    T__0=1
    T__1=2
    T__2=3
    T__3=4
    T__4=5
    T__5=6
    T__6=7
    T__7=8
    T__8=9
    T__9=10
    T__10=11
    NUMBER=12
    TIME=13
    IDENTIFIER=14
    COMPARISON=15
    TIME_SUM=16
    WS=17

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class FullexprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext,0)


        def EOF(self):
            return self.getToken(ExprParser.EOF, 0)

        def getRuleIndex(self):
            return ExprParser.RULE_fullexpr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFullexpr" ):
                return visitor.visitFullexpr(self)
            else:
                return visitor.visitChildren(self)




    def fullexpr(self):

        localctx = ExprParser.FullexprContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_fullexpr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 16
            self.expr(0)
            self.state = 17
            self.match(ExprParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ExprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return ExprParser.RULE_expr

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class TimeSumContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def TIME_SUM(self):
            return self.getToken(ExprParser.TIME_SUM, 0)
        def IDENTIFIER(self):
            return self.getToken(ExprParser.IDENTIFIER, 0)
        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext,0)

        def shift(self):
            return self.getTypedRuleContext(ExprParser.ShiftContext,0)

        def timeShiftRange(self):
            return self.getTypedRuleContext(ExprParser.TimeShiftRangeContext,0)

        def timeRange(self):
            return self.getTypedRuleContext(ExprParser.TimeRangeContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeSum" ):
                return visitor.visitTimeSum(self)
            else:
                return visitor.visitChildren(self)


    class NegationContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNegation" ):
                return visitor.visitNegation(self)
            else:
                return visitor.visitChildren(self)


    class UnsignedAtomContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def atom(self):
            return self.getTypedRuleContext(ExprParser.AtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitUnsignedAtom" ):
                return visitor.visitUnsignedAtom(self)
            else:
                return visitor.visitChildren(self)


    class ExpressionContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitExpression" ):
                return visitor.visitExpression(self)
            else:
                return visitor.visitChildren(self)


    class TimeIndexContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IDENTIFIER(self):
            return self.getToken(ExprParser.IDENTIFIER, 0)
        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeIndex" ):
                return visitor.visitTimeIndex(self)
            else:
                return visitor.visitChildren(self)


    class ComparisonContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext,i)

        def COMPARISON(self):
            return self.getToken(ExprParser.COMPARISON, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitComparison" ):
                return visitor.visitComparison(self)
            else:
                return visitor.visitChildren(self)


    class TimeShiftContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IDENTIFIER(self):
            return self.getToken(ExprParser.IDENTIFIER, 0)
        def shift(self):
            return self.getTypedRuleContext(ExprParser.ShiftContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeShift" ):
                return visitor.visitTimeShift(self)
            else:
                return visitor.visitChildren(self)


    class FunctionContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IDENTIFIER(self):
            return self.getToken(ExprParser.IDENTIFIER, 0)
        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFunction" ):
                return visitor.visitFunction(self)
            else:
                return visitor.visitChildren(self)


    class AddsubContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext,i)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAddsub" ):
                return visitor.visitAddsub(self)
            else:
                return visitor.visitChildren(self)


    class PortFieldContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IDENTIFIER(self, i:int=None):
            if i is None:
                return self.getTokens(ExprParser.IDENTIFIER)
            else:
                return self.getToken(ExprParser.IDENTIFIER, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPortField" ):
                return visitor.visitPortField(self)
            else:
                return visitor.visitChildren(self)


    class MuldivContext(ExprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.ExprContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext,i)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitMuldiv" ):
                return visitor.visitMuldiv(self)
            else:
                return visitor.visitChildren(self)



    def expr(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = ExprParser.ExprContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 2
        self.enterRecursionRule(localctx, 2, self.RULE_expr, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 59
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,2,self._ctx)
            if la_ == 1:
                localctx = ExprParser.UnsignedAtomContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 20
                self.atom()
                pass

            elif la_ == 2:
                localctx = ExprParser.PortFieldContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 21
                self.match(ExprParser.IDENTIFIER)
                self.state = 22
                self.match(ExprParser.T__0)
                self.state = 23
                self.match(ExprParser.IDENTIFIER)
                pass

            elif la_ == 3:
                localctx = ExprParser.NegationContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 24
                self.match(ExprParser.T__1)
                self.state = 25
                self.expr(9)
                pass

            elif la_ == 4:
                localctx = ExprParser.ExpressionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 26
                self.match(ExprParser.T__2)
                self.state = 27
                self.expr(0)
                self.state = 28
                self.match(ExprParser.T__3)
                pass

            elif la_ == 5:
                localctx = ExprParser.FunctionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 30
                self.match(ExprParser.IDENTIFIER)
                self.state = 31
                self.match(ExprParser.T__2)
                self.state = 32
                self.expr(0)
                self.state = 33
                self.match(ExprParser.T__3)
                pass

            elif la_ == 6:
                localctx = ExprParser.TimeShiftContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 35
                self.match(ExprParser.IDENTIFIER)
                self.state = 36
                self.match(ExprParser.T__7)
                self.state = 37
                self.shift()
                self.state = 38
                self.match(ExprParser.T__8)
                pass

            elif la_ == 7:
                localctx = ExprParser.TimeIndexContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 40
                self.match(ExprParser.IDENTIFIER)
                self.state = 41
                self.match(ExprParser.T__7)
                self.state = 42
                self.expr(0)
                self.state = 43
                self.match(ExprParser.T__8)
                pass

            elif la_ == 8:
                localctx = ExprParser.TimeSumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 45
                self.match(ExprParser.TIME_SUM)
                self.state = 46
                self.match(ExprParser.T__2)
                self.state = 55
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input,1,self._ctx)
                if la_ == 1:
                    self.state = 51
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,0,self._ctx)
                    if la_ == 1:
                        self.state = 47
                        self.expr(0)
                        pass

                    elif la_ == 2:
                        self.state = 48
                        self.shift()
                        pass

                    elif la_ == 3:
                        self.state = 49
                        self.timeShiftRange()
                        pass

                    elif la_ == 4:
                        self.state = 50
                        self.timeRange()
                        pass


                    self.state = 53
                    self.match(ExprParser.T__9)


                self.state = 57
                self.match(ExprParser.IDENTIFIER)
                self.state = 58
                self.match(ExprParser.T__3)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 72
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,4,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 70
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
                    if la_ == 1:
                        localctx = ExprParser.MuldivContext(self, ExprParser.ExprContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expr)
                        self.state = 61
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 7)")
                        self.state = 62
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not(_la==5 or _la==6):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 63
                        self.expr(8)
                        pass

                    elif la_ == 2:
                        localctx = ExprParser.AddsubContext(self, ExprParser.ExprContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expr)
                        self.state = 64
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
                        self.state = 65
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not(_la==2 or _la==7):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 66
                        self.expr(7)
                        pass

                    elif la_ == 3:
                        localctx = ExprParser.ComparisonContext(self, ExprParser.ExprContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_expr)
                        self.state = 67
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
                        self.state = 68
                        self.match(ExprParser.COMPARISON)
                        self.state = 69
                        self.expr(6)
                        pass

             
                self.state = 74
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,4,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class AtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return ExprParser.RULE_atom

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class NumberContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NUMBER(self):
            return self.getToken(ExprParser.NUMBER, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNumber" ):
                return visitor.visitNumber(self)
            else:
                return visitor.visitChildren(self)


    class IdentifierContext(AtomContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.AtomContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def IDENTIFIER(self):
            return self.getToken(ExprParser.IDENTIFIER, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIdentifier" ):
                return visitor.visitIdentifier(self)
            else:
                return visitor.visitChildren(self)



    def atom(self):

        localctx = ExprParser.AtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_atom)
        try:
            self.state = 77
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [12]:
                localctx = ExprParser.NumberContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 75
                self.match(ExprParser.NUMBER)
                pass
            elif token in [14]:
                localctx = ExprParser.IdentifierContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 76
                self.match(ExprParser.IDENTIFIER)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TimeShiftRangeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.shift1 = None # ShiftContext
            self.shift2 = None # ShiftContext

        def shift(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ShiftContext)
            else:
                return self.getTypedRuleContext(ExprParser.ShiftContext,i)


        def getRuleIndex(self):
            return ExprParser.RULE_timeShiftRange

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeShiftRange" ):
                return visitor.visitTimeShiftRange(self)
            else:
                return visitor.visitChildren(self)




    def timeShiftRange(self):

        localctx = ExprParser.TimeShiftRangeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_timeShiftRange)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 79
            localctx.shift1 = self.shift()
            self.state = 80
            self.match(ExprParser.T__10)
            self.state = 81
            localctx.shift2 = self.shift()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class TimeRangeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.expr1 = None # ExprContext
            self.expr2 = None # ExprContext

        def expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.ExprContext)
            else:
                return self.getTypedRuleContext(ExprParser.ExprContext,i)


        def getRuleIndex(self):
            return ExprParser.RULE_timeRange

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitTimeRange" ):
                return visitor.visitTimeRange(self)
            else:
                return visitor.visitChildren(self)




    def timeRange(self):

        localctx = ExprParser.TimeRangeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_timeRange)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 83
            localctx.expr1 = self.expr(0)
            self.state = 84
            self.match(ExprParser.T__10)
            self.state = 85
            localctx.expr2 = self.expr(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class ShiftContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TIME(self):
            return self.getToken(ExprParser.TIME, 0)

        def shift_expr(self):
            return self.getTypedRuleContext(ExprParser.Shift_exprContext,0)


        def getRuleIndex(self):
            return ExprParser.RULE_shift

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitShift" ):
                return visitor.visitShift(self)
            else:
                return visitor.visitChildren(self)




    def shift(self):

        localctx = ExprParser.ShiftContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_shift)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 87
            self.match(ExprParser.TIME)
            self.state = 89
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==2 or _la==7:
                self.state = 88
                self.shift_expr(0)


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class Shift_exprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return ExprParser.RULE_shift_expr

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class SignedAtomContext(Shift_exprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.Shift_exprContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def atom(self):
            return self.getTypedRuleContext(ExprParser.AtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignedAtom" ):
                return visitor.visitSignedAtom(self)
            else:
                return visitor.visitChildren(self)


    class SignedExpressionContext(Shift_exprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.Shift_exprContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignedExpression" ):
                return visitor.visitSignedExpression(self)
            else:
                return visitor.visitChildren(self)


    class ShiftMuldivContext(Shift_exprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.Shift_exprContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def shift_expr(self):
            return self.getTypedRuleContext(ExprParser.Shift_exprContext,0)

        def right_expr(self):
            return self.getTypedRuleContext(ExprParser.Right_exprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitShiftMuldiv" ):
                return visitor.visitShiftMuldiv(self)
            else:
                return visitor.visitChildren(self)


    class ShiftAddsubContext(Shift_exprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.Shift_exprContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def shift_expr(self):
            return self.getTypedRuleContext(ExprParser.Shift_exprContext,0)

        def right_expr(self):
            return self.getTypedRuleContext(ExprParser.Right_exprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitShiftAddsub" ):
                return visitor.visitShiftAddsub(self)
            else:
                return visitor.visitChildren(self)



    def shift_expr(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = ExprParser.Shift_exprContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 12
        self.enterRecursionRule(localctx, 12, self.RULE_shift_expr, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 99
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,7,self._ctx)
            if la_ == 1:
                localctx = ExprParser.SignedAtomContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 92
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not(_la==2 or _la==7):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 93
                self.atom()
                pass

            elif la_ == 2:
                localctx = ExprParser.SignedExpressionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 94
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not(_la==2 or _la==7):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 95
                self.match(ExprParser.T__2)
                self.state = 96
                self.expr(0)
                self.state = 97
                self.match(ExprParser.T__3)
                pass


            self._ctx.stop = self._input.LT(-1)
            self.state = 109
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,9,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 107
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input,8,self._ctx)
                    if la_ == 1:
                        localctx = ExprParser.ShiftMuldivContext(self, ExprParser.Shift_exprContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_shift_expr)
                        self.state = 101
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
                        self.state = 102
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not(_la==5 or _la==6):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 103
                        self.right_expr(0)
                        pass

                    elif la_ == 2:
                        localctx = ExprParser.ShiftAddsubContext(self, ExprParser.Shift_exprContext(self, _parentctx, _parentState))
                        self.pushNewRecursionContext(localctx, _startState, self.RULE_shift_expr)
                        self.state = 104
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException
                            raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                        self.state = 105
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not(_la==2 or _la==7):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 106
                        self.right_expr(0)
                        pass

             
                self.state = 111
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,9,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx


    class Right_exprContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return ExprParser.RULE_right_expr

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class RightExpressionContext(Right_exprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.Right_exprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def expr(self):
            return self.getTypedRuleContext(ExprParser.ExprContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRightExpression" ):
                return visitor.visitRightExpression(self)
            else:
                return visitor.visitChildren(self)


    class RightMuldivContext(Right_exprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.Right_exprContext
            super().__init__(parser)
            self.op = None # Token
            self.copyFrom(ctx)

        def right_expr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(ExprParser.Right_exprContext)
            else:
                return self.getTypedRuleContext(ExprParser.Right_exprContext,i)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRightMuldiv" ):
                return visitor.visitRightMuldiv(self)
            else:
                return visitor.visitChildren(self)


    class RightAtomContext(Right_exprContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a ExprParser.Right_exprContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def atom(self):
            return self.getTypedRuleContext(ExprParser.AtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRightAtom" ):
                return visitor.visitRightAtom(self)
            else:
                return visitor.visitChildren(self)



    def right_expr(self, _p:int=0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = ExprParser.Right_exprContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 14
        self.enterRecursionRule(localctx, 14, self.RULE_right_expr, _p)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 118
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [3]:
                localctx = ExprParser.RightExpressionContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 113
                self.match(ExprParser.T__2)
                self.state = 114
                self.expr(0)
                self.state = 115
                self.match(ExprParser.T__3)
                pass
            elif token in [12, 14]:
                localctx = ExprParser.RightAtomContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 117
                self.atom()
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 125
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input,11,self._ctx)
            while _alt!=2 and _alt!=ATN.INVALID_ALT_NUMBER:
                if _alt==1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    localctx = ExprParser.RightMuldivContext(self, ExprParser.Right_exprContext(self, _parentctx, _parentState))
                    self.pushNewRecursionContext(localctx, _startState, self.RULE_right_expr)
                    self.state = 120
                    if not self.precpred(self._ctx, 3):
                        from antlr4.error.Errors import FailedPredicateException
                        raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
                    self.state = 121
                    localctx.op = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not(_la==5 or _la==6):
                        localctx.op = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 122
                    self.right_expr(4) 
                self.state = 127
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input,11,self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[1] = self.expr_sempred
        self._predicates[6] = self.shift_expr_sempred
        self._predicates[7] = self.right_expr_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def expr_sempred(self, localctx:ExprContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 7)
         

            if predIndex == 1:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 2:
                return self.precpred(self._ctx, 5)
         

    def shift_expr_sempred(self, localctx:Shift_exprContext, predIndex:int):
            if predIndex == 3:
                return self.precpred(self._ctx, 4)
         

            if predIndex == 4:
                return self.precpred(self._ctx, 3)
         

    def right_expr_sempred(self, localctx:Right_exprContext, predIndex:int):
            if predIndex == 5:
                return self.precpred(self._ctx, 3)
         




