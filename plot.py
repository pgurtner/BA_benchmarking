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
    name: str
    contents: str

class Measurement:
    solver: str
    ng_iteration: int
    acc_iteration: int
    metrics: list[tuple[str, str]]

    def __init__(self, solver, ng_iteration, acc_iteration, metrics):
        self.solver = solver
        self.ng_iteration = ng_iteration
        self.acc_iteration = acc_iteration
        self.metrics = metrics

    def restrict_metrics(self, metrics):
        self.metrics = list(filter(lambda m: m[0] in metrics, self.metrics))

class FileMeasurement:
    filename: str
    measurements: list[Measurement]

    def __init__(self, filename, measurements):
        self.filename = filename
        self.measurements = measurements

    def restrict_metrics(self, metrics):
        for m in self.measurements:
            m.restrict_metrics(metrics)

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

    parser.add_argument("--metrics", help="comma separated list of metrics to plot", required=True)
    parser.add_argument('files', nargs='+', help="files to plot")

    args = parser.parse_args()

    metrics = args.metrics.split(',')
    files = args.files

    plot_files(files, metrics)

def plot_files(filepaths: list[str], metrics: list[str]) -> None:
    contents: list[BenchmarkFile] = []
    for filepath in filepaths:
        file = open(filepath, 'r')
        content: str = file.read()

        (filename, _) = os.path.splitext(filepath)

        contents.append(BenchmarkFile(filename, content))

        file.close()

    file_measurements: list[FileMeasurement] = list(map(lambda c: FileMeasurement(c.name, extract_measurements(c.contents)), contents))
    for m in file_measurements:
        m.restrict_metrics(metrics)

    sanity_checks(file_measurements)

    filenames = list(map(lambda f: os.path.splitext(f)[0], filepaths))
    plot_filename = reduce(operator.add, filenames) + '.' + reduce(operator.add, metrics) + ".pdf"

    plot(plot_filename, 'iterations', 'norms (TODO)', file_measurements)


def extract_measurements(text: str) -> list[Measurement]:
    block_regex = r'\[0\]\[INFO\s*\]-*\(\d+\.\d+ sec\) finished'

    measurement_blocks = re.split(block_regex, text, re.M)[1:]

    return list(map(extract_measurements_from_block, measurement_blocks))


def extract_measurements_from_block (block: str) -> Measurement:
    outer_infos_regex = r'^\s*(\w+)\s*iteration\s*#(\d+)'
    acc_iterations_regex = r'\[0\]\s*acc_iterations\s*=\s*(\d+)'
    norm_regex = r'\[0\]\s*(\w+)\s*=\s*(\d+\.\d+(?:e[-+]\d+)?)'

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


def get_single_measurement_type(measurements: list[list[tuple[str, str]]], measurement) -> list[float]:
    return list_flatten(
        list(map(lambda m: list(map(lambda m: float(m[1]), filter(lambda a: a[0] == measurement, m))), measurements)))


def plot(dst_filepath: str, xlabel: str, ylabel: str, measurements: list[FileMeasurement],
         axis_dims: tuple[int, int, float, float] | None = None,
         axis_type: tuple[PlotAxisType, PlotAxisType] | None = None) -> None:

    assert len(measurements) > 0, "plot needs at least one measurement"
    has_multiple_graphs = len(measurements)*len(measurements[0].measurements[0].metrics) > 1

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

    def fold_measurements(l: list[Graph], m: Measurement) -> list[Graph]:
        for metric in m.metrics:
            for graph in l:
                if graph.metric == metric[0]:
                    graph.points.append(Point2D(m.acc_iteration, float(metric[1])))
                    break

        return l

    colors = iter(('b', 'g', 'r', 'c', 'm', 'y', 'k'))
    for file_measurement in measurements:
        a = file_measurement.measurements[0]
        graphs_start = [Graph(metric, [Point2D(a.acc_iteration, float(value))]) for (metric, value) in a.metrics]
        graphs = reduce(fold_measurements, file_measurement.measurements[1:], graphs_start)

        for graph in graphs:
            xpoints = []
            ypoints = []
            for point in graph.points: #todo very imperative
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


def sanity_checks(measurements: list[FileMeasurement]) -> None:
    for m in measurements:
        assert len(m.measurements) > 0, "file needs at least one measurement"

        for measurement in m.measurements:
            assert measurement.ng_iteration > 0, "ng iteration must be positive"
            assert measurement.acc_iteration >= 0, "acc iterations must be nonnegative"
            assert len(measurement.metrics) > 0, "metrics must be non-empty"


        solver = m.measurements[0].solver
        for mm in m.measurements: # todo very imperative
            assert solver == mm.solver, "solver must stay the same in one benchmark file"

if __name__ == '__main__':
    main()