# Reading input files


## Loading the library, the system and the timeseries:



~~~ python
with open(systems_file_path) as compo_file:
    input_component = parse_yaml_components(compo_file)

with open(lib_file_path) as lib_file:
    input_libraries = [parse_yaml_library(lib_file)]

result_lib = resolve_library(input_libraries)
components_input = resolve_system(input_component, result_lib)
database = build_data_base(input_component, Path(series_dir))
~~~