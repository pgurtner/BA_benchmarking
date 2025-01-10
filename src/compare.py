import os
from functools import reduce

from src.extract import extract_benchmarks
from src.utils import list_flatten, extract_info_from_run_filename
from src.plot import Plot


def compare_existing_logs(files: list[str], benchmarks: list[str], metrics: list[str], show: bool):
    basenames = list(map(os.path.basename, files))
    log_configs = map(extract_info_from_run_filename, basenames)

    extracted_benchmarks = list_flatten(map(lambda f: extract_benchmarks(f, metrics, benchmarks), files))
    graphs_per_benchmark = map(lambda b: b.to_graphs(), extracted_benchmarks)
    config_graph_pairs = list(zip(log_configs, graphs_per_benchmark))

    for log_config, graphs in config_graph_pairs:
        solver, grid_config = log_config
        for graph in graphs:
            graph.label = f"{solver}.{grid_config}." + graph.label

    relabeled_graphs = map(lambda p: p[1], config_graph_pairs)
    graphs = list_flatten(relabeled_graphs)

    base_file_names = map(lambda f: os.path.splitext(f)[0], basenames)
    metrics_str = reduce(lambda s, b: f"{s},{b}",
                         metrics)
    output_file_name = reduce(lambda s, f: f"{s}-vs-{f}", base_file_names) + '.' + reduce(
        lambda s, m: f"{s},{m}", benchmarks) + '.' + metrics_str

    plot = Plot(graphs, output_file_name, metrics_str)

    output_filepath = os.path.join(os.getcwd(), "plots_comparison", output_file_name + '.pdf')

    plot.save(output_filepath)

    if show:
        plot.show()
