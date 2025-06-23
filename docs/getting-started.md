# Getting started with Gems

## Example of library file
TBD

## Example of system file
TBD

## Example of timeseries file
TBD

# Getting started with pyGems

## Installation

You can directly clone the [GitHub repo](https://github.com/AntaresSimulatorTeam/pyGems) of the project.

## Interpretation and simulation with pyGems

Here is an example of how to load component and library files, resolve the system, and solve the optimisation problem using the ***pyGems*** package.

### Loading the library, the system and the timeseries:

Here is the pyGems syntax to read a test case described by

-  A library of models: "simple_library.yml"
-  A system file: "system_example.yml"
-  A set of timeseries located in the directory: series_dir.

~~~ python
with open("system_example.yml") as compo_file:
    input_system = parse_yaml_components(compo_file)

with open("simple_library.yml") as lib_file:
    input_libraries = [parse_yaml_library(lib_file)]

result_lib = resolve_library(input_libraries)
components_input = resolve_system(input_system, result_lib)
database = build_data_base(input_system, Path(series_dir))
~~~

### Building the optimisation problem



~~~ python

network = build_network(components_input)

problem = build_problem(
    network,
    database,
    TimeBlock(1, [i for i in range(0, timespan)]),
    scenarios,
)
~~~

### Solving the optimisation problem
~~~ python
status = problem.solver.Solve()
print(problem.solver.Objective().Value())
~~~
