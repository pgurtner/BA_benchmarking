import os
import re

from src.Benchmark import Benchmark, BenchmarkDeclaration, MetricDeclaration, MetricsMeasurement
from src.utils import load_prm_file, build_run_log_filename, list_flatten


def restrict_benchmarks(benchmarks: list[Benchmark], wanted_benchmarks: list[str] | None,
                        wanted_metrics: list[str] | None) -> list[Benchmark]:
    if wanted_benchmarks is not None:
        benchmarks = list(filter(lambda b: b.decl.name in wanted_benchmarks, benchmarks))

    if wanted_metrics is not None:
        for b in benchmarks:
            b.restrict_metrics(wanted_metrics)

    return benchmarks


def extract_benchmarks(target_dir: str) -> list[Benchmark]:
    prm = load_prm_file(target_dir)

    if "BenchmarkMetaData" not in prm:
        raise ValueError(f"config of {target_dir} does not contain a BenchmarkMetaData block")

    if "repeat" not in prm["BenchmarkMetaData"]:
        raise ValueError(f"config of {target_dir} does not contain a repeat value")

    if "reduce" not in prm["BenchmarkMetaData"]:
        raise ValueError(f"config of {target_dir} does not contain a reduce value")

    repetitions_amount = int(prm["BenchmarkMetaData"]["repeat"])
    reduce_type = prm["BenchmarkMetaData"]["reduce"]

    benchmark_runs = []
    for i in range(repetitions_amount):
        run_log_path = os.path.join(target_dir, build_run_log_filename(i))
        benchmark_runs.append(_extract_run_log(run_log_path))

    reduced_benchmarks = []
    benchmark_names = list(map(lambda b: b.decl.name, benchmark_runs[0]))

    # todo outsource some of the code here in functions
    for benchmark_name in benchmark_names:
        benchmarks = list_flatten(
            list(map(lambda b: filter(lambda b: b.decl.name == benchmark_name, b), benchmark_runs)))

        metrics = benchmarks[0].decl.metrics
        # todo assert all metrics are equal

        new_name = benchmark_name + '_reduced'
        reduced_benchmark_decl = BenchmarkDeclaration(new_name, metrics)
        reduced_benchmark = Benchmark(reduced_benchmark_decl)

        if reduce_type == 'avg':
            limit = max(map(lambda b: len(b.measurements), benchmarks))
        elif reduce_type == 'max':
            limit = max(map(lambda b: len(b.measurements), benchmarks))
        elif reduce_type == 'min':
            limit = min(map(lambda b: len(b.measurements), benchmarks))
        else:
            raise ValueError(f"unknown reduce type {reduce_type}")

        # todo this is a total naming mess with the different types of measurements
        for i in range(limit):
            # how varying amounts of measurements are handled
            # Nonexistent measurements are treated as zeroes therefore:
            # reduce avg:
            #   zeroed measurements are implicitly added by dividing by len(benchmarks)
            #   further down in the code.
            # reduce max:
            #   nothing to be done. zeroed measurements are irrelevant for this reduce type.
            # reduce min:
            #   limit is set to the min length in this case, so all measurement lists have
            #   the same length.

            measurements = list(map(lambda b: b.measurements[i], filter(lambda b: len(b.measurements) > i, benchmarks)))

            new_measurement = MetricsMeasurement(new_name, i, [])
            for m in metrics:
                metric_measurements = list(
                    map(lambda measurement: list(filter(lambda mvalue: mvalue[0] == m.name, measurement.values)),
                        measurements))

                for measurement in metric_measurements:
                    assert len(measurement) == 1, "unexpected amount of measurements"

                def parse_value(v: str):
                    if m.type == 'int':
                        return int(v)
                    elif m.type == 'float':
                        return float(v)
                    else:
                        raise ValueError("unknown metric type " + m.type)

                values = list(map(lambda mm: parse_value(mm[1]), list_flatten(metric_measurements)))

                if reduce_type == 'avg':
                    # when using len(benchmarks) non-existant benchmarks if e.g. the NG solver already finished
                    # aren't properly treated. These benchmarks are supposed to be treated like a list of zeroed
                    # measurements -> have to be included in the divisor
                    reduced_value = sum(values) / repetitions_amount
                elif reduce_type == 'max':
                    reduced_value = max(values)
                elif reduce_type == 'min':
                    reduced_value = min(values)
                else:
                    raise ValueError(f"unknown reduce type {reduce_type}")

                new_measurement.values.append((m.name, str(reduced_value)))

            reduced_benchmark.add_measurement(new_measurement)

        reduced_benchmarks.append(reduced_benchmark)

    return reduced_benchmarks


def _extract_run_log(run_log_path: str) -> list[Benchmark]:
    if not os.path.isfile(run_log_path):
        raise ValueError(f"Run log file not found at {run_log_path}")

    file = open(run_log_path, 'r')
    benchmark_log = file.read()
    file.close()

    declarations = _extract_declarations(benchmark_log)
    measurements = _extract_measurements(benchmark_log)

    benchmarks = list(map(lambda benchmark_decl: Benchmark(benchmark_decl),
                          declarations))
    for m in measurements:
        for b in benchmarks:
            if m.benchmark == b.decl.name:
                b.add_measurement(m)

    benchmarks = filter(lambda b: len(b.measurements) > 0, benchmarks)

    return list(benchmarks)


def _extract_declarations(text: str) -> list[BenchmarkDeclaration]:
    metric_pattern = r'\s*([^\s,]+(?:<\s*(?:int|float)\s*>)?)\s*'
    pattern = r'\[\s*\d+\s*\]\[\s*INFO\s*\]-+\(\d+\.\d+ sec\) #benchmark\[(.+)\]:' + metric_pattern + '((?:,' + metric_pattern + ')*)'

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

    pattern = r'\[\s*\d+\s*\]\[\s*INFO\s*\]-+\(\d+\.\d+ sec\) @\[(.+)\]:(\d+)\s+(' + metric_pattern + ')((?:,' + metric_pattern + ')*)'

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
