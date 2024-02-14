grammar Expr;

expr: expr '*' expr             # multiplication
    | expr '/' expr             # division
    | expr '+' expr             # addition
    | expr '-' expr             # subtraction
    | '-' expr                  # negation
    | expr COMPARISON expr      # comparison
    | expr '.sum()'             # sum
    | expr '.sum_connections()' # sumConnections
    | expr '.shift(' expr ')'   # timeShift
    | IDENTIFIER                # identifier
    | IDENTIFIER '.' IDENTIFIER # portField
    | NUMBER                    # number
    | '(' expr ')'              # expression
    ;

fragment DIGIT         : [0-9] ;
fragment CHAR          : [a-zA-Z];
fragment CHAR_OR_DIGIT : (CHAR | DIGIT);

NUMBER        : DIGIT+ ('.' DIGIT+)?;
IDENTIFIER    : CHAR CHAR_OR_DIGIT*;
COMPARISON    : ( '=' | '>=' | '<=' );

WS: (' ' | '\t' | '\r'| '\n') -> skip;
