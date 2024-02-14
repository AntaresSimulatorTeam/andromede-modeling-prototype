# Expression grammar definition

[Expr.g4](Expr.g4) defines the grammar for mathematical expressions
use for defining constraints, objective, etc.

[ANTLR](https://www.antlr.org) needs to be used to generate the associated
parser code, which must be placed in [andromede.expression.parsing.antlr](/src/andromede/expression/parsing/antlr)
package.

ANTLR may be used on the command line, or for example through
the associated PyCharm plugin.

We use the visitor and not the listener in order to translate ANTLR AST
into our own AST, so the options `-visitor` and `-no-listener` need to
to be used.
