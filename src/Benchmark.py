import copy
import operator
from dataclasses import dataclass
from functools import reduce

from src.plot import Graph, Point2D


class MetricDeclaration:
    name: str
    type: str

    def __init__(self, name: str, metric_type: str):
        if '.' in name or ' ' in name or ',' in name:
            raise ValueError("metric names cannot contain dots, spaces and commas")

        self.name = name
        self.type = metric_type


@dataclass
class MetricsMeasurement:
    benchmark: str
    iteration: int
    values: list[tuple[str, str]]


class BenchmarkDeclaration:
    name: str
    metrics: list[MetricDeclaration]

    def __init__(self, name: str, metrics: list[MetricDeclaration]):
        if '.' in name or ' ' in name or ',' in name:
            raise ValueError("benchmark names cannot contain dots, spaces and commas")

        self.name = name
        self.metrics = metrics


class Benchmark:
    active_metrics: list[MetricDeclaration]

    decl: BenchmarkDeclaration
    measurements: list[MetricsMeasurement]

    def __init__(self, decl: BenchmarkDeclaration):
        self.active_metrics = copy.deepcopy(decl.metrics)

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

        restricted_metrics = _restrict_measurement(measurement, list(
            map(lambda metric_declaration: metric_declaration.name, self.decl.metrics)))

        if len(restricted_metrics) == 0:
            # no error here because having all demanded metrics is checked above
            return

        restricted_measurement = MetricsMeasurement(measurement.benchmark, measurement.iteration, restricted_metrics)

        self.measurements.append(restricted_measurement)

    def restrict_metrics(self, restricted_metrics: list[str]):
        self.active_metrics = list(filter(lambda metric: metric.name in restricted_metrics, self.active_metrics))

        for m in self.measurements:
            m.values = _restrict_measurement(m, restricted_metrics)

        self.measurements = list(filter(lambda m: len(m.values) > 0, self.measurements))

        if len(self.measurements) == 0:
            print(
                f"Warning: removed all measurements of {self.decl.name} after restricting to metrics {restricted_metrics}")

    def to_graphs(self) -> list[Graph]:
        if len(self.measurements) == 0:
            return []

        first_measurement = self.measurements[0]
        # todo this could actually check the metric data type and cast value to int or float
        graphs_start = [Graph(metric, [Point2D(first_measurement.iteration, float(value))]) for (metric, value) in
                        first_measurement.values]
        graphs = reduce(_fold_measurements, self.measurements[1:], graphs_start)

        for g in graphs:
            g.label = f"{self.decl.name}." + g.label

        return graphs

    def get_id(self) -> str:
        return f"{self.decl.name}.{reduce(operator.add, self.active_metrics)}"

    def __str__(self) -> str:
        return self.get_id()

    def __repr__(self) -> str:
        return self.__str__()


def _restrict_measurement(m: MetricsMeasurement, restricted_metrics: list[str]):
    return list(
        filter(lambda value: value[0] in restricted_metrics,
               m.values))


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
