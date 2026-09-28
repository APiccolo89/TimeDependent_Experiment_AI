#!/bin/bash
module purge
module load python/3.13.0
module load spack/0.23

spack load py-fenics-dolfinx
spack load py-h5py
spack load py-petsc4py@3.22.1
source /users/wlnw570/stoned_fenicsx_env/bin/activate
