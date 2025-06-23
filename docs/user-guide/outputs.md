# Outputs: retrieving outputs with pyGems


Once the optimization problem was built and solved, one can retrieve the results as follows:

~~~ python
problem.solver.Solve()
results = OutputValues(problem)
~~~


Reading the timeseries of the optimization variable ''var_id'' of component "component_id" reads:

~~~ python
var_timeseries = results.component(component_id).var(var_id).value
~~~