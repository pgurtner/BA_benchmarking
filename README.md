# documentation
## benchmark declaration
`"#benchmark[" <name> "]:" (<metric name>("<"<metric value type = float>">")?)*`

e.g.
`#benchmark[NG mg]: max_norm, acc_iterations<int>`

## measurement
`"@[" <benchmark name> "]:" <iteration> " " (<metric name> = <metric value>) (", "<metric name> = <metric value>)*`

e.g.
`@[NG mg]:1 max_norm = 1.0e-5, acc_iterations = 100`