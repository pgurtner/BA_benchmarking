import os
import re
import subprocess
import time

from src.utils import GridConfig, build_run_filename

EXEC_ENVIRONMENT = None

"""
takes
    binary which gets benchmarked
    meshNx
    meshNy
    minLevel
    maxLevel
    solver
    [--tasks] default=1
    
creates
    runs/solver.meshNx.meshNy.minLevel.maxLevel.log
"""


def run(file: str, solver: str, tasks: int, grid_config: GridConfig):
    if EXEC_ENVIRONMENT is None:
        raise ValueError("EXEC_ENVIRONMENT must be set")
    elif EXEC_ENVIRONMENT == "laptop":
        _exec_on_laptop(file, solver, tasks, grid_config)
    elif EXEC_ENVIRONMENT == "fritz":
        _exec_on_fritz(file, solver, tasks, grid_config)


def _exec_on_laptop(file: str, solver: str, tasks: int,
                    grid_config: GridConfig) -> None:
    cwd = os.getcwd()

    bin_folder = os.path.dirname(file)

    output_filepath = os.path.join(cwd, "runs", build_run_filename(solver, grid_config))

    jobscript_filepath = os.path.join(cwd, "job_laptop.sh")

    # change to binary directory for the make call in the job script
    os.chdir(bin_folder)

    # typically EigenLU is used as the direct solver and it doesn't support multicore
    ntasks = 1
    if solver != "direct":
        ntasks = tasks

    meshNx, meshNy, minLevel, maxLevel = grid_config.to_tuple()

    subprocess.call(
        [jobscript_filepath, file, str(meshNx), str(meshNy), str(minLevel), str(maxLevel), solver, output_filepath,
         str(ntasks)])

    os.chdir(cwd)


def _exec_on_fritz(file: str, solver: str, tasks: int,
                   grid_config: GridConfig) -> None:
    cwd = os.getcwd()

    bin_folder = os.path.dirname(file)

    output_filepath = os.path.join(cwd, "runs", build_run_filename(solver, grid_config))

    jobscript_filepath = os.path.join(cwd, "job_fritz.sh")

    # change to binary directory for the make call in the job script
    os.chdir(bin_folder)

    ntasks = 1
    if solver != "direct":
        ntasks = tasks

    meshNx, meshNy, minLevel, maxLevel = grid_config.to_tuple()

    result = subprocess.run(
        ["sbatch", jobscript_filepath, file, str(meshNx), str(meshNy), str(minLevel), str(maxLevel), solver,
         output_filepath, str(ntasks)],
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


# typical waiting with exponentially increasing wait duration, capped at 10 mins
def _wait_until_slurm_job_finished(jobid: str) -> None:
    max_duration = 600

    duration = 1
    while not _is_slurm_job_finished(jobid):
        print(f"waiting {duration}s...")
        time.sleep(duration)
        duration = min(max_duration, duration * 2)
