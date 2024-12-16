import operator
import os.path
import re
from dataclasses import dataclass
from functools import reduce

import matplotlib.pyplot as plt
import numpy as np
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
        self.measurements = []

    def restrict_metrics(self, metrics):
        self.measurements = list(map(lambda m: m.restrict_metrics(metrics), self.measurements))


def list_flatten(l):
    return [x for xs in l for x in xs]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--metrics", help="comma separated list of metrics to plot")
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

    plot_filename = reduce(operator.add, filepaths) + reduce(operator.add, metrics) + ".pdf"
    #todo build filename
    plot(plot_filename, 'iterations', 'norms (TODO)', file_measurements)


def extract_measurements(text: str) -> list[Measurement]:
    block_regex = r'\[0\]\[INFO\s*\]-*\(\d+\.\d+ sec\) finished'

    measurement_blocks = re.split(block_regex, text, re.M)[1:]

    return list(map(extract_measurements_from_block, measurement_blocks))


def extract_measurements_from_block (block: str) -> Measurement:
    outer_infos_regex = r'^(\w+) iteration #(\d+)'
    acc_iterations_regex = r'\[0\]\s*acc_iterations = (\d+)'
    norm_regex = r'\[0\]\s*(\w+) = (\d+\.\d+(?:e[-+]\d+)?)'

    outer_infos = re.match(outer_infos_regex, block, re.M)
    if outer_infos is None:
        raise "couldn't find ng iteration and/or solver type in \n" + block

    solver = outer_infos.group(0)
    ng_iteration = int(outer_infos.group(1))

    acc_iterations = re.match(acc_iterations_regex, block, re.M)
    if acc_iterations is None:
        raise "acc_iterations is missing in text:\n" + block

    norms = re.findall(norm_regex, block, re.M)

    return Measurement(solver, ng_iteration, int(acc_iterations.group()), norms)


def get_single_measurement_type(measurements: list[list[tuple[str, str]]], measurement) -> list[float]:
    return list_flatten(
        list(map(lambda m: list(map(lambda m: float(m[1]), filter(lambda a: a[0] == measurement, m))), measurements)))


def plot(dst_filepath: str, xlabel: str, ylabel: str, measurements: list[FileMeasurement],
         axis_dims: tuple[int, int, float, float] | None = None,
         axis_type: tuple[PlotAxisType, PlotAxisType] | None = None) -> None:
    if axis_type is None:
        if axis_dims is None:
            axis_type = (PlotAxisType.LINEAR, PlotAxisType.LOGARITHMIC)
        else:
            axis_type = (PlotAxisType.LINEAR, PlotAxisType.LINEAR)

    plt.figure()

    plt.title(dst_filepath)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if axis_dims is None:
        # t2 = map(lambda ds: ds[1], datasets)
        #
        # t1 = map(lambda ds: max(map(lambda d: d[0], ds)), t2)
        # largest_x = max(t1)
        #
        # t4 = map(lambda ds: ds[1], datasets)
        # t3 = map(lambda ds: max(map(lambda d: d[1], ds)), t4)
        # largest_y = max(t3)
        # plt.axis((1, largest_x, 0, largest_y))
        pass
    else:
        plt.axis(axis_dims)

    (xaxis_type, yaxis_type) = axis_type
    if xaxis_type == PlotAxisType.LOGARITHMIC:
        plt.xscale('log')
    if yaxis_type == PlotAxisType.LOGARITHMIC:
        plt.yscale('log')

    colors = iter(('b', 'g', 'r', 'c', 'm', 'y', 'k'))
    for (label, points) in datasets:
        (xpoints, ypoints) = zip(*points)

        usedlabel = None
        if len(datasets) > 1:
            usedlabel = label

        plt.plot(xpoints, ypoints, marker='.', label=usedlabel, color=next(colors))

    plt.grid(visible=True)
    if (len(datasets) > 1):
        plt.legend()
    plt.savefig(dst_filepath)


def sanity_checks(measurements: list[FileMeasurement]) -> None:
    for m in measurements:
        for measurement in m.measurements:
            assert measurement.ng_iteration > 0, "ng iteration must be positive"
            assert measurement.acc_iteration >= 0, "acc iterations must be nonnegative"

        solvers = map(lambda measurement: measurement.solver, m.measurements)
        assert reduce(operator.eq, solvers), "solver must stay the same in one benchmark file"

def plot_manually() -> None:
    gmres = [(0, 1), (1400, 4.729714e-01), (2800, 7.900971e-02), (4200, 5.315518e-02), (5600, 3.759398e-02),
             (7000, 5.500144e-03), (8400, 4.811260e-03), (9800, 3.028098e-03), (11200, 4.406953e-04),
             (12600, 5.201884e-04),
             (14000, 2.068233e-04), (15400, 7.337124e-06), (16800, 2.916612e-05), (18200, 4.500988e-06),
             (19600, 1.672948e-06), (21000, 5.993488e-07), (22400, 2.369102e-08), (23800, 5.718583e-08),
             (25200, 2.543933e-08), (26600, 4.542850e-09)]
    mg = [(0, 1), (256, 3.978841e-01), (512, 7.005615e-02), (768, 2.724757e-02), (1024, 1.442532e-02),
          (1280, 2.379722e-04), (1536, 1.635978e-03), (1792, 3.930050e-04), (2048, 9.692360e-05), (2304, 6.713465e-05),
          (2560, 4.281234e-06), (2816, 6.696049e-06), (3072, 2.021280e-06), (3328, 3.036644e-07), (3584, 3.036644e-07),
          (3840, 3.167425e-08), (4096, 5.478615e-09)]
    direct = [(0, 1), (1, 5.893677e-01), (2, 1.444670e-01), (3, 3.497706e-02), (4, 1.808695e-03), (5, 4.592547e-06),
              (6, 2.952218e-11)]
    gmresp = [(0, 1), (272, 5.893677e-01), (667, 1.444670e-01), (983, 3.497706e-02), (1257, 1.808695e-03),
              (1489, 4.592548e-06), (1643, 2.951378e-11)]

    fmgExp = [(0, 1), (1, 1.284682e-01), (3, 1.545465e-02), (7, 2.777453e-02), (15, 4.689945e-02), (31, 7.568565e-02),
              (63, 1.152525e-01), (127, 1.396102e-01), (255, 2.451499e+05),
              (511, 0.000000e+00)]

    mgExpNG = [(0, 1), (1, 5.904063e-01), (3, 4.569633e-01), (7, 3.107204e-01), (15, 1.353586e-01), (31, 1.119550e-01),
               (63, 1.341227e-01), (127, 1.681922e-01), (255, 6.609933e-02),
               (511, 2.941445e-02), (1023, 1.196179e-02), (2047, 6.381133e-05), (4095, 2.040371e-06),
               (5666, 9.176532e-12)]

    mgExpNGSym = [(0, 1), (1, 1.153060e+00), (3, 1.581880e-01), (7, 9.273964e-02), (15, 8.580599e-02),
                  (31, 9.766990e-02), (63, 1.466326e-01), (127, 1.588710e-01), (255, 7.042848e-02),
                  (511, 6.717335e-02), (1023, 1.609975e-02), (2047, 1.279641e-02), (4095, 4.983220e-03),
                  (7673, 1.291749e-03), (11043, 2.548260e-04), (14135, 4.050383e-05)]

    mgExpNGSep = [(0, 1), (1, 2.749270e+00), (3, 4.914751e+00), (7, 1.254289e+01), (15, 3.642902e+01),
                  (31, 1.767802e+26), (33, 0.000000e+00)]

    # plots
    # std operator: all (including mg exp), without fmg, without fmg+gmres, without fmg+gmres smol, without fmg+gmres smoller
    stdop_all = [("MG const", mg), ("LU", direct), ("GMRES prec", gmresp), ("MG exp", mgExpNG), ("GMRES", gmres),
                 ("FMG exp", fmgExp)]
    stdop_nofmg = [("MG const", mg), ("LU", direct), ("GMRES prec", gmresp), ("MG exp", mgExpNG), ("GMRES", gmres)]
    stdop_nofmg_nogmres = [("MG const", mg), ("LU", direct), ("GMRES prec", gmresp), ("MG exp", mgExpNG)]

    # changed operators: all, without ngSep
    chop_all = [("NG", mgExpNG), ("NGSym", mgExpNGSym), ("NGSep", mgExpNGSep)]
    chop_nongsep = [("MG NG", mgExpNG), ("MG NGSym", mgExpNGSym)]

    # plot("unchangedOperator_All.jpg", "iterations", "residual", stdop_all)
    plot("unchangedOperator_NoFMG.jpg", "iterations", "residual", stdop_nofmg)  # , (0, 10000, 0.0, 1.0))
    plot("unchangedOperator_NoFMG_NoGMRES.jpg", "iterations", "residual", stdop_nofmg_nogmres)  # , (0, 2000, 0.0, 1.0))

    # plot("changedOperator_All.jpg", "iterations", "residual", chop_all)
    plot("changedOperator_NoNGSep.jpg", "iterations", "residual", chop_nongsep)  # , (0, 6000, 0.0, 1.0))
    # plot("changedOperator_NoNGSep_smol.jpg", "iterations", "residual", chop_nongsep)#, (0, 3000, 0.0, 0.2))

    # plot("mg_exp_vs_const.jpg", "iterations", "residual", [("MG const", mg), ("MG exp", mgExpNG)])#, (0, 3000, 0.0, 1.0))
    # plot("mg_exp_vs_const_smol.jpg", "iterations", "residual", [("MG const", mg), ("MG exp", mgExpNG)])

    # datasets1 = [("LU", direct), ["MG", mg], ["GMRES prec", gmresp]]
    #
    # t2 = map(lambda ds: ds[1], datasets1)
    #
    # t1 = map(lambda ds: max(map(lambda d: d[0], ds)), t2)
    # largest_x = max(t1)
    #
    # t4 = map(lambda ds: ds[1], datasets1)
    # t3 = map(lambda ds: max(map(lambda d: d[1], ds)), t4)
    # largest_y = max(t3)
    #
    # plot("unchangedOperator_nogmres_smol.jpg", "iterations", "residual", [("LU", direct), ["MG", mg], ["GMRES prec", gmresp]], (0, largest_x, 0, 0.01))
    # plot("unchangedOperator_nogmres_smoller.jpg", "iterations", "residual", [("LU", direct), ["MG", mg], ["GMRES prec", gmresp]], (0, largest_x, 0, 0.0001))


main()
