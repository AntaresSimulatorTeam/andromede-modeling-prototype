# Mathematical expressions and syntax


An essential aspect of **Gems** is that it allows mathematical expressions (describing models) to be defined in configuration files, independently of any software or programming language. Mathematical expressions are represented here as human-readable equations. This allows a large flexibility in defining objects of optimisation.

## Arithmetic operators

The following operators are allowed between two elements:

- **+**: addition of two elements
- **-**: subtraction
- __*__: multiplication
- **/**: division
- **=**: equality, only allowed for constraint definitions
- **<=**: less or equal to, only allowed for constraint definitions
- **>=**: greater or equal to, only allowed for constraint definitions

## Scalars

You can use simple floating-point scalars anywhere. The character `.` represents the floating point.  
Example:

~~~yaml
expression: 3 * 67.43 - 5 / 3.14
~~~

## Parameters

You can use a parameter by using its ID.   
Example:

~~~yaml
expression: 3 * parameter_1 + 6.345 / parameter_2
~~~

## Variables

You can use a parameter by using its ID. Note that if the variable is time-dependent (resp. scenario-dependent), then
it can be used only for constraints that are time-dependent (resp. scenario-dependent), and that its values
will be implicitly unfolded during the interpretation of the expression.  
Example:

~~~yaml
expression: 3 * parameter_1 * variable_a + variable_b + 56.4 <= variable_4 * 439
~~~

Also note that all expressions must be linear with respect to variables.  
Examples of prohibited expressions:

~~~yaml
(X) expression: variable_a * variable_b
~~~

~~~yaml
(X) expression: 3 / variable_a
~~~

## Fields

You can use a port field (cf Ports in the Models) in the expression, using its ID composed by: **port_ID.field_ID**. Note that if the
port is time-dependent (resp. scenario-dependent), which is deduced from the variables defining it, then
it can be used only for constraints that are time-dependent (resp. scenario-dependent), and that its values
will be implicitly unfolded during the interpretation of the expression. Unless, of course, you use time (resp.
scenario)
aggregators to aggregate it into a time-constant (resp. scenario-constant) value.  
Example:

~~~yaml
expression: 45.4 * port_3.field_6 + 5.4 * variable_6 - 9
~~~

Note that, like with variables, all expressions must be linear with respect to ports.

## Time operators

For time-dependent parameters, variables, and port fields, you can use these time operators:

- **[t]** suffix: this operator is implied, but can be used if you like to explicit your intent
- **[N]** suffix: where N is any expression resolving to an integer (using only scalars and parameters), this selects
  the value of the element at the N-th timestamp.
- **[t+N]** suffix: where N is any expression resolving to an integer (using only scalars and parameters), this is a
  forward shift operator of N timestamps.
- **[t-N]** suffix: where N is any expression resolving to an integer (using only scalars and parameters), this is a
  backward shift operator of N timestamps.
- **sum(X)** aggregator: where X is the time-dependent operand, this operator sums the operand on the whole optimisation
  horizon.
- **sum(S .. E, X)** aggregator: where X is the time-dependent operand, this operator sums the operand between S and E (
  included), where:
    - **S** represents the first timestamp, either as an expression resolving to an integer, or a time-shift expression
      like the ones defined above
    - **E** represents the last timestamp, either as an expression resolving to an integer, or a time-shift expression
      like the ones defined above

Examples:

~~~yaml
expression: a[t] + b[t + 5] * c[t - 3 - 65 * parameter_1] - sum(a)
~~~

~~~yaml
expression: sum(4 .. 87, c) - sum(t - 3 * parameter_15 + 5 .. t, d)
~~~

## Scenario operators

For scenario-dependent parameters, variables, and port fields, you can use this operator:

- **expec(X)** aggregator: where X is the scenario-dependent operand, this operator computes its expected value (i.e.
  its scenario-wise average).

## Port operators

You can aggregate incoming ports using the following operator:

- **sum_connections(port.field)**: where "port" is the port ID and "field" is the field ID, this operator computes the
  sum of values of this port field, on all incoming connections from other models.  
  Note that the resulting sum can be time-dependent and/or scenario-dependent, depending on the port definition.

Examples:

~~~yaml
expression: sum(dc_port.flow) = 0
~~~

## Rules for IDs

All IDs in the model [library](libraries.md) and [system](systems.md) file must respect the following:

- Alphanumeric characters are allowed, as well as the underscore (`_`) character
- All other characters are prohibited
- Only lower-case is allowed