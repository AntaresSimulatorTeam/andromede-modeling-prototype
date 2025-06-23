# System file

The system file (.yml) describes the energy system that is to be simulated, by listing 

- the **components** of the system, i.e., instances of [models](libraries.md#models);
- their **port connections**.

The header of the yml file must contain exactly one "system" key at the root level. 
The **system** object contains one **id**, one **description**, one **model-libraries** collection, one **components**
collection.  Unless stated otherwise, all listed fields are mandatory.

## ID, description, and model libraries

Example:

~~~yaml
system:
  id: my_system
  description: example of system
  model-libraries: my_library_id, my_other_library_id
~~~

- **id**: an ID for your system. Has no effect on the simulation.
- **description** _(optional)_: a free description of your system. Has no effect on the simulation.
- **model-libraries**: a collection of model libraries needed for your system. Must contain at least one element, and
  refer to IDs of model libraries found in the **input/model-libraries" directory. Beware that the ID of the library is
  one defined in its header, not the name of the file.

## Components

The **components** section lists all the components of your simulated system, i.e., instances of [models](libraries.md#models)  
Example:

~~~yaml
components:
  - id: generator1
    model: my_library_id.generator_dc
    scenario-group: thermal_group
    parameters:
      - id: min_active_power_setpoint
        time-dependent: false
        scenario-dependent: false
        value: 100
      - id: max_active_power_setpoint
        time-dependent: true
        scenario-dependent: true
        value: generator1_max_p
      - id: proportional_cost
        time-dependent: false
        scenario-dependent: true
        value: generator1_cost
     - id: fixed_cost
        time-dependent: false
        scenario-dependent: false
        value: 0
  - id: generator2
    model: my_lib_id.generator_dc
    scenario-group: hydro_group
    parameters:
      - id: min_active_power_setpoint
        time-dependent: false
        scenario-dependent: false
        value: 20
      - id: max_active_power_setpoint
        time-dependent: true
        scenario-dependent: false
        value: generator2_max_p
      - id: proportional_cost
        time-dependent: false
        scenario-dependent: false
        value: 0.5
      - id: fixed_cost
        time-dependent: false
        scenario-dependent: false
        value: 0
  - id: demand
      model: basic.load
      parameters:
        - id: load
          time-dependent: true
          scenario-dependent: true
          value: load_data
  - id: node1
    model: my_lib_id.node
~~~

- **id**: an ID for the component. Must be unique in the scope of the system, and respect [these rules](syntax.md#rules-for-ids).
- **model**: the ID of the model to use for the component, composed as "library_id.model_id", where "library_id" is the
  ID of the model library (must be listed in the [required model libraries](libraries.md)), and
  "model_id" is the ID of the model as it is defined inside the [model library](libraries.md#models).
- **scenario-group** _(only needed if the model has scenario-dependent parameters)_: the ID of the scenario group this
  component belongs to. Must be correctly configured in the [scenario builder](#scenario-builder), and
  respect [these rules](syntax.md#rules-for-ids).
- **parameters** _(not needed if model has no parameters)_: a collection of values for the model's parameters. Note that
  all the parameters of the model should have their values assigned by the component.
    - **id**: the ID of the parameter, as defined by the [model](libraries.md#models)
    - **time-dependent**: `true` or `false`, indicates whether the parameter depends on time or is constant across the
      whole simulation horizon. If the model parameter is not time-dependent, this can't be set to true.
    - **scenario-dependent**: `true` or `false`, indicates whether the parameter changes depending on the simulated
      scenario, or is the same for all scenarios. If the model parameter is not scenario-dependent, this can't be set to
      true.
    - **value**: the value of the parameter:
        - If the parameter is constant, then this is a numerical value (using a data-series ID is not allowed in this
          case)
        - If the parameter is time-dependent, then this is the ID of a time-dependent [data serie](data.md)
        - If the parameter is scenario-dependent, then this is the ID of a scenario-dependent [data serie](data.md)
        - If the parameter is time and scenario-dependent, then this is the ID of a
          time-and-scenario-dependent [data serie](data.md)

## Port connections

The **connections** section lists the port connections between components.  
Example:

~~~yaml
connections:
  - component1: generator1
    port1: injection_port
    component2: node1
    port2: injection_port

  - component1: generator2
    port1: injection_port
    component2: node1
    port2: injection_port

  - component1: demand
    port1: injection_port
    component2: node1
    port2: injection_port
~~~

- **component1**, **component2**: the IDs of the components to connect together
- **port1**, **port2**: the IDs of the respective ports to connect (as defined by the two models). Note that exactly one
  of the two models must define the port (in the "port-field-definition" section).


## Scenario builder

_**This feature is under development**_  
This feature allows you to map, for different scenario groups of components, all scenarios to a limited number of data
sets. This prevents duplication of data when some data-series are "less" scenario-dependent than others.  
For now, "scenario-groups" are ignored and scenario indices map to data set indices.
