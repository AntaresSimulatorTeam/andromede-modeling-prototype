# Getting started

## Example of library file

## Example of system file

## Example of timeserie file


## Interpretation and simulation with pyGems

Here is an example of how to load component and library files, resolve the system, and solve the optimization problem using the ***pyGems*** package.

### Loading the library, the system and the timeseries:



<pre> with open(systems_file_path) as compo_file:
    input_component = parse_yaml_components(compo_file)

with open(lib_file_path) as lib_file:
    input_libraries = [parse_yaml_library(lib_file)]

result_lib = resolve_library(input_libraries)
components_input = resolve_system(input_component, result_lib)
database = build_data_base(input_component, Path(series_dir))
</pre> 


### Building the optimization problem



<pre>

network = build_network(components_input)

problem = build_problem(
    network,
    database,
    TimeBlock(1, [i for i in range(0, timespan)]),
    scenarios,
)
</pre>

### Solving the optimization problem
<pre>
status = problem.solver.Solve()
print(problem.solver.Objective().Value())
</pre>
