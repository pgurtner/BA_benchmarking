import operator
from dataclasses import dataclass
from functools import reduce

import matplotlib.pyplot as plt
from enum import Enum

from matplotlib.figure import Figure


class PlotAxisType(Enum):
    LINEAR = 'linear'
    LOGARITHMIC = 'log'


@dataclass
class Point2D:
    x: float
    y: float


@dataclass
class Graph:
    label: str
    points: list[Point2D]


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

        if len(self.graphs) > 1:
            plt.legend()

        return plot
