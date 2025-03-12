import math
import os
import re
import subprocess
import time
from subprocess import Popen

from src.config import prep_fresh_directory
from src.utils import find_single_prm_file, BenchmarkIterator, clean_benchmark_suite, \
    build_run_log_filename, load_benchmark_parameters


class BenchmarkJob:
    tasks: int

    def poll(self) -> bool:
        return False

    def wait(self) -> None:
        return None

    def kill(self) -> None:
        return None


class LaptopJob(BenchmarkJob):
    _subprocess: Popen

    def __init__(self, tasks: int, subprocess: Popen):
        self.tasks = tasks
        self._subprocess = subprocess

    def poll(self) -> bool:
        return self._subprocess.poll() is not None

    def wait(self) -> None:
        self._subprocess.wait()

        return None

    def kill(self) -> None:
        self._subprocess.kill()


class FritzJob(BenchmarkJob):
    _job_id: str

    def __init__(self, tasks: int, _job_id: str):
        self.tasks = tasks
        self._job_id = _job_id

    def poll(self) -> bool:
        return _is_slurm_job_finished(self._job_id)

    def wait(self) -> None:
        _wait_until_slurm_job_finished(self._job_id)

        return None

    def kill(self) -> None:
        _cancel_slurm_job(self._job_id)


def run(target_dirs: list[str], multicore: bool):
    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')

    if env is None:
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set")
    elif env == "laptop":
        exec_benchmark = _exec_on_laptop
    elif env == "fritz":
        exec_benchmark = _exec_on_fritz
    else:
        raise ValueError("invalid BA_BENCHMARKING_UTILITIES_ENV value " + env)

    benchmark_iter = BenchmarkIterator(target_dirs)

    active_jobs: list[BenchmarkJob] = []
    built_folders = []

    try:
        for b in benchmark_iter:
            bm_params = load_benchmark_parameters(b)["BenchmarkMetaData"]
            binary_path = bm_params['binary']
            tasks = int(bm_params['tasks'])
            repeat = int(bm_params['repeat'])

            binary_folder = os.path.dirname(binary_path)

            if binary_folder not in built_folders:
                _build_project(binary_folder)
                built_folders.append(binary_folder)

            prep_fresh_directory(b)
            clean_benchmark_suite(b)

            for i in range(repeat):
                if multicore:
                    if env == "laptop":
                        raise "multicore processing not implemented yet on laptop"

                    allowed_total_jobs = 1
                    if env == 'laptop':
                        allowed_total_jobs = 6  # todo
                    elif env == 'fritz':
                        allowed_total_jobs = 20 * 72

                    # todo rearranging remaining jobs might improve performance
                    #   e.g. if small and big jobs are mixed, performance is waisted
                    #   a simple idea would be to sort jobs by size
                    wait_duration = 1
                    while _waiting_update_and_check_is_busy(allowed_total_jobs, active_jobs, tasks, wait_duration):
                        wait_duration = min(600, wait_duration * 2)

                else:
                    for j in active_jobs:
                        j.wait()

                print(f"starting benchmark {b}, repetition {i}")
                job = exec_benchmark(b, f"{build_run_log_filename(i)}")
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


def _exec_on_laptop(target_dir: str,
                    output_name: str = build_run_log_filename(0)) -> LaptopJob:
    param_file_path = find_single_prm_file(target_dir)
    params = load_benchmark_parameters(target_dir)
    binary_path = params["BenchmarkMetaData"]["binary"]
    tasks = int(params["BenchmarkMetaData"]["tasks"])

    output_filepath = os.path.join(target_dir, output_name)
    jobscript_filepath = os.path.join(os.path.dirname(__file__), '..', "job_laptop.sh")

    # todo is this automatically running?
    job = Popen([jobscript_filepath, binary_path, param_file_path, output_filepath,
                 str(tasks)])

    # subprocess.call(
    #     [jobscript_filepath, binary_path, param_file_path, output_filepath,
    #      str(tasks)])

    return LaptopJob(tasks, job)


def _exec_on_fritz(target_dir: str, output_name: str = build_run_log_filename(0)) -> FritzJob:
    fritz_cores_per_node = 72

    param_file_path = find_single_prm_file(target_dir)
    params = load_benchmark_parameters(target_dir)

    assert "FritzMetaParameters" in params
    assert "pinThreads" in params["FritzMetaParameters"]

    binary_path = params["BenchmarkMetaData"]["binary"]
    tasks = int(params["BenchmarkMetaData"]["tasks"])
    pinThreads = params["FritzMetaParameters"]["pinThreads"]

    output_filepath = os.path.join(target_dir, output_name)

    jobscript_template_filepath = os.path.join(os.path.dirname(__file__), '..', "job_fritz.template")
    nodes = math.ceil(tasks / fritz_cores_per_node)
    tasks_per_node = min(fritz_cores_per_node, tasks)

    with open(jobscript_template_filepath) as f:
        jobscript_template = f.read()

    jobscript = jobscript_template.replace("__NODES__", str(nodes)).replace("__NTASKS_PER_NODE__",
                                                                            str(tasks_per_node))

    if pinThreads == "true":
        jobscript = jobscript.replace("__THREAD_PINNING__", "likwid-pin -q -C N:scatter")
    else:
        jobscript = jobscript.replace("__THREAD_PINNING__", "")

    if "frequency" in params["FritzMetaParameters"]:
        frequency = params["FritzMetaParameters"]["frequency"]
        jobscript = jobscript.replace("__CPU_FREQUENCY__", f"--cpu-freq={frequency}-{frequency}:performance")
    else:
        jobscript = jobscript.replace("__CPU_FREQUENCY__", "")

    if nodes >= 65:
        jobscript = jobscript.replace("__DEPENDANT_SRUN_FLAGS__", "-p big")
    else:
        jobscript = jobscript.replace("__DEPENDANT_SRUN_FLAGS__", "")

    jobscript_filepath = os.path.join(target_dir, "job_fritz.sh")

    with open(jobscript_filepath, 'w') as f:
        f.write(jobscript)

    result = subprocess.run(
        ["sbatch", jobscript_filepath, binary_path, param_file_path,
         output_filepath],
        stdout=subprocess.PIPE)

    # retrieve the job id to wait for the job's completion
    result = result.stdout.decode("utf-8")
    pattern = r"Submitted batch job (\d+)"
    match = re.search(pattern, result)
    jobid = match.group(1)
    print(f"job id: {jobid}")

    return FritzJob(tasks, jobid)


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


# usual waiting with exponentially increasing wait duration, capped at 10 min
def _wait_until_slurm_job_finished(jobid: str) -> None:
    max_duration = 600

    duration = 1
    while not _is_slurm_job_finished(jobid):
        print(f"waiting {duration}s...")
        time.sleep(duration)
        duration = min(max_duration, duration * 2)


def _cancel_slurm_job(jobid: str) -> None:
    result = subprocess.run(["scancel", jobid], stdout=subprocess.PIPE)
