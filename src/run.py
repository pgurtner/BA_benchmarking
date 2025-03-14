import math
import os
import re
import subprocess
import time
from functools import reduce
from subprocess import Popen

from src.config import prep_fresh_directory
from src.utils import find_single_prm_file, BenchmarkIterator, clean_benchmark_suite, \
    build_run_log_filename, load_benchmark_parameters

import datetime
import logging

_logger = logging.getLogger(__name__)


class BenchmarkJob:
    tasks: int
    name: str

    def poll(self) -> bool:
        return False

    def wait(self) -> None:
        return None

    def kill(self) -> None:
        return None


class LaptopJob(BenchmarkJob):
    _subprocess: Popen

    def __init__(self, name: str, tasks: int, subprocess: Popen):
        self.name = name
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

    def __init__(self, name: str, tasks: int, _job_id: str):
        self.name = name
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
    date = datetime.datetime.now()
    log_name = date.strftime("%Y-%m-%d_%Hh-%Mm-%Ss")
    log_path = os.path.join("benchmarks", "logs", log_name + ".log")
    logging.basicConfig(filename=log_path, level=logging.INFO)
    _logger.info(f"Starting at time {date}.")

    env = os.environ.get('BA_BENCHMARKING_UTILITIES_ENV')

    if env is None:
        raise ValueError("BA_BENCHMARKING_UTILITIES_ENV must be set")
    elif env == "laptop":
        run_on_laptop(target_dirs, multicore)
    elif env == "fritz":
        run_on_slurm_machine(target_dirs, multicore)
    else:
        raise ValueError("invalid BA_BENCHMARKING_UTILITIES_ENV value " + env)


def run_on_laptop(target_dirs: list[str], multicore: bool):
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
                    raise ValueError("multicore processing not implemented yet on laptop")

                    allowed_total_jobs = 6  # todo

                    # todo rearranging remaining jobs might improve performance
                    #   e.g. if small and big jobs are mixed, performance is waisted
                    #   a simple idea would be to sort jobs by size
                    wait_duration = 1
                    while _waiting_update_and_check_is_busy(allowed_total_jobs, active_jobs, tasks, wait_duration):
                        wait_duration = min(600, wait_duration * 2)

                else:
                    for j in active_jobs:
                        j.wait()

                job = _exec_on_laptop(b, f"{build_run_log_filename(i)}")
                _logger.info(f"started job " + job.name)
                active_jobs.append(job)

        for j in active_jobs:
            j.wait()

    except KeyboardInterrupt:
        _logger.info("canceled benchmarks")

    for j in active_jobs:
        j.kill()


def run_on_slurm_machine(target_dirs: list[str], multicore: bool):
    benchmark_iter = BenchmarkIterator(target_dirs)
    tasks_per_node = 72
    max_node_amount = 32

    built_folders = []
    chunks: dict[int, list[tuple[str, str]]] = {}

    # partition into chunks with same tasks amount
    for b in benchmark_iter:
        params = load_benchmark_parameters(b)
        tasks = int(params['BenchmarkMetaData']['tasks'])
        repeat = int(params['BenchmarkMetaData']['repeat'])

        # todo building and cleaning should be outside partitioning
        #   these things should be outsourced and merged from laptop and slurm execution
        # build all binaries alongside partitioning
        binary_path = params['BenchmarkMetaData']['binary']
        binary_folder = os.path.dirname(binary_path)

        if binary_folder not in built_folders:
            _build_project(binary_folder)
            built_folders.append(binary_folder)

        # and clean the benchmark directory
        prep_fresh_directory(b)
        clean_benchmark_suite(b)

        if tasks not in chunks:
            chunks[tasks] = []

        for i in range(repeat):
            chunks[tasks].append((b, build_run_log_filename(i)))

    demanded_nodes = sum(map(lambda t: math.ceil(t / tasks_per_node), chunks.keys()))
    free_nodes = max_node_amount - demanded_nodes

    assert free_nodes > 0, "todo: implement load balancing on slurm machines"

    if 1 in chunks:
        # spread single node chunks across remaining nodes
        chunk_size = len(chunks[1]) // (free_nodes + 1)
        remainder = len(chunks[1]) % (free_nodes + 1)
        pointer = chunk_size

        if remainder > 0:
            pointer += 1
        single_node_chunks = [chunks[1][:pointer]]

        for i in range(1, free_nodes):
            old_pointer = pointer
            pointer += chunk_size
            if remainder > i:
                pointer += 1

            single_node_chunks.append(chunks[1][old_pointer:pointer])

        single_node_chunks.append(chunks[1][pointer:])

        assert len(single_node_chunks) == free_nodes + 1
        assert sum(map(lambda c: len(c), single_node_chunks)) == len(chunks[1])

        del chunks[1]

        total_chunks = list(chunks.values()) + single_node_chunks
    else:
        total_chunks = list(chunks.values())

    enumerated_chunks = enumerate(total_chunks)

    for chunk_id, chunk in enumerated_chunks:
        _exec_chunk_on_fritz(chunk, chunk_id)


def _waiting_update_and_check_is_busy(task_limit: int, active_jobs: list[BenchmarkJob], needed_tasks: int,
                                      wait_duration: int) -> bool:
    # update active jobs
    for j in active_jobs:
        if j.poll():
            active_jobs.remove(j)
            _logger.info(f"finished job {j.name}")

    active_tasks = sum(map(lambda j: j.tasks, active_jobs))

    if active_tasks + needed_tasks <= task_limit:
        return False

    time.sleep(wait_duration)
    return True


def _build_project(bin_folder: str) -> None:
    cwd = os.getcwd()

    os.chdir(bin_folder)

    print(f"compiling {bin_folder}")
    _logger.info(f"compiling {bin_folder}")
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

    return LaptopJob(output_filepath, tasks, job)


def _exec_chunk_on_fritz(jobs: list[tuple[str, str]], chunk_index: int):
    fritz_cores_per_node = 72

    assert len(jobs) > 0

    enumerated_jobs = enumerate(jobs)

    param_files = [{}] * len(jobs)
    for i, j in enumerated_jobs:
        target_dir, _ = j
        params = load_benchmark_parameters(target_dir)

        assert "FritzMetaParameters" in params
        assert "pinThreads" in params["FritzMetaParameters"]

        param_files[i] = params

    tasks = int(param_files[0]["BenchmarkMetaData"]["tasks"])
    for p in param_files[1:]:
        p_tasks = int(p["BenchmarkMetaData"]["tasks"])
        assert tasks == p_tasks, "multiple task amounts in benchmark chunk found"

    jobscript_template_filepath = os.path.join(os.path.dirname(__file__), '..', "job_fritz.template")
    nodes = math.ceil(tasks / fritz_cores_per_node)
    tasks_per_node = min(fritz_cores_per_node, tasks)

    with open(jobscript_template_filepath) as f:
        jobscript_template = f.read()

    jobscript = jobscript_template.replace("__NODES__", str(nodes)).replace("__NTASKS_PER_NODE__",
                                                                            str(tasks_per_node))

    for i, j in enumerate(jobs):
        target_dir, output_name = j
        params = param_files[i]
        # srun __DEPENDANT_SRUN_FLAGS__ __CPU_FREQUENCY__ --output="$3" __THREAD_PINNING__ "$1" "$2"

        dependant_srun_flags = ""
        cpu_frequency = ""
        output_filepath = os.path.abspath(os.path.join(target_dir, output_name))
        thread_pinning = ""
        binary_path = params["BenchmarkMetaData"]["binary"]
        param_file_path = os.path.abspath(find_single_prm_file(target_dir))

        pinThreadsParameter = params["FritzMetaParameters"]["pinThreads"]

        if pinThreadsParameter == "true":
            thread_pinning = "likwid-pin -q -C N:scatter"

        if "frequency" in params["FritzMetaParameters"]:
            frequency = params["FritzMetaParameters"]["frequency"]
            cpu_frequency = f"--cpu-freq={frequency}-{frequency}:performance"

        if nodes >= 65:
            dependant_srun_flags = "-p big"

        srun_line = f'srun {dependant_srun_flags} {cpu_frequency} --output="{output_filepath}" {thread_pinning} "{binary_path}" "{param_file_path}"'
        jobscript += '\n' + srun_line

    jobscript_filepath = os.path.join("benchmarks", "chunks", f"chunk{chunk_index}_job_fritz.sh")

    with open(jobscript_filepath, 'w') as f:
        f.write(jobscript)

    subprocess.run(
        ["sbatch", jobscript_filepath],
        stdout=subprocess.PIPE)

    benchmarks_str = reduce(lambda s, b: f"{s}, {b}", map(lambda j: j[0], jobs))
    _logger.info(f"submitted chunk {chunk_index}, consisting of benchmarks {benchmarks_str}")

    # retrieve the job id to wait for the job's completion
    # result = result.stdout.decode("utf-8")
    # pattern = r"Submitted batch job (\d+)"
    # match = re.search(pattern, result)
    # jobid = match.group(1)
    # _logger.info(f"submitted batch job {jobid}")
    #
    # return FritzJob(output_filepath, tasks, jobid)


def _is_slurm_job_finished(jobid: str) -> bool:
    result = subprocess.run(["squeue", "-j", jobid], stdout=subprocess.PIPE)
    result = result.stdout.decode("utf-8")
    pattern = r"\s*JOBID\s+PARTITION\s+NAME\s+USER\s+ST\s+TIME\s+TIME_LIMIT\s+NODES\s+CPUS\s+NODELIST\(REASON\)\s*\n\s+\S+\s+\S+\s+\S+\s+\S+\s+(\w+)"
    match = re.search(pattern, result)

    # if the job is finished, it isn't displayed in the squeue output
    if match is None:
        return True

    jobstatus = match.group(1)

    # if it is displayed, only(?) the status CG means it is finished
    return jobstatus == "CG"


# usual waiting with exponentially increasing wait duration, capped at 10 min
def _wait_until_slurm_job_finished(jobid: str) -> None:
    max_duration = 600

    duration = 1
    while not _is_slurm_job_finished(jobid):
        time.sleep(duration)
        duration = min(max_duration, duration * 2)


def _cancel_slurm_job(jobid: str) -> None:
    subprocess.run(["scancel", jobid], stdout=subprocess.PIPE)
