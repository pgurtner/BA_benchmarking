# todo

## priority
* add option to plot all benchmarks
* move plot functions out of main.py

## normal

* prevent runtime errors when benchmark and metric lists are empty
* fix --show (doesn't block currently, i.e. instantly closes)

# documentation

Create a benchmark suite in directory benchmarks, i.e. a directory with arbitrary name and a .prm file. Then see
`python3 main.py -h`
For the run functionality you have to set BA_BENCHMARKING_UTILITIES_ENV to "laptop" or "fritz" respectively depending on
the machine that'll run the benchmarks

names can't contain dots, spaces and commas.

## benchmark declaration

`"#benchmark[" <name> "]:" (<metric name>("<"<metric value type = float>">")?)*`

e.g.
`#benchmark[NG_mg]: max_norm, acc_iterations<int>`

## measurement

`"@[" <benchmark name> "]:" <iteration> " " (<metric name> = <metric value>) (", "<metric name> = <metric value>)*`

e.g.
`@[NG_mg]:1 max_norm = 1.0e-5, acc_iterations = 100`