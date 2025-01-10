# todo
## priority
 * rework benchmark parameter handling


## normal
 * prevent runtime errors when benchmark and metric lists are empty
 * test multiple benchmarks/metrics in one call
 * fix --show (doesnt block currently, i.e. instantly closes)
 * also iterate through graph dots, not just graph colors

# documentation
names can't contain dots, spaces and commas.
## benchmark declaration
`"#benchmark[" <name> "]:" (<metric name>("<"<metric value type = float>">")?)*`

e.g.
`#benchmark[NG_mg]: max_norm, acc_iterations<int>`

## measurement
`"@[" <benchmark name> "]:" <iteration> " " (<metric name> = <metric value>) (", "<metric name> = <metric value>)*`

e.g.
`@[NG_mg]:1 max_norm = 1.0e-5, acc_iterations = 100`