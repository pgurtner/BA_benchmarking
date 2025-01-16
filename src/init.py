import os


def prep_fresh_directory(target_dir: str):
    os.makedirs(os.path.join(target_dir, "matplots"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "vtk"), exist_ok=True)


def init_default_prm_file(suiteName: str) -> str:
    return '''BenchmarkMetaData
{{
    binary /home/pg/Documents/uni/bachelor/fs7/Bachelorarbeit/hyteg-build/apps/nlDiffusion/nlDiffusionExample;
}}

Parameters
{{
    vtk true;
    vtk_output /home/pg/Documents/uni/bachelor/fs7/Bachelorarbeit/benchmarks/benchmarkPlotting/benchmarks/{suiteName}/vtk;

    minLevel 2;
    maxLevel 4;
    meshNx 2;
    meshNy 2;

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
}}'''.format(suiteName=suiteName)


def init_suite():
    name = input("Enter suite name: ")

    if name == '':
        print(f"invalid suite name: {name}")
        return

    os.makedirs(os.path.join(os.getcwd(), 'benchmarks', name), exist_ok=True)

    with open(os.path.join(os.getcwd(), 'benchmarks', name, 'Parameters.prm'), 'w') as f:
        f.write(init_default_prm_file(name))

    prep_fresh_directory(os.path.join(os.getcwd(), 'benchmarks', name))
