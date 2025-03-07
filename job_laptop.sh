#!/bin/bash -l

if [ "$#" -ne 4 ]; then
    echo "Illegal number of parameters. Needs bin, .prm file, output and mpi task amount."
    exit 1
fi

echo "running benchmark..."
mpirun -N "$4" "$1" "$2" >"$3"