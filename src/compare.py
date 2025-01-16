import os
from functools import reduce

from src.extract import extract_benchmarks
from src.utils import list_flatten
from src.plot import Plot


def compare_existing_logs(dirs: list[str], benchmarks: list[str], metrics: list[str], show: bool):
    suites = map(lambda d: (os.path.basename(d), extract_benchmarks(d, metrics, benchmarks)), dirs)
    suites = list(map(lambda s: (s[0], list_flatten(list(map(lambda benchmark: benchmark.to_graphs(), s[1])))), suites))

    for suite_name, graphs in suites:
        for graph in graphs:
            graph.label = f"{suite_name}." + graph.label

    relabeled_graphs = map(lambda p: p[1], suites)
    graphs = list_flatten(relabeled_graphs)

    suite_names = list(map(lambda d: os.path.basename(d), dirs))
    benchmark_str = reduce(
        lambda s, b: f"{s},{b}", benchmarks)
    metrics_str = reduce(lambda s, m: f"{s},{m}",
                         metrics)
    output_file_name = reduce(lambda s, f: f"{s}-vs-{f}", suite_names) + '.' + benchmark_str + '.' + metrics_str

    plot = Plot(graphs, output_file_name, metrics_str)

    output_filepath = os.path.join(os.getcwd(), "comparisons", output_file_name + '.pdf')

    plot.save(output_filepath)

    if show:
        plot.show()
