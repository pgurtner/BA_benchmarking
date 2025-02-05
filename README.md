# todo

* check if benchmark suite exists before creating files (probably via prep_dir)

## priority

* improve option to plot all benchmarks?
    * add option to plot all benchmarks in one file
* put multiple benchmarks next to each other in a file

`python3 main.py plot benchmarks/mg_small_grid --metrics=r_l2 `

## normal

* prevent runtime errors when benchmark and metric lists are empty
* fix --show (doesn't block currently, i.e. instantly closes)
* use separate waiting times for job-is-admitted and job-is-running
* "slurm_load_jobs error: Invalid job id specified" occurred after long waiting times

## idea

* add remote benchmark suites (that are executed i.e. on fritz)
* add init profiles (i.e. one for ng 2d, ng 3d, etc)

# documentation

Create a benchmark suite with `python3 main.py init`. Then see
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

## parameter files
out of date
```
BenchmarkMetaData{
    binary {ba_path}/hyteg-build/apps/nlDiffusion/nlDiffusionExample;
    tasks 6;
}

Parameters{
    vtk false;
    vtk_output {ba_plot_path}/benchmarks/{suiteName}/vtk;

    minLevel 2;
    maxLevel 5;
    [
      meshFile 3D/cube_6el.msh;
        or
      meshX <x>;
      meshY <y>;
      meshZ <z>;
    ]
    maxNGIterations 20;

    solver mg;
        preSmoothSteps 2;
        postSmoothSteps 1;
        smoothStepsIncreaseOnCoarserGrids 0;
        cycleType v;
        [
          mgMaxIter 30; 
            or
          mgDynamicMaxIterStart <i>;
        ]
        mgTolerance 1e-13;

        smoother chebyshev;
            chebyshevOrder 5;
            chebyshevSpectralRadiusEstMaxIter 100;
    
        coarseGridSolver cg;
            cgMaxIter 256;
    
        restriction linear;
        prolongation linear;

    logOuterBenchmarks true;
    logOuterTests false;
    logOuterMisc false;
    logInnerBenchmarks true;
    logInnerTests false;
    logInnerMisc false;
}```