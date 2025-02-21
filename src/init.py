import os


def prep_fresh_directory(target_dir: str):
    os.makedirs(os.path.join(target_dir, "matplots"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "vtk"), exist_ok=True)


def init_default_prm_file(suiteName: str) -> str:
    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')
    if env == "laptop":
        ba_path = os.path.join('/', 'home', 'pg', 'Documents', 'uni', 'bachelor', 'fs7', 'Bachelorarbeit')
        ba_plot_path = os.path.join(ba_path, 'benchmarks', 'benchmarkPlotting')
    elif env == "fritz":
        ba_path = os.path.join('/', 'home', 'hpc', 'iwia', 'iwia123h')
        ba_plot_path = os.path.join(ba_path, 'BA_benchmarking')
    else:
        raise ValueError(f"BA_BENCHMARKING_UTILITIES_ENV has invalid value {env}")

    # todo this enforces Unix file paths
    return '''BenchmarkMetaData
{{
    binary {ba_path}/hyteg-build/apps/nlDiffusion/nlDiffusionExample;
    tasks 1;
}}

Parameters
{{
    vtk false;
    vtk_output {ba_plot_path}/{suiteName}/vtk;

    minLevel 2;
    maxLevel 5;
    meshFile 3D/cube_6el.msh;
    maxNGIterations 20;
    initialGuessType constant;
    initialGuessValue 0;

    ngOperator symmetric;

    solver mg;
        preSmoothSteps 2;
        postSmoothSteps 1;
        smoothStepsIncreaseOnCoarserGrids 0;
        cycleType v;
        mgMaxIter 30;
        mgTolerance 1e-14;
        mgInitialGuessType constant;
        mgInitialGuessValue 0;

        smoother chebyshev;
            chebyshevOrder 2;
            chebyshevSpectralRadiusEstMaxIter 20;
    
        coarseGridSolver direct;
    
        restriction linear;
        prolongation linear;

    logOuterBenchmarks true;
    logOuterTests false;
    logOuterMisc false;
    logInnerBenchmarks true;
    logInnerTests false;
    logInnerMisc false;
}}'''.format(suiteName=suiteName, ba_path=ba_path, ba_plot_path=ba_plot_path)


def init_suite(name: str):
    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')

    if env is None:
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set")
    elif env != "laptop" and env != "fritz":
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set to 'laptop' or 'fritz'")

    if name == '':
        raise ValueError(f"invalid suite name: {name}")

    suite_path = os.path.join(os.getcwd(), name)

    os.makedirs(suite_path, exist_ok=True)

    with open(os.path.join(suite_path, 'Parameters.prm'), 'w') as f:
        f.write(init_default_prm_file(name))

    prep_fresh_directory(suite_path)
