import os
import re
import subprocess
import time

from src.utils import parse_prm_file, find_single_prm_file, RUN_LOG_FILE_NAME


def run(target_dir: str, tasks: int):
    param_file = find_single_prm_file(target_dir)
    abs_param_file_path = os.path.join(target_dir, param_file)
    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')

    if env is None:
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set")
    elif env == "laptop":
        _exec_on_laptop(target_dir, abs_param_file_path, tasks)
    elif env == "fritz":
        _exec_on_fritz(target_dir, abs_param_file_path, tasks)


def _extract_binary_path(param_file_path: str) -> str:
    params = parse_prm_file(param_file_path)
    if "BenchmarkMetaData" not in params:
        raise ValueError(f"No benchmark metadata found in {param_file_path}, aborting run")

    if "binary" not in params["BenchmarkMetaData"]:
        raise ValueError(f"No binary path found in {param_file_path}, aborting run")

    return params["BenchmarkMetaData"]["binary"]


def _exec_on_laptop(target_dir: str, param_file_path: str, tasks: int) -> None:
    cwd = os.getcwd()

    binary_path = _extract_binary_path(param_file_path)
    bin_folder = os.path.dirname(binary_path)
    output_filepath = os.path.join(target_dir, RUN_LOG_FILE_NAME)
    jobscript_filepath = os.path.join(cwd, "job_laptop.sh")

    # change to binary directory for the make call in the job script
    os.chdir(bin_folder)

    subprocess.call(
        [jobscript_filepath, binary_path, param_file_path, output_filepath,
         str(tasks)])

    os.chdir(cwd)


# todo untested
def _exec_on_fritz(target_dir: str, param_file_path: str, tasks: int) -> None:
    cwd = os.getcwd()

    binary_path = _extract_binary_path(param_file_path)
    bin_folder = os.path.dirname(param_file_path)
    output_filepath = os.path.join(target_dir, RUN_LOG_FILE_NAME)
    jobscript_filepath = os.path.join(cwd, "job_fritz.sh")

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
