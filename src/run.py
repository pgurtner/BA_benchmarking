import math
import os
import re
import subprocess
import time
from subprocess import Popen

from src.config import prep_fresh_directory
from src.utils import parse_prm_file, find_single_prm_file, RUN_LOG_FILE_NAME, BenchmarkIterator, clean_directory


class BenchmarkJob:
    tasks: int

    def poll(self) -> bool:
        return False

    def wait(self) -> None:
        return None

    def kill(self) -> None:
        return None


class LaptopJob(BenchmarkJob):
    subprocess: Popen

    def __init__(self, tasks: int, subprocess: Popen):
        self.tasks = tasks
        self.subprocess = subprocess

    def poll(self) -> bool:
        return self.subprocess.poll() is not None

    def wait(self) -> None:
        self.subprocess.wait()

        return None

    def kill(self) -> None:
        self.subprocess.kill()


class FritzJob(BenchmarkJob):
    subprocess: Popen

    # todo


def run(target_dirs: list[str], multicore: bool):
    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')

    if env is None:
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set")
    elif env == "laptop":
        exec_benchmark = _exec_on_laptop
    elif env == "fritz":
        # exec_benchmark = _exec_on_fritz
        raise ValueError(
            "running on fritz still has to implement parallel jobs: handling slurm, jobscript copying (running parallel jobs might cause problems if copied job files clash)")
    else:
        raise ValueError("invalid BA_BENCHMARKING_UTILITIES_ENV value " + env)

    benchmark_iter = BenchmarkIterator(target_dirs)

    active_jobs: list[BenchmarkJob] = []
    built_folders = []

    try:
        for b in benchmark_iter:
            prm_file = find_single_prm_file(b)

            binary_path, tasks = _extract_meta_parameters(prm_file)
            binary_folder = os.path.dirname(binary_path)

            if multicore:
                raise "multicore processing not implemented yet"
                allowed_total_jobs = 6 # todo
                wait_duration = 1
                while _waiting_update_and_check_is_busy(allowed_total_jobs, active_jobs, tasks, wait_duration):
                    wait_duration = min(600, wait_duration * 2)

            else:
                for j in active_jobs:
                    j.wait()


            if binary_folder not in built_folders:
                _build_project(binary_folder)
                built_folders.append(binary_folder)

            prep_fresh_directory(b)
            clean_directory(os.path.join(b, 'matplots'))
            clean_directory(os.path.join(b, 'vtk'))

            print(f"starting benchmark {b}")
            job = exec_benchmark(b, prm_file)
            active_jobs.append(job)

        for j in active_jobs:
            j.wait()

    except KeyboardInterrupt:
        print("canceled benchmarks")

    for j in active_jobs:
        j.kill()


def _waiting_update_and_check_is_busy(task_limit: int, active_jobs: list[BenchmarkJob], needed_tasks: int,
                                      wait_duration: int) -> bool:
    # update active jobs
    for j in active_jobs:
        if j.poll():
            active_jobs.remove(j)

    active_tasks = sum(map(lambda j: j.tasks, active_jobs))

    if active_tasks + needed_tasks <= task_limit:
        return False

    time.sleep(wait_duration)
    return True


def _build_project(bin_folder: str) -> None:
    cwd = os.getcwd()

    os.chdir(bin_folder)

    print(f"compiling {bin_folder}")
    subprocess.call(['make'])

    os.chdir(cwd)


def _extract_meta_parameters(param_file_path: str) -> tuple[str, int]:
    with open(param_file_path) as param_file:
        param_file_content = param_file.read()

    params = parse_prm_file(param_file_content)

    if "BenchmarkMetaData" not in params:
        raise ValueError(f"No benchmark metadata found in {param_file_path}, aborting run")

    if "binary" not in params["BenchmarkMetaData"]:
        raise ValueError(f"No binary path found in {param_file_path}, aborting run")

    if "tasks" not in params["BenchmarkMetaData"]:
        raise ValueError(f"No tasks found in {param_file_path}, aborting run")

    return params["BenchmarkMetaData"]["binary"], int(params["BenchmarkMetaData"]["tasks"])


# todo is changing cwd even needed anymore?
def _exec_on_laptop(target_dir: str, param_file_path: str) -> LaptopJob:
    cwd = os.getcwd()

    binary_path, tasks = _extract_meta_parameters(param_file_path)
    bin_folder = os.path.dirname(binary_path)
    output_filepath = os.path.join(target_dir, RUN_LOG_FILE_NAME)
    jobscript_filepath = os.path.join(cwd, "job_laptop.sh")

    # change to binary directory for the make call in the job script
    os.chdir(bin_folder)

    # todo is this automatically running?
    job = Popen([jobscript_filepath, binary_path, param_file_path, output_filepath,
                 str(tasks)])

    # subprocess.call(
    #     [jobscript_filepath, binary_path, param_file_path, output_filepath,
    #      str(tasks)])

    os.chdir(cwd)

    return LaptopJob(tasks, job)


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
