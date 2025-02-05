import os
import re
from dataclasses import dataclass
from functools import reduce

RUN_LOG_FILE_NAME = "run.log"


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


def find_single_prm_file(target_dir: str) -> str:
    parameter_files = []

    for f in os.scandir(target_dir):
        if f.is_file() and os.path.splitext(f.name)[1] == ".prm":
            parameter_files.append(f.name)

    if len(parameter_files) < 1:
        raise ValueError(f"No parameter files found in {target_dir}")
    elif len(parameter_files) > 1:
        raise ValueError(f"Multiple parameter files found in {target_dir}")

    return os.path.join(target_dir, parameter_files[0])


def parse_prm_file(param_file_path: str) -> dict[str, dict[str, str]]:
    f = open(param_file_path, "r")
    param_content = f.read()
    f.close()

    block_pattern = r"(.+)\s*{([\s\S]*?)}"
    prm = {}

    for block in re.finditer(block_pattern, param_content):
        fields_pattern = r"\s*(\w+)\s*(.+?)\s*;"

        block_dict = {}

        for field in re.finditer(fields_pattern, block.group(2)):
            block_dict[field.group(1)] = field.group(2)

        prm[block.group(1)] = block_dict

    return prm


def build_std_plot_filename(benchmarks: list[str], metrics: list[str] | None) -> str:
    assert len(benchmarks) > 0

    benchmarks_str = reduce(lambda s, a: f"{s},{a}", benchmarks)

    metrics_str = 'all'
    if metrics is not None:
        metrics_str = reduce(lambda s, a: f"{s},{a}", metrics)

    return f"{benchmarks_str}.{metrics_str}.pdf"


def clean_directory(directory: str) -> None:
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            else:
                print(f'Cleaning directory encountered unexpected file format of {filename} in directory {directory}')
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')
