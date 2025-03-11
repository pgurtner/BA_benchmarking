import os
import re
from dataclasses import dataclass
from functools import reduce


@dataclass
class Point2D:
    x: float
    y: float


@dataclass
class Graph:
    label: str
    points: list[Point2D]


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


def build_run_log_filename(i: int) -> str:
    return f"run{i}.log"


def find_prm_files(target_dir: str) -> list[str]:
    parameter_files = []

    for f in os.scandir(target_dir):
        if f.is_file() and os.path.splitext(f.name)[1] == ".prm":
            parameter_files.append(f.path)

    return parameter_files


def find_single_prm_file(target_dir: str) -> str:
    parameter_files = find_prm_files(target_dir)

    if len(parameter_files) < 1:
        raise ValueError(f"No parameter files found in {target_dir}")
    elif len(parameter_files) > 1:
        raise ValueError(f"Multiple parameter files found in {target_dir}")

    return parameter_files[0]


def parse_prm_file(param_file_content: str) -> dict[str, dict[str, str]]:
    block_pattern = r"(.+)\s*{([\s\S]*?)}"
    prm = {}

    for block in re.finditer(block_pattern, param_file_content):
        fields_pattern = r"\s*(\w+)\s*(.+?)\s*;"

        block_dict = {}

        for field in re.finditer(fields_pattern, block.group(2)):
            block_dict[field.group(1).strip()] = field.group(2).strip()

        prm[block.group(1).strip()] = block_dict

    return prm


def load_prm_file(dir: str) -> dict[str, dict[str, str]]:
    prm_path = find_single_prm_file(dir)
    with open(prm_path, 'r') as f:
        prm_content = f.read()

    prm = parse_prm_file(prm_content)

    return prm


def format_prm_file(prm_file_content: str) -> str:
    prm = parse_prm_file(prm_file_content)
    newline = 0

    parameter_blocks = [
        "vtk", "vtk_output", "minLevel", "maxLevel", "meshFile", "maxNGIterations", "initialGuessType",
        "initialGuessValue",
        newline,
        "ngOperator",
        newline,
        "solver",
        [
            "preSmoothSteps",
            "postSmoothSteps",
            "smoothStepsIncreaseOnCoarserGrids",
            "cycleType",
            "mgMaxIter",
            "mgDynamicMaxIterStart",
            "mgTolerance",
            "mgInitialGuessType",
            "mgInitialGuessValue",
            newline,
            "smoother",
            [
                "chebyshevOrder",
                "chebyshevSpectralRadiusEstMaxIter",
            ],
            newline,
            "coarseGridSolver",
            [
                "gmresMaxIter",
                "gmresRestartLength",
                "cgMaxIter"
            ],
            newline,
            "restriction",
            "prolongation"
        ],
        newline,
        "logOuterBenchmarks",
        "logOuterTests",
        "logOuterMisc",
        "logInnerBenchmarks",
        "logInnerTests",
        "logInnerMisc"
    ]

    formatted_text = ""

    def add_block(block: str) -> str:
        t = block + "\n{"
        for field, value in prm[block].items():
            t += f"\n\t{field} {value};"
        t += "\n}\n\n"

        return t

    def add_formatted_blocks(block: str, block_format: list, indents: int) -> str:
        t = ""
        for b in block_format:
            if isinstance(b, str):
                if b in prm[block]:
                    t += f"{'\t' * indents}{b} {prm[block][b]};\n"
                    del prm[block][b]

            elif isinstance(b, list):
                t += add_formatted_blocks(block, b, indents + 1)

            elif isinstance(b, type(newline)):
                t += '\n'
            else:
                raise ValueError(f"Unrecognized block: {b}")

        return t

    formatted_text += add_block("BenchmarkMetaData")
    del prm["BenchmarkMetaData"]

    formatted_text += "Parameters\n{\n"
    formatted_text += add_formatted_blocks("Parameters", parameter_blocks, 1)
    for remaining_field in prm["Parameters"]:
        formatted_text += f"\t{remaining_field} {prm["Parameters"][remaining_field]};\n"
    formatted_text += "}\n\n"
    del prm["Parameters"]

    for remaining_block in prm.keys():
        formatted_text += add_block(remaining_block)

    return formatted_text


def build_std_plot_filename(benchmarks: list[str], metrics: list[str] | None) -> str:
    assert len(benchmarks) > 0

    benchmarks_str = reduce(lambda s, a: f"{s},{a}", benchmarks)

    metrics_str = 'all'
    if metrics is not None:
        metrics_str = reduce(lambda s, a: f"{s},{a}", metrics)

    return f"{benchmarks_str}.{metrics_str}.pdf"


def clean_directory(directory: str, file_ext: str | None = None) -> None:
    for filename in os.listdir(directory):
        if file_ext is not None and not filename.endswith(file_ext):
            continue

        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            else:
                print(f'Cleaning directory encountered unexpected file format of {filename} in directory {directory}')
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


def clean_benchmark_suite(path: str) -> None:
    clean_directory(os.path.join(path, 'matplots'))
    clean_directory(os.path.join(path, 'vtk'))
    clean_directory(path, '.log')


def benchmark_fold_iterator(directory_path: str, leaf_action, node_action):
    is_benchmark_suite = len(find_prm_files(directory_path)) > 0

    if is_benchmark_suite:
        leaf_action(directory_path)
    else:
        node_action(directory_path)

        files = list(os.scandir(directory_path))
        directories = filter(lambda f: f.is_dir(), files)
        for d in directories:
            benchmark_fold_iterator(d.path, leaf_action, node_action)


class BenchmarkIterator:
    directory_path: list[str]
    benchmark_paths: list[str]
    counter: int

    def __init__(self, directory_path: str | list[str]):
        if isinstance(directory_path, str):
            self.directory_path = [directory_path]
        else:
            self.directory_path = directory_path

        self.benchmark_paths = []
        self.counter = 0

    def __iter__(self):
        for dir in self.directory_path:
            benchmark_fold_iterator(dir, lambda d: self.benchmark_paths.append(d), lambda d: None)

        return self

    def __next__(self):
        if self.counter >= len(self.benchmark_paths):
            raise StopIteration

        el = self.benchmark_paths[self.counter]
        self.counter += 1

        return el
