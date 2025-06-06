# Library of models

A library is a collection of abstract objects: port types and models.

## Structure of a library file
The header of the .yml file must contain exactly one "library" key at the root level.  
The **library** object contains one **id**, one **description**, one **port-types** collection, and one **models**
collection. Unless stated otherwise, all listed fields are mandatory.

## ID & description

Example:

~~~yaml
library:
  id: my_library_id
  description: my library is great!
~~~

- **id**: the unique ID for you library. Beware that if you are using many libraries in your study, every library must
  have a unique ID. This ID will be used inside the [system description file](systems.md) in order to reference the
  library's objects. It must respect [these rules](syntax.md#rules-for-ids).
- **description** _(optional)_: a free description of your library. Has no effect on the simulation.


## Port types

The **port-types** collection lists the possible types of [ports](models.md) inside the library,
that can be used by models/components to communicate with each-other.  
This field is optional: 
- you can develop a library with no ports, even though this would have limited interest (the
models would not be able to communicate with each-other),
- you can develop a library that use ports defined in another library.
Example:

~~~yaml
port-types:
  - id: dc_port
    description: A port which transfers power flow value
    fields:
      - id: flow
  - id: ac_port
    description: A port which transfers power flow and voltage angle values
    fields:
      - id: flow
      - id: angle
~~~

- **id**: the ID for the port type. Must be unique inside the scope of the library, and
  respect [these rules](syntax.md#rules-for-ids).
- **description** _(optional)_: a free description of your port type. Has no effect on the simulation.
- **fields**: a collection of coherent fields that transit through this port type. A field holds a single floating
  number.
    - **id**: the ID of the field. Must be unique in the scope of the port type, and
      respect [these rules](syntax.md#rules-for-ids).
- **area-connection** _(optional)_: used only for the [antares-modeler](https://antares-simulator.readthedocs.io/en/latest/user-guide/modeler/01-overview-modeler/).
  For more information on hybrid
  studies, [see the relevant documentation](https://antares-simulator.readthedocs.io/en/latest/user-guide/modeler/01-overview-modeler/).

    

## Models

The **models** collection lists all the [models](models.md) that can be instantiated using your library. See [the relevant page](models.md) for the definition of models inside a library file.

~~~yaml
models:
  - id: node
    description: A balance node with injections (productions and loads)
    ports:
      - id: injections
        type: dc_port
    binding-constraints:
      - id: balance
        expression: sum_connections(injections.flow) = 0
~~~
