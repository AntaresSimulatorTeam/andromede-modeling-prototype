# Optimization: building and solving problems with pyGems


### Building the optimization problem



~~~ python

network = build_network(components_input)

problem = build_problem(
    network,
    database,
    TimeBlock(1, [i for i in range(0, timespan)]),
    scenarios,
)
~~~

### Solving the optimization problem
~~~ python
status = problem.solver.Solve()
print(problem.solver.Objective().Value())
~~~
