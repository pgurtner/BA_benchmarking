import operator
import re
from dataclasses import dataclass
from functools import reduce

import matplotlib.pyplot as plt
from enum import Enum
import argparse


class PlotAxisType(Enum):
    LINEAR = 1
    LOGARITHMIC = 2


@dataclass
class MetricDeclaration:
    name: str
    type: str


@dataclass
class BenchmarkDeclaration:
    name: str
    metrics: list[MetricDeclaration]


@dataclass
class MetricsMeasurement:
    benchmark: str
    iteration: int
    values: list[tuple[str, str]]


def restrict_measurement(m: MetricsMeasurement, restricted_metrics: list[str]):
    return list(
        filter(lambda value: value[0] in restricted_metrics,
               m.values))


@dataclass
class Point2D:
    x: float
    y: float


@dataclass
class Graph:
    label: str
    points: list[Point2D]


class Benchmark:
    decl: BenchmarkDeclaration
    measurements: list[MetricsMeasurement]

    def __init__(self, decl: BenchmarkDeclaration):
        self.decl = decl
        self.measurements = []

    def add_measurement(self, measurement: MetricsMeasurement):
        if not measurement.benchmark == self.decl.name:
            raise ValueError(f"tried to add measurement from benchmark {measurement.benchmark} to {self.decl.name}")

        measurement_includes_all_demanded_metrics = all(map(lambda benchmark_metric: any(
            map(lambda measurement_value: benchmark_metric.name == measurement_value[0], measurement.values)),
                                                            self.decl.metrics))

        if not measurement_includes_all_demanded_metrics:
            raise ValueError(f"measurement {measurement} misses a metric of {self.decl.metrics}")

        restricted_metrics = restrict_measurement(measurement, list(
            map(lambda metric_declaration: metric_declaration.name, self.decl.metrics)))

        if len(restricted_metrics) == 0:
            # no error here because having all demanded metrics is checked above
            return

        restricted_measurement = MetricsMeasurement(measurement.benchmark, measurement.iteration, restricted_metrics)

        self.measurements.append(restricted_measurement)

    def restrict_metrics(self, restricted_metrics: list[str]):
        for m in self.measurements:
            m.values = restrict_measurement(m, restricted_metrics)

        self.measurements = list(filter(lambda m: len(m.values) > 0, self.measurements))

    def to_graphs(self) -> list[Graph]:
        if len(self.measurements) == 0:
            return []

        first_measurement = self.measurements[0]
        # todo this could actually check the metric data type and cast value to int or float
        graphs_start = [Graph(metric, [Point2D(first_measurement.iteration, float(value))]) for (metric, value) in
                        first_measurement.values]
        graphs = reduce(_fold_measurements, self.measurements[1:], graphs_start)

        return graphs

    def __str__(self) -> str:
        return f"{self.decl}"

    def __repr__(self) -> str:
        return self.__str__()


# measurements can be seen as a list of tuples that contain the different metrics
# for plotting we need a list for each metric containing the values
# gets a list of measurements for each metric and adds the different measurements from m to the corresponding metric list
def _fold_measurements(l: list[Graph], m: MetricsMeasurement) -> list[Graph]:
    for value in m.values:
        for graph in l:
            if graph.label == value[0]:
                graph.points.append(Point2D(m.iteration, float(value[1])))
                break

    return l


def _list_flatten(l):
    return [x for xs in l for x in xs]


def _convert_to_valid_filename(string: str) -> str:
    filename = string.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_')
    filename = filename.replace('?', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    filename = filename.replace(' ', '_')

    filename = filename.strip()

    if filename == '':
        raise ValueError("filename only contains invalid characters or whitespace")

    return filename


def plot(files: list[str], metrics: list[str], show: bool = False, wanted_benchmarks: list[str] | None = None):
    contents: list[str] = []
    for filepath in files:
        file = open(filepath, 'r')
        content: str = file.read()

        contents.append(content)

        file.close()

    # benchmark names are treated as global names
    text = reduce(operator.add, contents)

    benchmarks = _extract_benchmarks(text, metrics, wanted_benchmarks)

    for b in benchmarks:
        graphs = b.to_graphs()

        output_filename = _plot_filename(b.decl.name, metrics)
        _plot_graphs(output_filename, "iterations", "todo", graphs)

    if show:
        plt.show()  # todo very unclean


def _extract_benchmarks(text: str, wanted_metrics: list[str], wanted_benchmarks: list[str] | None) -> list[Benchmark]:
    declarations = _extract_declarations(text)
    measurements = _extract_measurements(text)

    if wanted_benchmarks is not None:
        declarations = filter(lambda decl: decl.name in wanted_benchmarks, declarations)

    benchmarks = list(map(lambda benchmark_decl: Benchmark(benchmark_decl),
                          declarations))
    for m in measurements:
        for b in benchmarks:
            if m.benchmark == b.decl.name:
                b.add_measurement(m)

    for b in benchmarks:
        b.restrict_metrics(wanted_metrics)

    return list(benchmarks)


def _extract_declarations(text: str) -> list[BenchmarkDeclaration]:
    metric_pattern = r'\s*([^\s,]+(?:<\s*(?:int|float)\s*>)?)\s*'
    pattern = r'\[\d+\]\[INFO\s*\]-+\(\d+\.\d+ sec\) #benchmark\[(.+)\]:' + metric_pattern + '((?:,' + metric_pattern + ')*)'

    declarations = []

    for decl in re.finditer(pattern, text):
        solver = decl.group(1)
        first_metric = _parse_metric_declaration(decl.group(2))

        other_metrics = []
        if decl.group(3) != '':
            other_metrics = map(_parse_metric_declaration, decl.group(3).strip().strip(',').split(','))

        benchmark_decl = BenchmarkDeclaration(solver, [first_metric] + list(other_metrics))

        declarations.append(benchmark_decl)

    return declarations


def _parse_metric_declaration(text: str) -> MetricDeclaration:
    type_parameter_pattern = r'\s*([^\s,]+)<\s*((?:int|float))\s*>\s*'
    match = re.search(type_parameter_pattern, text)

    if match is None:
        return MetricDeclaration(text.strip(), 'float')
    else:
        if match.group(2) == 'int' or match.group(2) == 'float':
            return MetricDeclaration(match.group(1).strip(), match.group(2))
        else:
            raise ValueError(f"Unknown metric type parameter: {match.group(2)}")


def _extract_measurements(text: str) -> list[MetricsMeasurement]:
    metric_pattern = r'\s*(?:[^\s,]+\s*=\s*(?:[^\s,]+))\s*'

    pattern = r'\[\d+\]\[INFO\s*\]-+\(\d+\.\d+ sec\) @\[(.+)\]:(\d+) (' + metric_pattern + ')((?:,' + metric_pattern + ')*)'

    measurements = []

    for m in re.finditer(pattern, text):
        solver = m.group(1)
        iteration = m.group(2)
        first_metric = _parse_metric_measurement(m.group(3))

        other_metrics = []
        if m.group(4) != '':
            other_metrics = map(_parse_metric_measurement, m.group(4).strip().strip(',').split(','))

        measurement = MetricsMeasurement(solver, iteration, [first_metric] + list(other_metrics))

        measurements.append(measurement)

    return measurements


def _parse_metric_measurement(text: str) -> tuple[str, str]:
    metric_pattern = r'\s*([^\s,]+)\s*=\s*([^\s,]+)\s*'

    match = re.match(metric_pattern, text)
    if match is None:
        raise ValueError(f"Metric measurement doesn't fit pattern {text}")
    else:
        return match.group(1), match.group(2)


def _plot_graphs(dst_filepath: str, xlabel: str, ylabel: str, graphs: list[Graph],
                 axis_dims: tuple[int, int, float, float] | None = None,
                 axis_type: tuple[PlotAxisType, PlotAxisType] | None = None):
    if all(map(lambda g: len(g.points) == 0, graphs)):
        return

    has_multiple_graphs = len(graphs) > 1

    # y-axis is logarithmic by default
    if axis_type is None:
        axis_type = (PlotAxisType.LINEAR, PlotAxisType.LOGARITHMIC)

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

    for graph in graphs:
        xpoints = []
        ypoints = []
        for point in graph.points:  # todo very imperative
            xpoints.append(point.x)
            ypoints.append(point.y)

        label = None
        if has_multiple_graphs:
            label = graph.label
        plt.plot(xpoints, ypoints, marker='.', label=label, color=next(colors))

    plt.grid(visible=True)
    if has_multiple_graphs:
        plt.legend()
    plt.savefig(dst_filepath)

    # if show:
    #     plt.show()


def _plot_filename(benchmark: str, metrics: list[str]) -> str:
    return _convert_to_valid_filename(benchmark + '.' + reduce(operator.add,
                                                               metrics) + '.pdf')


if __name__ == "__main__":
    plot(["mg.max_norm"], ["max_norm"])

    _parser = argparse.ArgumentParser()

    _parser.add_argument('files', nargs='+', help="files to plot")
    _parser.add_argument("--show", help="display plot automatically", action="store_true")
    _parser.add_argument("--metrics", help="comma separated list of metrics to plot", default="max_norm")
    _parser.add_argument("--benchmarks", help="comma separated list of benchmarks to plot")

    _args = _parser.parse_args()

    _metrics = _args.metrics.split(',')
    _files = _args.files
    _show = _args.show
    _benchmarks = _args.benchmarks

    if _benchmarks is not None:
        _benchmarks = _args.benchmarks.split(',')

    plot(_files, _benchmarks, _metrics, _show)
