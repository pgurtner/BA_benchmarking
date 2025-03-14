import operator
import os
from functools import reduce

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
from enum import Enum

from matplotlib.figure import Figure

from src.extract import extract_benchmarks, restrict_benchmarks
from src.utils import Graph, list_flatten, build_std_plot_filename, BenchmarkIterator, find_single_prm_file, \
    load_prm_file, build_run_log_filename

import logging

_logger = logging.getLogger(__name__)


class PlotAxisType(Enum):
    LINEAR = 'linear'
    LOGARITHMIC = 'log'


class Plot:
    title: str
    xlabel: str
    ylabel: str

    axis_dims: tuple[int, int, float, float]
    axis_types: tuple[PlotAxisType, PlotAxisType]

    graphs: list[Graph]

    _plt: Figure | None

    def __init__(self, graphs: list[Graph], title: str, ylabel: str, xlabel: str = "iterations",
                 axis_dims: tuple[int, int, float, float] = None,
                 axis_types: tuple[PlotAxisType, PlotAxisType] = (PlotAxisType.LINEAR,
                                                                  PlotAxisType.LOGARITHMIC)):
        self.graphs = graphs
        self.title = title
        self.ylabel = ylabel
        self.xlabel = xlabel

        if axis_dims is None:
            all_points = reduce(operator.concat, map(lambda g: g.points, graphs))
            all_x_coords = list(map(lambda p: p.x, all_points))
            all_y_coords = list(map(lambda p: p.y, all_points))

            min_x = min(all_x_coords)
            min_y = min(all_y_coords)
            max_x = max(all_x_coords)
            max_y = max(all_y_coords)

            self.axis_dims = (min_x, max_x, min_y, max_y)

        self.axis_types = axis_types

        self._plt = None

    def show(self):
        if self._plt is None:
            self._plt = self._create_plot()

        self._plt.show()

    def save_and_close(self, filepath: str):
        if self._plt is None:
            self._plt = self._create_plot()

        self._plt.savefig(filepath)
        plt.close(self._plt)

    def _create_plot(self) -> Figure:
        plot = plt.figure()

        axes = plot.add_subplot()

        axes.set_title(self.title)
        axes.set_xlabel(self.xlabel)
        axes.set_ylabel(self.ylabel)
        axes.set_xscale(self.axis_types[0].value)
        axes.set_yscale(self.axis_types[1].value)
        axes.grid(visible=True)

        colors = iter(mcolors.TABLEAU_COLORS.keys())
        markers = iter(
            Line2D.markers.keys())
        next(markers)
        next(markers)  # skip plain pixel

        for graph in self.graphs:
            xpoints = []
            ypoints = []
            for point in graph.points:  # todo very imperative
                xpoints.append(point.x)
                ypoints.append(point.y)

            label = None
            if len(self.graphs) > 1:
                label = graph.label

            axes.plot(xpoints, ypoints, marker=next(markers), label=label, color=next(colors))

        xticks = axes.get_xticks()
        int_xticks = map(int, xticks)
        positiv_int_xticks = filter(lambda t: t >= 0, int_xticks)
        axes.set_xticks(list(positiv_int_xticks))

        if len(self.graphs) > 1:
            plt.legend()

        return plot

    def create_plot_script(self, output_filepath: str) -> str:
        add_graphs_template = """
xpoints = {xpoints}
ypoints = {ypoints}
axes.plot(xpoints, ypoints{label}, marker=next(markers), color=next(colors))"""

        add_graphs_snippet = ''
        for graph in self.graphs:
            xpoints = []
            ypoints = []
            for point in graph.points:
                xpoints.append(point.x)
                ypoints.append(point.y)

            label = ""
            if len(self.graphs) > 1:
                label = f', label="{graph.label}"'
            add_graphs_snippet += add_graphs_template.format(xpoints=xpoints, ypoints=ypoints, label=label) + '\n'

        template = """
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

plot = plt.figure()

axes = plot.add_subplot()

axes.set_title("{title}")
axes.set_xlabel("{xlabel}")
axes.set_ylabel("{ylabel}")
axes.set_xscale("{xscale}")
axes.set_yscale("{yscale}")
axes.grid(visible=True)

colors = iter(mcolors.TABLEAU_COLORS.keys())
markers = iter(Line2D.markers.keys())
next(markers)
next(markers)  # skip plain pixel

{add_graphs}

# force xticks to be integers
xticks = axes.get_xticks()
int_xticks = map(int, xticks)
positiv_int_xticks = filter(lambda t: t >= 0, int_xticks)
axes.set_xticks(list(positiv_int_xticks))

{plot_legend}

plot.savefig("{output_filepath}")"""
        plot_legend = ""
        if len(self.graphs) > 1:
            plot_legend = "plt.legend()"

        return template.format(add_graphs=add_graphs_snippet, title=self.title, xlabel=self.xlabel, ylabel=self.ylabel,
                               xscale=self.axis_types[0].value, yscale=self.axis_types[1].value,
                               plot_legend=plot_legend, output_filepath=output_filepath)


# todo output writing has code duplication
def std_plot(target_dir: str, wanted_benchmarks: list[str] | None, wanted_metrics: list[str] | None,
             show: bool = False, format: str = 'std'):
    benchmark_iter = BenchmarkIterator(target_dir)

    for benchmark_dir in benchmark_iter:
        prm = load_prm_file(benchmark_dir)
        if "BenchmarkMetaData" not in prm or "repeat" not in prm["BenchmarkMetaData"]:
            raise ValueError(f"config of {benchmark_dir} does not contain a repeat value")

        repetitions_amount = int(prm["BenchmarkMetaData"]["repeat"])

        for i in range(repetitions_amount):
            run_log_path = os.path.join(benchmark_dir, build_run_log_filename(i))
            if not os.path.isfile(run_log_path):
                _logger.error(
                    f"{benchmark_dir} misses run log index {i}, first run the program before trying to plot its benchmarks")

                return

        benchmarks = extract_benchmarks(benchmark_dir)
        benchmarks = restrict_benchmarks(benchmarks, wanted_benchmarks, wanted_metrics)

        ylabel = 'all'
        if wanted_metrics is not None:
            ylabel = reduce(lambda s, m: f"{s},{m}", wanted_metrics)

        if wanted_benchmarks is None:
            for b in benchmarks:
                graphs = b.to_graphs()
                output_filename = build_std_plot_filename([b.decl.name], wanted_metrics)
                output_filepath = os.path.join(benchmark_dir, 'matplots', output_filename)

                plot = Plot(list(graphs), output_filename, ylabel)

                if format == 'std':
                    plot.save_and_close(output_filepath)
                elif format == 'script':
                    script = plot.create_plot_script(output_filepath)
                    with open(output_filepath + '.py', 'w') as f:
                        f.write(script)

        else:
            graph_blocks = map(lambda b: b.to_graphs(), benchmarks)
            output_filename = build_std_plot_filename(wanted_benchmarks, wanted_metrics)
            output_filepath = os.path.join(benchmark_dir, 'matplots', output_filename)
            graphs = list_flatten(graph_blocks)
            plot = Plot(list(graphs), output_filename, ylabel)

            if format == 'std':
                plot.save_and_close(output_filepath)
            elif format == 'script':
                script = plot.create_plot_script(output_filepath)
                with open(output_filepath + '.py', 'w') as f:
                    f.write(script)

        # if show:
        #   plot.show
