import operator
import os.path
import re
from dataclasses import dataclass
from functools import reduce

import matplotlib.pyplot as plt
from enum import Enum
import argparse, sys


class PlotAxisType(Enum):
    LINEAR = 1
    LOGARITHMIC = 2

@dataclass
class BenchmarkFile:
    # file basename without file extension
    name: str
    # plain file content
    contents: str

class Measurement:
    # type of solver, currently one of {direct, mg, fmg, gmres, gmresp}
    solver: str
    # outer Newton-Galerkin iteration of this measurement
    ng_iteration: int
    # accumulated iteration of inner solver
    acc_iteration: int
    # the actual metrics (usually norms) that make up the measurement
    metrics: list[tuple[str, str]]

    def __init__(self, solver, ng_iteration, acc_iteration, metrics):
        self.solver = solver
        self.ng_iteration = ng_iteration
        self.acc_iteration = acc_iteration
        self.metrics = metrics

    # restrict the stored metrics to the ones given in the argument
    def restrict_metrics(self, metrics: list[str]):
        self.metrics = list(filter(lambda m: m[0] in metrics, self.metrics))

    def __str__(self) -> str:
        return f"{self.solver} #{self.ng_iteration} acc:{self.acc_iteration} : {self.metrics}"

    def __repr__(self) -> str:
        return self.__str__()
        #return "FileMeasurement()"

class FileMeasurement:
    # same as BenchmarkFile.name
    filename: str
    # all measurements of file @filename
    measurements: list[Measurement]

    def __init__(self, filename, measurements):
        self.filename = filename
        self.measurements = measurements

    def restrict_metrics(self, metrics):
        for m in self.measurements:
            m.restrict_metrics(metrics)

    def __str__(self) -> str:
        return f"{self.filename}: {self.measurements}"

    def __repr__(self) -> str:
        return self.__str__()
        #return "FileMeasurement()"

@dataclass
class Point2D:
    x: float
    y: float

@dataclass
class Graph:
    metric: str
    points: list[Point2D]

def list_flatten(l):
    return [x for xs in l for x in xs]

#todo: naming for different types of measurements is a complete mess
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--metrics", help="comma separated list of metrics to plot", default="max_norm")
    parser.add_argument('files', nargs='+', help="files to plot")
    parser.add_argument("--show", help="display plot automatically", action="store_true")
    parser.add_argument("--inner-solver", help="plot metrics from inner solver", action="store_true")

    args = parser.parse_args()

    metrics = args.metrics.split(',')
    files = args.files
    show = args.show
    inner_solver = args.inner_solver

    plot_files(files, metrics, show, inner_solver)

def plot_files(filepaths: list[str], metrics: list[str], show: bool = False, inner_solver: bool = False) -> None:
    contents: list[BenchmarkFile] = []
    for filepath in filepaths:
        file = open(filepath, 'r')
        content: str = file.read()

        (filename, _) = os.path.splitext(filepath)

        contents.append(BenchmarkFile(filename, content))

        file.close()

    if inner_solver:
        plot_inner_metrics(contents, metrics, show)
    else:
        plot_outer_metrics(contents, metrics, show)

def plot_outer_metrics(contents: list[BenchmarkFile], metrics: list[str], show: bool) -> None:
    # extract all measurements from all files
    file_measurements: list[FileMeasurement] = list(
        map(lambda c: FileMeasurement(c.name, extract_measurements(c.contents)), contents))

    # extract restrict measured metrics to the wanted ones
    for m in file_measurements:
        m.restrict_metrics(metrics)

    sanity_checks(file_measurements)

    filenames = list(map(lambda f: f.name, contents))
    plot_filename = reduce(operator.add, filenames) + '.' + reduce(operator.add, metrics) + ".pdf"

    plot(plot_filename, 'accumulated inner solver iterations', 'norms', file_measurements, show)


def extract_measurements(text: str) -> list[Measurement]:
    block_regex = r'\[0\]\[INFO\s*\]-*\(\d+\.\d+ sec\) finished'

    measurement_blocks = re.split(block_regex, text, 0, re.M)[1:]

    return list(map(extract_measurements_from_block, measurement_blocks))


def extract_measurements_from_block (block: str) -> Measurement:
    # ng iteration and solver type, "<solver> iteration #<ng iteration>"
    outer_infos_regex = r'^\s*(\w+)\s*iteration\s*#(\d+)'

    # accumulated iteration of inner solver, "[0] acc_iterations = <iteration>"
    acc_iterations_regex = r'\[0\]\s*acc_iterations\s*=\s*(\d+)'

    # metrics of a measurement, "[0] <metric> = <value>"
    norm_regex = r'\[0\]\s*(\S+)\s*=\s*(\d+\.\d+(?:e[-+]\d+)?)'

    outer_infos = re.match(outer_infos_regex, block, re.M)
    if outer_infos is None:
        raise ValueError("couldn't find ng iteration and/or solver type in \n" + block)

    solver = outer_infos.group(1)
    ng_iteration = int(outer_infos.group(2))

    acc_iterations = re.search(acc_iterations_regex, block)
    if acc_iterations is None:
        raise ValueError("acc_iterations is missing in text:\n" + block)

    norms = re.findall(norm_regex, block)

    return Measurement(solver, ng_iteration, int(acc_iterations.group(1)), norms)

def plot(dst_filepath: str, xlabel: str, ylabel: str, measurements: list[FileMeasurement], show: bool,
         axis_dims: tuple[int, int, float, float] | None = None,
         axis_type: tuple[PlotAxisType, PlotAxisType] | None = None) -> None:

    assert len(measurements) > 0, "plot needs at least one measurement"

    # todo: this roughly assumes that all measurements have the same amount of metrics
    has_multiple_graphs = len(measurements)*len(measurements[0].measurements[0].metrics) > 1

    # y-axis is logarithmic by default
    # todo: logarithmic scale should also work with fixed axis dimensions, maybe also use logarithmic y-axis as the default if axis_dims is set
    if axis_type is None:
        if axis_dims is None:
            axis_type = (PlotAxisType.LINEAR, PlotAxisType.LOGARITHMIC)
        else:
            axis_type = (PlotAxisType.LINEAR, PlotAxisType.LINEAR)

    plt.figure()

    plt.title(dst_filepath)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if not axis_dims is None:
        plt.axis(axis_dims)

    (xaxis_type, yaxis_type) = axis_type
    if xaxis_type == PlotAxisType.LOGARITHMIC:
        plt.xscale('log')
    if yaxis_type == PlotAxisType.LOGARITHMIC:
        plt.yscale('log')

    colors = iter(('b', 'g', 'r', 'c', 'm', 'y', 'k'))

    for file_measurement in measurements:
        a = file_measurement.measurements[0]
        graphs_start = [Graph(metric, [Point2D(a.acc_iteration, float(value))]) for (metric, value) in a.metrics]
        graphs = reduce(fold_measurements, file_measurement.measurements[1:], graphs_start)

        for graph in graphs:
            # split measurements into iteration list and value list
            xpoints = []
            ypoints = []
            for point in graph.points:  # todo very imperative
                xpoints.append(point.x)
                ypoints.append(point.y)

            label = None
            if has_multiple_graphs:
                label = file_measurement.filename + '.' + graph.metric
            plt.plot(xpoints, ypoints, marker='.', label=label, color=next(colors))

    plt.grid(visible=True)
    if has_multiple_graphs:
        plt.legend()
    plt.savefig(dst_filepath)

    if show:
        plt.show()

def sanity_checks(measurements: list[FileMeasurement]) -> None:
    for m in measurements:
        assert len(m.measurements) > 0, "file needs at least one measurement"

        for measurement in m.measurements:
            assert measurement.ng_iteration >= 0, "ng iteration must be nonnegative"
            assert measurement.acc_iteration >= 0, "acc iterations must be nonnegative"
            assert len(measurement.metrics) > 0, "metrics must be non-empty"


        solver = m.measurements[0].solver
        for mm in m.measurements: # todo very imperative
            assert solver == mm.solver, "solver must stay the same in one benchmark file"

# measurements can be seen as a list of tuples that contain the different metrics
# for plotting we need a list for each metric containing the values
# gets a list of measurements for each metric and adds the different measurements from m to the corresponding metric list
def fold_measurements(l: list[Graph], m: Measurement) -> list[Graph]:
    for metric in m.metrics:
        for graph in l:
            if graph.metric == metric[0]:
                graph.points.append(Point2D(m.acc_iteration, float(metric[1])))
                break

    return l

def plot_inner_metrics(contents: list[BenchmarkFile], metrics: list[str], show: bool) -> None:
    # extract all measurements from all files
    file_measurements: list[FileMeasurement] = list(
        map(lambda c: FileMeasurement(c.name, extract_inner_measurements(c.contents)), contents))

    # extract restrict measured metrics to the wanted ones
    for m in file_measurements:
        m.restrict_metrics(metrics)

    sanity_checks(file_measurements)

    filenames = list(map(lambda f: f.name, contents))
    plot_filename = reduce(operator.add, filenames) + '.inner.' + reduce(operator.add, metrics) + ".pdf"

    plot(plot_filename, 'inner solver iterations of one outer NG iteration', 'norms', file_measurements, show)

def extract_inner_measurements(text: str) -> list[Measurement]:
    outer_block_regex = r'\[0\]\[INFO\s*\]-*\(\d+\.\d+ sec\) finished'

    outer_measurement_block = re.split(outer_block_regex, text, 0, re.M)[0]

    inner_block_regex = r'\[0\]\[INFO\s*\]-*\(\d+\.\d+ sec\) inner solver: finished'
    inner_measurement_blocks = re.split(inner_block_regex, outer_measurement_block, 0, re.M)[1:]

    return list(map(extract_measurements_from_inner_block, inner_measurement_blocks))


def extract_measurements_from_inner_block(block: str) -> Measurement:
    outer_info_regex = r'^\s*(\w+) iteration #(\d+)'

    # metrics of a measurement, "[0] <metric> = <value>"
    norm_regex = r'\[0\]\s*(\S+)\s*=\s*(\d+\.\d+(?:e[-+]\d+)?)'

    outer_info = re.match(outer_info_regex, block, re.M)
    if outer_info is None:
        raise ValueError("couldn't find iteration of inner solver or inner solver type in \n" + block)

    solver = outer_info.group(1)
    iteration = int(outer_info.group(2))

    norms = re.findall(norm_regex, block)

    return Measurement(solver, iteration, iteration, norms)


def plot_inner_metrics2(file_measurement: FileMeasurement, colors, has_multiple_graphs: bool) -> None:
    m = file_measurement.measurements[0]
    metric = m.metrics[0][0] # todo: currently only the first metric type is used

    xpoints = []
    ypoints = []

    counter = 1
    for a in m.metrics:
        if a[0] == metric:
            xpoints.append(counter)
            ypoints.append(a[1])
            counter += 1

    label = None
    if has_multiple_graphs:
        label = file_measurement.filename + '.' + metric
    plt.plot(xpoints, ypoints, marker='.', label=label, color=next(colors))


if __name__ == '__main__':
    main()
