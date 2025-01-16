import argparse
import os
from functools import reduce

from src.compare import compare_existing_logs
from src.extract import extract_benchmarks
from src.init import prep_fresh_directory, init_suite
from src.run import run
from src.utils import build_std_plot_filename, list_flatten, RUN_LOG_FILE_NAME
from src.plot import Plot

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

    subparsers.add_parser('init')

    args = parser.parse_args()

    if args.command == 'run':
        target_dir = os.path.abspath(args.dir)
        tasks = int(args.tasks)

        prep_fresh_directory(target_dir)

        run(target_dir, tasks)


    elif args.command == 'plot':
        exec_plot_command(args)

    elif args.command == 'benchmark':
        target_dir = os.path.abspath(args.dir)
        tasks = int(args.tasks)
        run(target_dir, tasks)

        exec_plot_command(args)

    elif args.command == 'compare':
        target_dirs = map(lambda f: os.path.abspath(f), args.dirs)
        wanted_benchmarks = args.benchmarks.split(',')
        wanted_metrics = args.metrics.split(',')
        show = bool(args.show)

        compare_existing_logs(list(target_dirs), wanted_benchmarks, wanted_metrics, show)

    elif args.command == 'init':
        init_suite()


def add_run_args(parser):
    parser.add_argument("dir", help="which benchmark directory to run")
    parser.add_argument("--tasks", help="number of mpi threads", type=int, default=1)


def add_common_plot_args(parser):
    parser.add_argument("--for-each",
                        help="plot these benchmarks separately, equivalent to just calling plot individually; can't be used with --benchmarks")
    parser.add_argument("--benchmarks", help="which benchmarks to plot")
    parser.add_argument("--metrics", help="which metrics to plot", required=True)
    parser.add_argument("--show", help="whether to show the plot", action="store_true")


def exec_plot_command(args):
    target_dir = os.path.abspath(args.dir)
    wanted_metrics = args.metrics.split(',')
    show = bool(args.show)

    if args.for_each is not None and args.benchmarks is not None or args.for_each is None and args.benchmarks is None:
        print("exactly one of --for-each or --benchmarks should be specified")
        exit(1)

    if args.for_each is not None:

        benchmarks = args.for_each.split(',')
        for b in benchmarks:
            std_plot(target_dir, [b], wanted_metrics, show)
    else:
        wanted_benchmarks = args.benchmarks.split(',')
        std_plot(target_dir, wanted_benchmarks, wanted_metrics, show)


def std_plot(target_dir: str, wanted_benchmarks: list[str], wanted_metrics: list[str], show: bool = False):
    # todo this doesnt belong in main

    run_log_path = os.path.join(target_dir, RUN_LOG_FILE_NAME)
    if not os.path.isfile(run_log_path):
        print(f"{target_dir} misses run log, first run the program before trying to plot its benchmarks")
        return

    benchmarks = extract_benchmarks(target_dir, wanted_metrics, wanted_benchmarks)
    graphs = map(lambda b: b.to_graphs(), benchmarks)
    graphs = list_flatten(graphs)

    output_filename = build_std_plot_filename(wanted_benchmarks, wanted_metrics)
    output_filepath = os.path.join(target_dir, 'matplots', output_filename)

    plot = Plot(list(graphs), output_filename, reduce(lambda s, m: f"{s},{m}", wanted_metrics))

    plot.save(output_filepath)

    if show:
        plot.show()


if __name__ == "__main__":
    # @dataclass
    # class Config:
    #     dir = './benchmarks/arbitrary_name'
    #     metrics = 'r_l2'
    #     show = False
    #     for_each = 'NG_mg,NG_inner_mg_0'
    #     benchmarks = None


    #exec_plot_command(Config())

    main()
