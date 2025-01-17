#!/bin/bash -l

#SBATCH --nodes=1
#SBATCH --time=06:00:00
#SBATCH --export=NONE

if [ "$#" -ne 4 ]; then
    echo "Illegal number of parameters. Needs bin, .prm file, output and ntasks-per-node."
    exit 1
fi

unset SLURM_EXPORT_ENV

echo "compiling..."

make -j 72

echo "finished build, running benchmark..."

srun --ntasks-per-node="$4" --output="$3" "$1" "$2"