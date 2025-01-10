#!/bin/bash -l

#SBATCH --nodes=1
#SBATCH --time=06:00:00
#SBATCH --export=NONE

if [ "$#" -ne 8 ]; then
    echo "Illegal number of parameters. Needs bin, meshNx, meshNy, minLevel, maxLevel, solver, output and ntasks-per-node."
    exit 1
fi

unset SLURM_EXPORT_ENV

make -j 72

srun --ntasks-per-node="$8" --output="$7" "$1" "$2" "$3" "$4" "$5" "$6"