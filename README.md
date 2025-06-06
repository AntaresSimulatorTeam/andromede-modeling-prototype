# andromede-modeling-prototype

Andromede is an open-source tool, developed in Python, for the modeling and the simulation of complex energy systems under uncertainty.

## The vision

Andromede introduces a novel approach to model and simulate energy systems, centered around a simple principle: getting models out of the code.

To develop and test new models of energy system components, writing software code should not be a prerequisite. This is where the Andromede 'modeler' package excels, offering users a "no-code" modeling experience with unparalleled versatility.

Within the 'modeler' framework:
- Abstract mathematical descriptions of models are described in 'library' files, formatted in YAML. These files contain behavioral equations written in a straightforward modeling language. 
- Meanwhile, the numerical representation of a case study is detailed in separate 'system' files, also in YAML format. 
These files outline the components of a system, with their numerical parameters: nodes in the graph represent instances of abstract models from the 'library', and vertices denote connections between components (as defined by 'ports').

This Python package features a generic interpreter capable of generating optimization problems from any library and system files that adhere to the modeling language syntax. It then employs dedicated optimization code to solve these problems. The Python API facilitates reading case studies stored in YAML format, modifying them, or creating new ones from scratch by scripting.



## Repository structure

The repository consists in:
- [src/andromede](./src/andromede):
  python package that implements the concepts (models, ports)
  and allows for simulation using them.
- [tests](./tests):
  python tests illustrating the use and behaviour of the concepts
- [models-design](./models-design):
  mainly schemas to design the models that one could implement
  using our concepts.

### 'Library' file examples

Examples of 'library' files, that describe abstract models, may be found in [src/andromede/libs](./src/andromede/libs).

### 'System' file examples

Examples of 'system' files, that describe test cases, may be found in [tests/e2e/models/andromede-v1/systems](./tests/e2e/models/andromede-v1/systems).

### Code example

Examples of codes that load 'library' and 'system' files, interprets and simulates them may be found in [tests/e2e/models/andromede-v1/test_andromede_v1_models.py](./tests/e2e/models/andromede-v1/test_andromede_v1_models.py).

## Link with Antares Simulator software
This Python software package forms part of the Antares project, but its implementation is completely independent of that of the AntaresSimulator software. Although it was initially designed to prototype the next features of the Antares software (for more information, see https://antares-simulator.readthedocs.io/en/latest/user-guide/modeler/01-overview-modeler/), its structuring and development practices have resulted in high-quality, self-supporting code. It is currently maintained to offer the flexibility of the designed modeling language and interpreter to Python users and to continue exploring its potential.