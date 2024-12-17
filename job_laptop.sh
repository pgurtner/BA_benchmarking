#!/bin/bash -l

if [ "$#" -ne 4 ]; then
    echo "Illegal number of parameters. Needs bin, solver, output and mpi task amount."
    exit 1
fi

make -j 4

mpirun -N "$4" "$1" "$2" >"$3"