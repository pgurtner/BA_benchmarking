import os
from functools import reduce

from src.extract import extract_benchmarks, restrict_benchmarks
from src.utils import list_flatten, BenchmarkIterator
from src.plot import Plot


def compare_existing_logs(dirs: list[str], benchmarks: list[str], metrics: list[str], show: bool, format: str = 'std',
                          x_axis: str = "iterations", y_axis: list[str] | None = None, x_axis_name: str | None = None,
                          y_axis_name: str | None = None, plot_title: str | None = None) -> None:
    b_iter = BenchmarkIterator(dirs)
    extracted_benchmarks = map(lambda d: (d, extract_benchmarks(d)), b_iter)
    restricted_benchmarks = map(lambda b: (b[0], restrict_benchmarks(b[1], benchmarks, metrics)), extracted_benchmarks)
    suites = map(lambda b: (os.path.basename(b[0]), b[1]), restricted_benchmarks)
    suites = list(
        map(lambda s: (s[0], list_flatten(list(map(lambda benchmark: benchmark.to_graphs(x_axis, y_axis), s[1])))),
            suites))

    for suite_name, graphs in suites:
        for graph in graphs:
            graph.label = f"{suite_name}." + graph.label

    relabeled_graphs = list(map(lambda p: p[1], suites))
    graphs = list_flatten(relabeled_graphs)

    suite_names = list(map(lambda d: os.path.basename(d), dirs))
    benchmark_str = reduce(
        lambda s, b: f"{s},{b}", benchmarks)
    metrics_str = reduce(lambda s, m: f"{s},{m}",
                         metrics)
    # output_file_name = reduce(lambda s, f: f"{s}-vs-{f}", suite_names) + '.' + benchmark_str + '.' + metrics_str

    output_dir = os.path.commonpath(dirs)
    os.makedirs(os.path.join(output_dir, "comparisons"), exist_ok=True)

    a = os.listdir(os.path.join(output_dir, "comparisons"))
    output_file_name = str(len(a))

    if plot_title is None:
        plot_title = output_file_name

    if y_axis_name is None:
        y_axis_name = metrics_str

    plot = Plot(graphs, plot_title, y_axis_name, x_axis_name)

    output_filepath = os.path.join(output_dir, "comparisons", output_file_name + '.pdf')

    if format == 'std':
        plot.save_and_close(output_filepath)
    elif format == 'script':
        script = plot.create_plot_script(output_filepath)
        with open(output_filepath + '.py', 'w') as f:
            f.write(script)

    # if show:
    #     plot.show()
