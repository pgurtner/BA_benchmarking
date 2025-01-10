import os
import re
from functools import reduce


def list_flatten(l):
    return [x for xs in l for x in xs]


def convert_to_valid_filename(string: str) -> str:
    filename = string.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_')
    filename = filename.replace('?', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    filename = filename.replace(' ', '_')

    filename = filename.strip()

    if filename == '':
        raise ValueError("filename only contains invalid characters or whitespace")

    return filename


class GridConfig:
    meshNx: str
    meshNy: str
    minLevel: str
    maxLevel: str

    def __init__(self, meshNx, meshNy, minLevel, maxLevel):
        self.meshNx = meshNx
        self.meshNy = meshNy
        self.minLevel = minLevel
        self.maxLevel = maxLevel

    def to_tuple(self):
        return (self.meshNx, self.meshNy, self.minLevel, self.maxLevel)

    def __str__(self) -> str:
        return f"{self.meshNx}x{self.meshNy}.{self.minLevel}-{self.maxLevel}"

    def __repr__(self) -> str:
        return self.__str__()


def build_run_filename(solver: str, grid_config: GridConfig) -> str:
    return f"{solver}.{grid_config}.log"


def extract_info_from_run_filename(run_filename: str) -> tuple[str, GridConfig]:
    basename = os.path.basename(run_filename)
    log_file_pattern = r"(.+)\.(.+)x(.+)\.(.+)-(.+)\.log"
    match_result = re.match(log_file_pattern, basename)

    if match_result is None:
        raise ValueError(f"{basename} is not a valid run filename")

    solver = match_result.group(1)
    grid_config = GridConfig(match_result.group(2), match_result.group(3), match_result.group(4), match_result.group(5))

    return solver, grid_config


def build_std_plot_filename(solver: str, grid_config: GridConfig, benchmarks: list[str], metrics: list[str]) -> str:
    assert len(benchmarks) > 0
    assert len(metrics) > 0

    benchmarks = reduce(lambda s, a: f"{s},{a}", benchmarks)
    metrics = reduce(lambda s, a: f"{s},{a}", metrics)

    return f"{solver}.{grid_config}.{benchmarks}.{metrics}.pdf"


def extract_info_from_std_plot_filename(std_plot_filename: str) -> tuple[str, GridConfig, list[str], list[str]]:
    basename = os.path.basename(std_plot_filename)
    plot_file_pattern = r"(.+)\.(\d+)x(\d+)\.(\d+)-(\d+)\.((?:[^\s\.]+)(?:,[^\s\.]+)*)\.((?:[^\s\.]+)(?:,[^\s\.]+)*)\.pdf"
    match_result = re.match(plot_file_pattern, basename)

    if match_result is None:
        raise ValueError(f"{basename} is not a valid std plot filename")

    solver = match_result.group(1)
    grid_config = GridConfig(match_result.group(2), match_result.group(3), match_result.group(4), match_result.group(5))
    benchmarks = match_result.group(6).split(",")
    metrics = match_result.group(7).split(",")
    return solver, grid_config, benchmarks, metrics
