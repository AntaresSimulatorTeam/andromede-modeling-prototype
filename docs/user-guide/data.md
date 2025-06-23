# Data series

Data series needed by the [system description](systems.md) to define component parameter values are defined in dedicated input files. Currently, the framework supports defining data-series using tab-seperated-values files. Values must be separated using tabs, and the character `.` represents the floating point. 

More performant data file formats will be available in future releases.

### Naming

TSV files inside the directory should respect the "XXX.tsv" or the "XXX.csv" naming template, where "XXX" is the ID of
the data-series. Thus, this ID **must be unique**, and is the one to be used in the [system file](systems.md).

### Time-dependent series

To define a time-dependent series, define a column vector, where every timestamp is represented by a row.  
Example file for a simulation with 6 timestamps:

~~~
10
15
34
56
34
65
~~~

Note that current Python interpreter package does not conduct quality checks on data-series, and that it is up to you to ensure
that the rows cover the time horizon of the simulation.

### Scenario-dependent series

To define a parameter value that changes depending on the scenario, define a row vector, where every data set is
represented by a column. Example file for a simulation with 4 scenarios:

~~~
54 67.5 23.652 253
~~~

### Time and scenario-dependent series

Use the two methods described above.  
Example file for a simulation with 2 timestamps and 3 scenarios:

~~~
2345 1243 123
2378 748  0
~~~