import argparse
import operator
import os
import re
import subprocess
import time
from functools import reduce

from plot import plot

EXEC_ENVIRONMENT = None

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("file", help="which file to run")
    parser.add_argument('solver', help="which solver to use")
    parser.add_argument("--metrics", help="comma separated list of metrics to plot", default="max_norm")
    parser.add_argument("--tasks", help="number of mpi threads", type=int, default=1)
    parser.add_argument("--show", help="display plot automatically", action="store_true")

    args = parser.parse_args()

    file = os.path.abspath(args.file)
    metrics = args.metrics.split(',')
    solver = args.solver
    tasks = args.tasks
    show = args.show

    if EXEC_ENVIRONMENT is None:
        raise ValueError("EXEC_ENVIRONMENT must be set")
    elif EXEC_ENVIRONMENT == "laptop":
        exec_on_laptop(file, solver, metrics, tasks, show)
    elif EXEC_ENVIRONMENT == "fritz":
        exec_on_fritz(file, solver, metrics, tasks)

def exec_on_laptop(file: str, solver: str, metrics: list[str], tasks: int, show: bool) -> None:
    cwd = os.getcwd()

    bin_folder = os.path.dirname(file)

    output_filename = solver + "." + reduce(operator.add, metrics)
    output_filepath = os.path.join(cwd, output_filename)

    jobscript_filepath = os.path.join(cwd, "job_laptop.sh")

    # change to binary directory for the make call in the job script
    os.chdir(bin_folder)

    # typically EigenLU is used as the direct solver and it doesn't support multicore
    ntasks = 1
    if solver != "direct":
        ntasks = tasks

    subprocess.call([jobscript_filepath, file, solver, output_filepath, str(ntasks)])

    os.chdir(cwd)

    plot([output_filepath], metrics, show)

def exec_on_fritz(file: str, solver: str, metrics: list[str], tasks: int) -> None:
    cwd = os.getcwd()

    bin_folder = os.path.dirname(file)

    output_filename = solver + "." + reduce(operator.add, metrics)
    output_filepath = os.path.join(cwd, output_filename)

    jobscript_filepath = os.path.join(cwd, "job_fritz.sh")

    # change to binary directory for the make call in the job script
    os.chdir(bin_folder)

    ntasks = 1
    if solver != "direct":
        ntasks = tasks

    result = subprocess.run(["sbatch", jobscript_filepath, file, solver, output_filepath, str(ntasks)], stdout=subprocess.PIPE)

    # retrieve the job id to wait for the job's completion
    result = result.stdout.decode("utf-8")
    pattern = r"Submitted batch job (\d+)"
    match = re.search(pattern, result)
    jobid = match.group(1)
    print(f"job id: {jobid}")

    wait_until_slurm_job_finished(jobid)

    os.chdir(cwd)
    plot([output_filepath], metrics)

def is_slurm_job_finished(jobid: str) -> bool:
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
def wait_until_slurm_job_finished(jobid: str) -> None:
    max_duration = 600

    duration = 1
    while not is_slurm_job_finished(jobid):
        print(f"waiting {duration}s...")
        time.sleep(duration)
        duration = min(max_duration, duration*2)

if __name__ == '__main__':
    main()