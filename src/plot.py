import operator
import os
from functools import reduce

import matplotlib.pyplot as plt
from enum import Enum

from matplotlib.figure import Figure

from src.extract import extract_benchmarks, restrict_benchmarks
from src.utils import Graph, RUN_LOG_FILE_NAME, list_flatten, build_std_plot_filename


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

    def save(self, filepath: str):
        if self._plt is None:
            self._plt = self._create_plot()

        self._plt.savefig(filepath)

    def _create_plot(self) -> Figure:
        plot = plt.figure()

        # origin_x = self.axis_dims[0]
        # origin_y = self.axis_dims[2]
        # width = self.axis_dims[1] - self.axis_dims[0]
        # height = self.axis_dims[3] - self.axis_dims[2]
        # axes = plot.add_axes(origin_x, origin_y, width, height)
        axes = plot.add_subplot()

        axes.set_title(self.title)
        axes.set_xlabel(self.xlabel)
        axes.set_ylabel(self.ylabel)
        axes.set_xscale(self.axis_types[0].value)
        axes.set_yscale(self.axis_types[1].value)
        axes.grid(visible=True)

        colors = iter(('b', 'g', 'r', 'c', 'm', 'y', 'k'))
        markers = iter(('.', 's', 'p', 'P', '*', 'h', 'o', '^', '<', '>', '1', '2', '3', '4', '8', '+', 'x', 'X', 'D'))
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


def std_plot(target_dir: str, wanted_benchmarks: list[str] | None, wanted_metrics: list[str] | None,
             show: bool = False):
    run_log_path = os.path.join(target_dir, RUN_LOG_FILE_NAME)
    if not os.path.isfile(run_log_path):
        print(f"{target_dir} misses run log, first run the program before trying to plot its benchmarks")
        return

    benchmarks = extract_benchmarks(target_dir)
    benchmarks = restrict_benchmarks(benchmarks, wanted_benchmarks, wanted_metrics)

    ylabel = 'all'
    if wanted_metrics is not None:
        ylabel = reduce(lambda s, m: f"{s},{m}", wanted_metrics)

    if wanted_benchmarks is None:
        for b in benchmarks:
            graphs = b.to_graphs()
            output_filename = build_std_plot_filename([b.decl.name], wanted_metrics)
            output_filepath = os.path.join(target_dir, 'matplots', output_filename)

            plot = Plot(list(graphs), output_filename, ylabel)
            plot.save(output_filepath)
    else:
        graph_blocks = map(lambda b: b.to_graphs(), benchmarks)
        output_filename = build_std_plot_filename(wanted_benchmarks, wanted_metrics)
        output_filepath = os.path.join(target_dir, 'matplots', output_filename)
        graphs = list_flatten(graph_blocks)
        plot = Plot(list(graphs), output_filename, ylabel)
        plot.save(output_filepath)

    # if show:
    #     plot.show()
