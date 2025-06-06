# Models

A model is an abstract object, that will be instantiated once or several times in a system. A model is defined by:

- **id**: an ID for the model. Must be unique inside the scope of the library, and
  respect [these rules](syntax.md#rules-for-ids).
- **description** _(optional)_: a free description of the model. Has no effect on the simulation.
- **parameters** _(optional)_: a collection of parameters for the model. The values for these parameters will be set in
  the [system file](systems.md).
    - **id**: an ID for the parameter. Must be unique inside the scope of the model, and
      respect [these rules](syntax.md#rules-for-ids).
    - **time-dependent**: `true` or `false`, indicates whether the parameter depends on time or is constant across the
      whole simulation horizon.
    - **scenario-dependent**: `true` or `false`, indicates whether the parameter changes depending on the simulated
      scenario, or is the same for all scenarios.
- **variables** _(optional)_: a collection of optimization variables that are defined for this model
    - **id**: an ID for the variable. Must be unique inside the scope of the model, and
      respect [these rules](syntax.md#rules-for-ids).
    - **variable-type**: `continuous`, `integer`, or `binary`
    - **lower-bound** _(optional)_: an [expression](syntax.md) representing the lower bound of the variable. Must use scalars
      and/or parameters only. If missing, defaults to -inf for continuous and integer types, or 0 for binary.
    - **upper-bound** _(optional)_: an [expression](syntax.md) representing the upper bound of the variable. Must use scalars
      and/or parameters only. If missing, defaults to +inf for continuous and integer types, or 1 for binary.
- **constraints** _(optional)_: a collection of "internal" optimization constraints set by the model
    - **id**: an ID for the constraint. Must be unique inside the scope of the model, and
      respect [these rules](syntax.md#rules-for-ids).
    - **expression**: an [expression](syntax.md) representing the constraint. Can use scalars, parameters, internal
      variables, time and scenario operators.
      Must contain exactly one comparison operator (**=**, **<=**, or **>=**).
- **binding-constraints** _(optional)_: a collection of "external" optimization constraints set by the model, that use
  ports. While these have no
  real difference with "internal constraints", it is best practice to separate internal and external constraints in
  order to make the model more readable.
    - **id**: an ID for the constraint. Must be unique inside the scope of the model, and
      respect [these rules](syntax.md#rules-for-ids).
    - **expression**: an [expression](syntax.md) representing the constraint. Can use scalars, parameters, internal
      variables, ports, and time, scenario, and port operators.
- **objective** _(optional)_: an [expression](syntax.md) representing the (additive) participation of the model to
  the optimization objective.
  Note that **minimization** is implied. The expression can use scalars, parameters and variables of the model.
- **ports** _(optional)_: a collection of ports exposed by the model, either as input or output
    - **id**: an ID for the port. Must be unique in the scope of the model, and respect [these rules](syntax.md#rules-for-ids).
    - **type**: the type of the port. Must refer to the ID of a port type defined in the [port types](libraries.md#port-types)
      section.
- **port-field-definitions** _(optional)_: a collection of definitions for ports output by this model. Note that if the
  model is to define a port, then it must define all fields of this port.
    - **port**: the ID of a port exposed by the model (defined in the **ports** section above)
    - **field**: the field to define (refers to a field ID defined in the port type)
    - **definition**: an [expression](syntax.md) representing the definition of the field. Can use scalars,
      parameters, and variables of the model.

### Example 1: a simple generator

~~~yaml
  - id: generator_dc
    description: A simple DC model of a generator
    parameters:
      - id: min_active_power_setpoint
        time-dependent: false
        scenario-dependent: false
      - id: max_active_power_setpoint
        time-dependent: true
        scenario-dependent: true
      - id: proportional_cost
        time-dependent: false
        scenario-dependent: true
      - id: fixed_cost
        time-dependent: false
        scenario-dependent: true
    variables:
      - id: is_on
        variable-type: boolean
        lower-bound: 0
        upper-bound: 1
      - id: active_power
        variable-type: continuous
        lower-bound: 0
        upper-bound: max_active_power_setpoint
    constraints:
      - id: respect_min_p
        expression: active_power >= is_on * min_active_power_setpoint
    objective: active_power * proportional_cost + fixed_cost * is_on
    ports:
      - id: injection
        type: dc_port
    port-field-definitions:
      - port: injection
        field: flow
        definition: active_power
~~~

### Example 2: a node

~~~yaml
  - id: node
    description: A balance node with injections (productions and loads)
    ports:
      - id: injections
        type: dc_port
    binding-constraints:
      - id: balance
        expression: sum_connections(injections.flow) = 0
~~~