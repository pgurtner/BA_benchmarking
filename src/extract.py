import os
import re

from src.Benchmark import Benchmark, BenchmarkDeclaration, MetricDeclaration, MetricsMeasurement
from src.utils import extract_info_from_run_filename


def extract_benchmarks(filepath: str, wanted_metrics: list[str] | None = None,
                       wanted_benchmarks: list[str] | None = None) -> list[Benchmark]:
    file = open(filepath, 'r')
    benchmark_log = file.read()
    file.close()

    declarations = _extract_declarations(benchmark_log)
    measurements = _extract_measurements(benchmark_log)

    if wanted_benchmarks is not None:
        declarations = filter(lambda decl: decl.name in wanted_benchmarks, declarations)

    solver, grid_config = extract_info_from_run_filename(os.path.basename(filepath))
    benchmarks = list(map(lambda benchmark_decl: Benchmark(benchmark_decl, solver, grid_config),
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
        benchmark_name = decl.group(1)
        first_metric = _parse_metric_declaration(decl.group(2))

        other_metrics = []
        if decl.group(3) != '':
            other_metrics = map(_parse_metric_declaration, decl.group(3).strip().strip(',').split(','))

        benchmark_decl = BenchmarkDeclaration(benchmark_name, [first_metric] + list(other_metrics))

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

        measurement = MetricsMeasurement(solver, int(iteration), [first_metric] + list(other_metrics))

        measurements.append(measurement)

    return measurements


def _parse_metric_measurement(text: str) -> tuple[str, str]:
    metric_pattern = r'\s*([^\s,]+)\s*=\s*([^\s,]+)\s*'

    match = re.match(metric_pattern, text)
    if match is None:
        raise ValueError(f"Metric measurement doesn't fit pattern {text}")
    else:
        return match.group(1), match.group(2)
