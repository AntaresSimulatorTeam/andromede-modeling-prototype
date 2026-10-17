# Outputs: retrieving outputs with GemsPy

## Via `SimulationSession` (recommended)

`SimulationSession.run()` returns a `SimulationTable` directly after solving:

~~~ python
from pathlib import Path
from gems_craft.study.folder import load_study
from gems_runner.session import SimulationSession
from gems_craft.optim_config import load_optim_config

study = load_study(Path("my_study"))
optim_config = load_optim_config(Path("my_study/input/optim-config.yml"))

session = SimulationSession(study=study, optim_config=optim_config)
results = session.run()  # SimulationTable
~~~

## Via `SimulationTableBuilder` (low-level)

When using `build_problem()` directly, build the table from the solved problem:

~~~ python
from gems_runner.simulation.simulation_table import SimulationTableBuilder

results = SimulationTableBuilder().build(problem)
~~~

---

## Accessing results

`SimulationTable` exposes a fluent accessor API and a raw DataFrame.

### Fluent API

~~~ python
# All values for a component
component_view = results.component("gen_de")

# Pivot for a specific output variable
output_view = component_view.output("generation")

# Single value (single timestep, single scenario)
val = output_view.value(time_index=0, scenario_index=0)

# All timesteps for scenario 0
series = output_view.value(scenario_index=0)  # returns a pandas Series
~~~

### Raw DataFrame

~~~ python
df = results.data
~~~

The DataFrame has columns: `block`, `component`, `output`,
`absolute_time_index`, `block_time_index`, `scenario_index`, `value`, `basis_status`.

Reading the value of the optimisation variable `var_id` of component `component_id`
for a single time step and scenario:

~~~ python
value = df[(df["component"] == component_id) & (df["output"] == var_id)]["value"].iloc[0]
~~~

For multi-time or multi-scenario results, filter additionally by `block_time_index`
and `scenario_index`:

~~~ python
sub = df[(df["component"] == component_id) & (df["output"] == var_id)]
value_s0_t1 = sub[(sub["scenario_index"] == 0) & (sub["block_time_index"] == 1)]["value"].iloc[0]
~~~

---

## Saving and reopening results

~~~ python
from gems_craft.study.parsing import OutputFormat
from gems_runner.simulation import SimulationTable

results.save(Path("my_run"))                    # a table folder, in Parquet
results.save(Path("my_run_csv"), OutputFormat.CSV)
results = SimulationTable.open(Path("my_run"))  # reads it back, lazily
~~~

`save()` writes a folder with one file per scenario, a `scenario-common` file
for the rows shared by all scenarios, and a `manifest.json` written last. The
folder is created if missing and must be empty otherwise. Parquet files are
written with zstd compression (level 3) and row groups of 64,000 rows.

On a reopened table, `data` raises: use `to_pandas(load_all=True)`,
`to_pandas()` with filters, or `iter_scenarios()`.

`to_csv()`, `to_parquet()`, `to_dataset()` and `to_netcdf()` are deprecated and
will be removed in a following release: use `save()`, or build an xarray object
from `to_pandas()`.

### Choosing the output format from the CLI

`gemspy` writes the simulation table as CSV by default. Use `--output-format`
to write Parquet instead:

~~~ bash
gemspy --study path/to/study_dir --output-format parquet
~~~

The equivalent Python call is
`run_study(Path("path/to/study_dir"), output_format=OutputFormat.PARQUET)`,
with `OutputFormat` imported from `gems_craft.study.parsing`.
