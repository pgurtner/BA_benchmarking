import argparse
import os
from pathlib import PurePath

from src.compare import compare_existing_logs
from src.config import create_config, set_configs
from src.meshgen import calculate_3d_mesh_config
from src.run import run
from src.plot import std_plot
from src.move import move_benchmark_folders

import logging

from src.utils import BenchmarkIterator, load_prm_file, build_run_log_filename

_logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(prog='benchmarking-utilities')

    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run')
    add_run_args(run_parser)

    plot_parser = subparsers.add_parser('plot')
    plot_parser.add_argument("dir", help="which benchmark directory to plot", type=str)
    add_common_plot_args(plot_parser)

    benchmark_parser = subparsers.add_parser('benchmark')
    add_run_args(benchmark_parser)
    add_common_plot_args(benchmark_parser)

    compare_parser = subparsers.add_parser('compare')
    compare_parser.add_argument("dirs", help="which benchmark directories to compare", type=str, nargs='+')
    add_common_plot_args(compare_parser)

    config_parser = subparsers.add_parser('config')
    config_parser.add_argument("suite_name", help="name of the benchmark suite", type=str)
    config_parser.add_argument("--create", action='store_true',
                               help="create the config along with the benchmark suite directories, implies --set-defaults")
    config_parser.add_argument("--set-defaults", action='store_true', help="sets the configs to the default config")
    config_parser.add_argument("--add-missing-defaults", action='store_true',
                               help="sets missing values to their default")
    config_parser.add_argument("--assignments", nargs='*',
                               help="<Block>.<field>=<value>, for non-default updates")

    meshgen_parser = subparsers.add_parser('meshgen')
    meshgen_parser.add_argument("total_tets", help="total number of tets", type=int)
    meshgen_parser.add_argument("tets_per_thread", help="number of tets per thread", type=int, default=1)
    meshgen_parser.add_argument("--tets-per-block", help="number of tets per block", type=int, default=6)

    move_parser = subparsers.add_parser("move")
    move_parser.add_argument("from_loc", help="old benchmark file location")
    move_parser.add_argument("to", help="new benchmark file location")

    args = parser.parse_args()

    # todo this is ignored
    #   find a good way to add logging to this entire project
    # _logger.info(args)

    if args.command == 'run':
        target_dirs = list(map(os.path.abspath, args.dirs))
        multicore = bool(args.m)

        run(target_dirs, multicore)


    elif args.command == 'plot':
        exec_plot_command(args)

    elif args.command == 'benchmark':
        target_dirs = list(map(os.path.abspath, args.dirs))
        multicore = bool(args.m)
        run(target_dirs, multicore)

        exec_plot_command(args)

    elif args.command == 'compare':
        target_dirs = map(lambda f: os.path.abspath(f), args.dirs)
        wanted_benchmarks = args.benchmarks.split(',')
        wanted_metrics = args.metrics.split(',')
        show = bool(args.show)
        format = 'std'
        if args.format is not None:
            assert args.format in ['std', 'script']
            format = args.format

        x_axis = "iterations"
        if args.x_axis is not None:
            x_axis = args.x_axis
        y_axis = None
        if args.y_axis is not None:
            y_axis = args.y_axis.split(',')

        x_axis_label = None
        if args.x_axis_label is not None:
            x_axis_label = args.x_axis_label

        y_axis_label = None
        if args.y_axis_label is not None:
            y_axis_label = args.y_axis_label

        plot_title = None
        if args.plot_title is not None:
            plot_title = args.plot_title

        compare_existing_logs(list(target_dirs), wanted_benchmarks, wanted_metrics, show, format, x_axis, y_axis,
                              x_axis_label, y_axis_label, plot_title)

    elif args.command == 'config':
        name = args.suite_name
        create = bool(args.create)
        set_defaults = bool(args.set_defaults)
        add_missing_defaults = bool(args.add_missing_defaults)
        assignments = []

        if args.assignments is not None:
            assignments = args.assignments

        if create:
            create_config(name, assignments)
        else:
            set_configs(name, assignments, set_defaults, add_missing_defaults)

    elif args.command == 'meshgen':
        total_tets = int(args.total_tets)
        tets_per_thread = int(args.tets_per_thread)
        tets_per_block = int(args.tets_per_block)

        config = calculate_3d_mesh_config(total_tets * tets_per_thread, tets_per_block)
        print(config)
    elif args.command == 'move':
        from_loc = os.path.abspath(args.from_loc)
        to = os.path.abspath(args.to)

        assert os.path.isdir(from_loc)

        p = PurePath(to)
        assert not p.is_relative_to(from_loc), "can't move directories inside themselves"

        move_benchmark_folders(from_loc, to)


def add_run_args(parser):
    parser.add_argument("dirs", help="which benchmark directories to run", nargs='+')
    parser.add_argument("-m", help="allow running jobs on multiple cores", action="store_true", default=False)


def add_common_plot_args(parser):
    parser.add_argument("--for-each",
                        help="plot these benchmarks separately, equivalent to just calling plot individually; can't be used with --benchmarks")
    parser.add_argument("--benchmarks", help="which benchmarks to plot")
    parser.add_argument("--metrics", help="which metrics to plot")
    parser.add_argument("--format", help="output format, std | script", type=str)
    parser.add_argument("--show", help="whether to show the plot", action="store_true")

    parser.add_argument("--x-axis", help="one of the chosen metrics or iterations by default", type=str)
    parser.add_argument("--y-axis", help="subset of the chosen metrics or all by default", type=str)
    parser.add_argument("--x-axis-label", type=str)
    parser.add_argument("--y-axis-label", type=str)
    parser.add_argument("--plot-title", type=str)


def exec_plot_command(args):
    format = 'std'
    if args.format is not None:
        assert args.format in ['std', 'script']
        format = args.format

    target_dir = os.path.abspath(args.dir)
    wanted_metrics = None
    if args.metrics is not None:
        wanted_metrics = args.metrics.split(',')
    show = bool(args.show)

    if args.for_each is not None and args.benchmarks is not None:
        _logger.error("exactly one of --for-each or --benchmarks should be specified")
        exit(1)

    if args.for_each is None and args.benchmarks is None:
        std_plot(target_dir, None, wanted_metrics, show, format)
    elif args.for_each is not None:

        benchmarks = args.for_each.split(',')
        for b in benchmarks:
            std_plot(target_dir, [b], wanted_metrics, show, format)
    else:
        wanted_benchmarks = args.benchmarks.split(',')
        std_plot(target_dir, wanted_benchmarks, wanted_metrics, show, format)


if __name__ == "__main__":
    # @dataclass
    # class Config:
    #     dir = './benchmarks/mg_small_grid'
    #     metrics = 'r_l2'
    #     show = False
    #     for_each = None
    #     benchmarks = 'NG_mg'
    #
    # exec_plot_command(Config())

    # compare_existing_logs(['./benchmarks/fritz/newton_galerkin/3D/mg_dynamic_iterations',
    #                        './benchmarks/fritz/newton_galerkin/3D/mg_dynamic_large'], ['NG_mg'], ['r_l2'], False)

    # run(["./benchmarks/newton_galerkin/3D/symmetric/optimizations"], True)

    # bcompare  --benchmarks=NG_mg --metrics=r_l2 --format=script
    # compare_existing_logs(["./benchmarks/fritz/newton_galerkin/3D/symmetric/optimizations/cycle_type/mg_v_cycles",
    #                        "./benchmarks/fritz/newton_galerkin/3D/symmetric/optimizations/cycle_type/mg_w_cycles/"],
    #                       ['NG_mg'], ['r_l2'], False)

    main()

    # biter = BenchmarkIterator(["./benchmarks/newton_galerkin/3D/symmetric/optimizations"])

    # for b in biter:
    #     prm = load_prm_file(b)

    #     assert prm["BenchmarkMetaData"]["tasks"] == "72", b
    #     assert prm["BenchmarkMetaData"]["repeat"] == "5"
    #     assert prm["BenchmarkMetaData"]["reduce"] == "avg"
    #     assert prm["BenchmarkMetaData"]["binary"].startswith("/home/hpc/iwia/iwia123h")

    #     assert prm["FritzMetaParameters"]["frequency"] == "2000000"
    #     assert prm["FritzMetaParameters"]["pinThreads"] == "true"

    #     assert prm["Parameters"]["minLevel"] == "2"
    #     assert prm["Parameters"]["maxLevel"] == "6"
    #     assert prm["Parameters"]["meshX"] == "2"
    #     assert prm["Parameters"]["meshY"] == "2"
    #     assert prm["Parameters"]["meshZ"] == "3"
    #     assert prm["Parameters"]["maxNGIterations"] == "20"
    #     assert prm["Parameters"]["initialGuessType"] in ["random", "constant"]
    #     assert "initialGuessValue" in prm["Parameters"]
    #     assert prm["Parameters"]["ngOperator"] in ["symmetric", "normal", "mass_lumped"]
    #     assert prm["Parameters"]["solver"] in ["mg", "fmg"]
    #     assert "preSmoothSteps" in prm["Parameters"]
    #     assert "postSmoothSteps" in prm["Parameters"]
    #     assert "smoothStepsIncreaseOnCoarserGrids" in prm["Parameters"]
    #     assert prm["Parameters"]["cycleType"] in ["v", "w"]
    #     assert prm["Parameters"]["mgMaxIter"] == "200"
    #     assert prm["Parameters"]["mgToleranceType"] in ["constant", "linear", "quadratic"]
    #     assert "mgToleranceValue" in prm["Parameters"]
    #     assert prm["Parameters"]["mgInitialGuessType"] in ["random", "constant"]
    #     assert prm["Parameters"]["smoother"] == "chebyshev"
    #     assert prm["Parameters"]["chebyshevOrder"] in ["1", "2", "3", "4", "5"]
    #     assert "chebyshevSpectralRadiusEstMaxIter" in prm["Parameters"]
    #     assert prm["Parameters"]["coarseGridSolver"] in ["cg", "gmres"]
    #     assert prm["Parameters"]["gmresMaxIter"] == "600"
    #     assert prm["Parameters"]["gmresRestartLength"] == "40"
    #     assert prm["Parameters"]["restriction"] == "linear"
    #     assert prm["Parameters"]["prolongation"] == "linear"


#         repetitions = int(prm['BenchmarkMetaData']['repeat'])
#
#         for i in range(repetitions):
#             run_log_path = os.path.join(b, build_run_log_filename(i))
#             print("read " + run_log_path)
#
#             with open(run_log_path, 'a') as f:
#                 f.write("""[0][INFO    ]------(0.011 sec) #benchmark[NG_mg]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_0]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_1]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_2]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_3]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_4]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_5]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_6]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_7]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_8]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_9]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_10]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_11]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_12]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_13]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_14]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_15]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_16]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_17]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_18]: r_l2, r_max, d_l2, d_max, time
# [0][INFO    ]------(0.011 sec) #benchmark[NG_inner_mg_19]: r_l2, r_max, d_l2, d_max, time""")
