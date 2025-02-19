import math
import os
import re
import subprocess
import time

from src.utils import parse_prm_file, find_single_prm_file, RUN_LOG_FILE_NAME


def run(target_dir: str):
    param_file = find_single_prm_file(target_dir)
    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')

    if env is None:
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set")
    elif env == "laptop":
        _exec_on_laptop(target_dir, param_file)
    elif env == "fritz":
        _exec_on_fritz(target_dir, param_file)


def _extract_meta_parameters(param_file_path: str) -> tuple[str, int]:
    params = parse_prm_file(param_file_path)
    if "BenchmarkMetaData" not in params:
        raise ValueError(f"No benchmark metadata found in {param_file_path}, aborting run")

    if "binary" not in params["BenchmarkMetaData"]:
        raise ValueError(f"No binary path found in {param_file_path}, aborting run")

    if "tasks" not in params["BenchmarkMetaData"]:
        raise ValueError(f"No tasks found in {param_file_path}, aborting run")

    return params["BenchmarkMetaData"]["binary"], int(params["BenchmarkMetaData"]["tasks"])


def _exec_on_laptop(target_dir: str, param_file_path: str) -> None:
    cwd = os.getcwd()

    binary_path, tasks = _extract_meta_parameters(param_file_path)
    bin_folder = os.path.dirname(binary_path)
    output_filepath = os.path.join(target_dir, RUN_LOG_FILE_NAME)
    jobscript_filepath = os.path.join(cwd, "job_laptop.sh")

    # change to binary directory for the make call in the job script
    os.chdir(bin_folder)

    subprocess.call(
        [jobscript_filepath, binary_path, param_file_path, output_filepath,
         str(tasks)])

    os.chdir(cwd)


def _exec_on_fritz(target_dir: str, param_file_path: str) -> None:
    fritz_cores_per_node = 72
    cwd = os.getcwd()

    binary_path, tasks = _extract_meta_parameters(param_file_path)
    bin_folder = os.path.dirname(binary_path)
    output_filepath = os.path.join(target_dir, RUN_LOG_FILE_NAME)

    jobscript_template_filepath = os.path.join(cwd, "job_fritz.template")
    nodes = math.ceil(tasks / fritz_cores_per_node)
    tasks_per_node = min(fritz_cores_per_node, tasks)

    with open(jobscript_template_filepath) as f:
        jobscript_template = f.read()

    jobscript = jobscript_template.replace("__NODES__", str(nodes)).replace("__NTASKS_PER_NODE__",
                                                                            str(tasks_per_node))
    if nodes >= 65:
        jobscript = jobscript.replace("__DEPENDANT_SRUN_FLAGS__", "-p big")
    else:
        jobscript = jobscript.replace("__DEPENDANT_SRUN_FLAGS__", "");

    jobscript_filepath = os.path.join(target_dir, "job_fritz.sh")

    with open(jobscript_filepath, 'w') as f:
        f.write(jobscript)

    # change to binary directory for the make call in the job script
    os.chdir(bin_folder)

    result = subprocess.run(
        ["sbatch", jobscript_filepath, binary_path, param_file_path,
         output_filepath, str(tasks)],
        stdout=subprocess.PIPE)

    # retrieve the job id to wait for the job's completion
    result = result.stdout.decode("utf-8")
    pattern = r"Submitted batch job (\d+)"
    match = re.search(pattern, result)
    jobid = match.group(1)
    print(f"job id: {jobid}")

    _wait_until_slurm_job_finished(jobid)

    os.chdir(cwd)


def _is_slurm_job_finished(jobid: str) -> bool:
    result = subprocess.run(["squeue", "-j", jobid], stdout=subprocess.PIPE)
    result = result.stdout.decode("utf-8")
    pattern = r"\s*JOBID\s+PARTITION\s+NAME\s+USER\s+ST\s+TIME\s+TIME_LIMIT\s+NODES\s+CPUS\s+NODELIST\(REASON\)\s*\n\s+\S+\s+\S+\s+\S+\s+\S+\s+(\w+)"
    match = re.search(pattern, result)

    # if the job is finished, it isn't displayed in the squeue output
    if match is None:
        return True

    jobstatus = match.group(1)

    if jobstatus == "PD":
        print(f"job {jobid} still pending...")

    # if it is displayed, only(?) the status CG means it is finished
    return jobstatus == "CG"


# typical waiting with exponentially increasing wait duration, capped at 10 min
def _wait_until_slurm_job_finished(jobid: str) -> None:
    max_duration = 600

    duration = 1
    while not _is_slurm_job_finished(jobid):
        print(f"waiting {duration}s...")
        time.sleep(duration)
        duration = min(max_duration, duration * 2)
