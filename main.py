import argparse
import os
from functools import reduce

from src.compare import compare_existing_logs
from src.extract import extract_benchmarks
from src.run import run
from src.utils import GridConfig, build_run_filename, extract_info_from_run_filename, build_std_plot_filename, \
    list_flatten
from src.plot import Plot


def main():
    parser = argparse.ArgumentParser(prog='benchmarking-utilities')

    subparsers = parser.add_subparsers(dest='command')

    run_parser = subparsers.add_parser('run')
    add_run_args(run_parser)

    plot_parser = subparsers.add_parser('plot')
    plot_parser.add_argument("file", help="which file to plot", type=str)
    add_common_plot_args(plot_parser)

    benchmark_parser = subparsers.add_parser('benchmark')
    add_run_args(benchmark_parser)
    add_common_plot_args(benchmark_parser)

    compare_parser = subparsers.add_parser('compare')
    compare_parser.add_argument("files", help="which files to compare", type=str, nargs='+')
    add_common_plot_args(compare_parser)

    args = parser.parse_args()

    if args.command == 'run':
        file = os.path.abspath(args.file)
        meshNx = int(args.meshNx)
        meshNy = int(args.meshNy)
        minLevel = int(args.minLevel)
        maxLevel = int(args.maxLevel)
        solver = args.solver
        tasks = int(args.tasks)

        run(file, solver, tasks, GridConfig(meshNx, meshNy, minLevel, maxLevel))


    elif args.command == 'plot':
        file = os.path.abspath(args.file)
        wanted_benchmarks = args.benchmarks.split(',')
        wanted_metrics = args.metrics.split(',')
        show = bool(args.show)

        std_plot(file, wanted_benchmarks, wanted_metrics, show)


    elif args.command == 'benchmark':
        file = os.path.abspath(args.file)
        meshNx = int(args.meshNx)
        meshNy = int(args.meshNy)
        minLevel = int(args.minLevel)
        maxLevel = int(args.maxLevel)
        solver = args.solver
        tasks = int(args.tasks)
        wanted_benchmarks = args.benchmarks.split(',')
        wanted_metrics = args.metrics.split(',')
        show = bool(args.show)

        grid_config = GridConfig(meshNx, meshNy, minLevel, maxLevel)

        run(file, solver, tasks, grid_config)

        run_log_name = build_run_filename(solver, grid_config)
        run_log_path = os.path.join(os.getcwd(), 'runs', run_log_name)

        std_plot(run_log_path, wanted_benchmarks, wanted_metrics, show)

    elif args.command == 'compare':
        files = map(lambda f: os.path.abspath(f), args.files)
        wanted_benchmarks = args.benchmarks.split(',')
        wanted_metrics = args.metrics.split(',')
        show = bool(args.show)

        compare_existing_logs(list(files), wanted_benchmarks, wanted_metrics, show)


def add_run_args(parser):
    parser.add_argument("file", help="which file to run")
    parser.add_argument("meshNx")
    parser.add_argument("meshNy")
    parser.add_argument("minLevel")
    parser.add_argument("maxLevel")
    parser.add_argument('solver', help="which solver to use")
    parser.add_argument("--tasks", help="number of mpi threads", type=int, default=1)


def add_common_plot_args(parser):
    parser.add_argument("--benchmarks", help="which benchmarks to plot", required=True)
    parser.add_argument("--metrics", help="which metrics to plot", default='max_norm')
    parser.add_argument("--show", help="whether to show the plot", action="store_true")

def std_plot (file: str, wanted_benchmarks: list[str], wanted_metrics: list[str], show: bool):
    # todo this doesnt belong in main
    solver, grid_config = extract_info_from_run_filename(file)

    benchmarks = extract_benchmarks(file, wanted_metrics, wanted_benchmarks)
    graphs = map(lambda b: b.to_graphs(), benchmarks)
    graphs = list_flatten(graphs)

    output_filename = build_std_plot_filename(solver, grid_config, wanted_benchmarks, wanted_metrics)
    output_filepath = os.path.join(os.getcwd(), 'plots_single', output_filename)

    plot = Plot(list(graphs), output_filename, reduce(lambda s, m: f"{s},{m}", wanted_metrics))

    plot.save(output_filepath)

    if show:
        plot.show()

if __name__ == "__main__":
    main()
