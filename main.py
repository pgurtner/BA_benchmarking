import argparse
import os
from pathlib import PurePath

from src.compare import compare_existing_logs
from src.init import prep_fresh_directory, init_suite
from src.meshgen import calculate_3d_mesh_config
from src.run import run
from src.plot import std_plot
from src.utils import clean_directory
from src.move import move_benchmark_folders


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

    init_parser = subparsers.add_parser('init')
    init_parser.add_argument("suite_name", help="name of the benchmark suite", type=str)

    meshgen_parser = subparsers.add_parser('meshgen')
    meshgen_parser.add_argument("total_tets", help="total number of tets", type=int)
    meshgen_parser.add_argument("tets_per_thread", help="number of tets per thread", type=int, default=1)
    meshgen_parser.add_argument("--tets-per-block", help="number of tets per block", type=int, default=6)

    move_parser = subparsers.add_parser("move")
    move_parser.add_argument("from_loc", help="old benchmark file location")
    move_parser.add_argument("to", help="new benchmark file location")

    args = parser.parse_args()

    if args.command == 'run':
        target_dir = os.path.abspath(args.dir)

        prep_fresh_directory(target_dir)
        clean_directory(os.path.join(target_dir, 'matplots'))
        clean_directory(os.path.join(target_dir, 'vtk'))

        run(target_dir)


    elif args.command == 'plot':
        exec_plot_command(args)

    elif args.command == 'benchmark':
        target_dir = os.path.abspath(args.dir)
        run(target_dir)

        exec_plot_command(args)

    elif args.command == 'compare':
        target_dirs = map(lambda f: os.path.abspath(f), args.dirs)
        wanted_benchmarks = args.benchmarks.split(',')
        wanted_metrics = args.metrics.split(',')
        show = bool(args.show)

        compare_existing_logs(list(target_dirs), wanted_benchmarks, wanted_metrics, show)

    elif args.command == 'init':
        name = args.suite_name
        init_suite(name)
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
    parser.add_argument("dir", help="which benchmark directory to run")


def add_common_plot_args(parser):
    parser.add_argument("--for-each",
                        help="plot these benchmarks separately, equivalent to just calling plot individually; can't be used with --benchmarks")
    parser.add_argument("--benchmarks", help="which benchmarks to plot")
    parser.add_argument("--metrics", help="which metrics to plot")
    parser.add_argument("--format", help="output format, std | script", type=str)
    parser.add_argument("--show", help="whether to show the plot", action="store_true")


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
        print("exactly one of --for-each or --benchmarks should be specified")
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

    main()
