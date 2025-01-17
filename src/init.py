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

    return '''BenchmarkMetaData
{{
    binary {ba_path}/hyteg-build/apps/nlDiffusion/nlDiffusionExample;
}}

Parameters
{{
    vtk true;
    vtk_output {ba_plot_path}/benchmarks/{suiteName}/vtk;

    minLevel 2;
    maxLevel 4;
    meshNx 2;
    meshNy 2;
    meshFlavour criss;

    solver mg;
    preSmoothSteps 3;
    postSmoothSteps 3;
    cycleType v;
    mgMaxIter 30;
    mgTolerance 1e-10;

    smoother chebyshev;
    chebyshevOrder 5;

    coarseGridSolver gmres;
    gmresMaxIter 600;
    gmresRestartLength 40;

    restriction linear;
    prolongation linear;
}}'''.format(suiteName=suiteName, ba_path=ba_path, ba_plot_path=ba_plot_path)


def init_suite():
    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')

    if env is None:
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set")
    elif env != "laptop" and env != "fritz":
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set to 'laptop' or 'fritz'")

    name = input("Enter suite name: ")

    if name == '':
        print(f"invalid suite name: {name}")
        return

    os.makedirs(os.path.join(os.getcwd(), 'benchmarks', name), exist_ok=True)

    with open(os.path.join(os.getcwd(), 'benchmarks', name, 'Parameters.prm'), 'w') as f:
        f.write(init_default_prm_file(name))

    prep_fresh_directory(os.path.join(os.getcwd(), 'benchmarks', name))
