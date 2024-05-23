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

expr
    : atom                                     # unsignedAtom
    | IDENTIFIER '.' IDENTIFIER                # portField
    | '-' expr                                 # negation
    | '(' expr ')'                             # expression
    | expr op=('/' | '*') expr                 # muldiv
    | expr op=('+' | '-') expr                 # addsub
    | expr COMPARISON expr                     # comparison
    | IDENTIFIER '(' expr ')'                  # function
    | IDENTIFIER '[' shift (',' shift)* ']'    # timeShift
    | IDENTIFIER '[' expr  (',' expr )* ']'    # timeIndex
    | IDENTIFIER '[' shift1=shift '..' shift2=shift ']'     # timeShiftRange
    | IDENTIFIER '[' expr '..' expr ']'        # timeRange
    ;

atom
    : NUMBER                                   # number
    | IDENTIFIER                               # identifier
    ;

shift: TIME shift_expr?;

shift_expr
    : op=('+' | '-') atom                      # signedAtom
    | op=('+' | '-') '(' expr ')'              # signedExpression
    | shift_expr op=('/' | '*') atom           # shiftMuldivAtom
    | shift_expr op=('/' | '*') '(' expr ')'   # shiftMuldiv
    | shift_expr op=('+' | '-') atom           # shiftAddsubAtom
    | shift_expr op=('+' | '-') '(' expr ')'   # shiftAddsub
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
