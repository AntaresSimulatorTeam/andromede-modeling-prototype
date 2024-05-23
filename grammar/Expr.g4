/*
Copyright (c) 2024, RTE (https://www.rte-france.com)

See AUTHORS.txt

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

SPDX-License-Identifier: MPL-2.0

This file is part of the Antares project.
*/

grammar Expr;

/* To match the whole input */
fullexpr: expr EOF;

shift: TIME shift_expr?;

shift_expr
    : op=('+' | '-') NUMBER                    # signedNumber
    | op=('+' | '-') IDENTIFIER                # signedIdentifier
    | op=('+' | '-') '(' expr ')'              # signedExpression
    | op=('+' | '-') IDENTIFIER '(' expr ')'   # signedFunction
    | shift_expr op=('/' | '*') NUMBER         # shiftMuldivNumber
    | shift_expr op=('/' | '*') IDENTIFIER     # shiftMuldivIdentifier
    | shift_expr op=('/' | '*') '(' expr ')'   # shiftMuldiv
    | shift_expr op=('+' | '-') expr           # shiftAddsub
    ;

expr
    : '-' expr                  # negation
    | expr op=('/' | '*') expr  # muldiv
    | expr op=('+' | '-') expr  # addsub
    | expr COMPARISON expr      # comparison
    | IDENTIFIER                # identifier
    | IDENTIFIER '.' IDENTIFIER # portField
    | NUMBER                    # number
    | '(' expr ')'              # expression
    | IDENTIFIER '(' expr ')'   # function
    | IDENTIFIER '[' shift (',' shift)* ']'  # timeShift
    | IDENTIFIER '[' expr  (',' expr )* ']'  # timeIndex
    | IDENTIFIER '[' shift1=shift '..' shift2=shift ']'      # timeShiftRange
    | IDENTIFIER '[' expr '..' expr ']'      # timeRange
    ;

fragment DIGIT         : [0-9] ;
fragment CHAR          : [a-zA-Z_];
fragment CHAR_OR_DIGIT : (CHAR | DIGIT);

NUMBER        : DIGIT+ ('.' DIGIT+)?;
TIME          : 't';
IDENTIFIER    : CHAR CHAR_OR_DIGIT*;
COMPARISON    : ( '=' | '>=' | '<=' );
ADDSUB        : ( '+' | '-' );
MULDIV        : ( '*' | '/' );
LBRACKET: '[';
RBRACKET: ']';

WS: (' ' | '\t' | '\r'| '\n') -> skip;
