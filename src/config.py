import os
import copy
from src.utils import BenchmarkIterator, find_prm_files, format_prm_file, parse_prm_file, find_single_prm_file

_default_config = {
    "BenchmarkMetaData": {
        "binary": '',
        "tasks": 1
    },
    "Parameters": {
        "vtk": False,
        "vtk_output": '',
        "minLevel": 2,
        "maxLevel": 5,
        "meshFile": "3D/cube_6el.msh",
        "maxNGIterations": 20,
        "initialGuessType": "random",
        "initialGuessValue": 1e-1,

        "ngOperator": "symmetric",

        "solver": "mg",
        "preSmoothSteps": 2,
        "postSmoothSteps": 1,
        "smoothStepsIncreaseOnCoarserGrids": 0,
        "cycleType": "v",
        "mgMaxIter": 200,
        "mgTolerance": 1e-14,
        "mgInitialGuessType": "random",
        "mgInitialGuessValue": 1e-1,

        "smoother": "chebyshev",
        "chebyshevOrder": 2,
        "chebyshevSpectralRadiusEstMaxIter": 20,

        "coarseGridSolver": "gmres",
        "gmresMaxIter": 600,
        "gmresRestartLength": 40,

        "restriction": "linear",
        "prolongation": "linear",

        "logOuterBenchmarks": True,
        "logOuterTests": False,
        "logOuterMisc": False,
        "logInnerBenchmarks": True,
        "logInnerTests": False,
        "logInnerMisc": False
    }
}

def _parse_assignment(assignment: str) -> tuple[tuple[str, str], str]:
    assert assignment.count('=') == 1, 'config field assignments must have exactly one "="'

    key, value = assignment.split('=')
    assert key.count('.') <= 1, 'config field assignment keys cant have more than one dot'

    if '.' in key:
        block, key = key.split('.')
    else:
        block = 'Parameters'

    return (block, key), value


def _sanitize_parameter_value(value):
    assert value != '', 'parameter value cannot be empty'

    if isinstance(value, bool):
        if value:
            value = 'true'
        else:
            value = 'false'

    value = str(value)

    return value

class BenchmarkConfig:
    fields = {}

    def __init__(self, fields: dict, ba_path: str):
        self.fields = fields

        self.fields["BenchmarkMetaData"]["binary"] = os.path.abspath(
            os.path.join(ba_path, 'hyteg-build', 'apps', 'nlDiffusion',
                         'nlDiffusionExample'))

    def set_individual_fields(self, suite_path: str):
        self.fields["Parameters"]["vtk_output"] = os.path.abspath(os.path.join(suite_path, 'vtk'))

    def update_field(self, block: str, field: str, value):
        if value == '':
            if block not in self.fields:
                return
            if field not in self.fields[block]:
                return

            del self.fields[block][field]

            if len(self.fields[block]) == 0:
                del self.fields[block]
        else:
            if block not in self.fields:
                self.fields[block] = {field: value}
                return

            self.fields[block][field] = value

    def set_assignments(self, assignments: list[str]):
        for assignment in assignments:
            (block, key), value = _parse_assignment(assignment)
            self.update_field(block, key, value)

    def __str__(self):
        text = ''
        for name, block in self.fields.items():
            text += name + '\n{\n'

            for key, value in block.items():
                sanitized_value = _sanitize_parameter_value(value)

                text += f"\t{key} {sanitized_value};\n"

            text += '}\n\n'

        formatted = format_prm_file(text)

        return formatted

def init_default_config (ba_path: str) -> BenchmarkConfig:
    return BenchmarkConfig(copy.deepcopy(_default_config), ba_path)

def init_existing_config (config_path: str, ba_path: str) -> BenchmarkConfig:
    prm_path = find_single_prm_file(config_path)

    with open(prm_path, 'r') as f:
        prm_content = f.read()

    config = parse_prm_file(prm_content)

    return BenchmarkConfig(config, ba_path)


def _get_env_dependent_values() -> str:
    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')
    if env == "laptop":
        ba_path = os.path.join('/', 'home', 'pg', 'Documents', 'uni', 'bachelor', 'fs7', 'Bachelorarbeit')
    elif env == "fritz":
        ba_path = os.path.join('/', 'home', 'hpc', 'iwia', 'iwia123h')
    else:
        raise ValueError(f"BA_BENCHMARKING_UTILITIES_ENV has invalid value {env}")

    return ba_path

def set_configs(directory_path: str, assignments: list[str], set_defaults: bool) -> None:
    ba_path = _get_env_dependent_values()

    if set_defaults:
        config = init_default_config(ba_path)
        config.set_assignments(assignments)

    benchmark_iter = BenchmarkIterator(directory_path)

    for b in benchmark_iter:
        if not set_defaults:
            config = init_existing_config(b, ba_path)
            config.set_assignments(assignments)

        config.set_individual_fields(b)

        prm_files = find_prm_files(b)

        for f in prm_files:
            with open(f, 'w') as file:
                file.write(str(config))


def prep_fresh_directory(target_dir: str):
    os.makedirs(os.path.join(target_dir, "matplots"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "vtk"), exist_ok=True)


def create_config(directory_path: str, assignments: list[str]) -> None:
    ba_path = _get_env_dependent_values()

    os.makedirs(directory_path, exist_ok=True)

    config = init_default_config(ba_path)
    config.set_assignments(assignments)
    config.set_individual_fields(directory_path)

    with open(os.path.join(directory_path, 'Parameters.prm'), 'w') as f:
        f.write(str(config))

    prep_fresh_directory(directory_path)
