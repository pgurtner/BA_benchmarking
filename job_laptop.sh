#!/bin/bash -l

if [ "$#" -ne 8 ]; then
    echo "Illegal number of parameters. Needs bin, meshNx, meshNy, minLevel, maxLevel, solver, output and mpi task amount."
    exit 1
fi

make -j 4

mpirun -N "$8" "$1" "$2" "$3" "$4" "$5" "$6" >"$7"