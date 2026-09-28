#!/bin/bash
#SBATCH --job-name=Sensitivity_no_shear_heating
#SBATCH --ntasks=1
#SBATCH --exclude=node052
#SBATCH --cpus-per-task=1
#SBATCH --time=30:00:00
#SBATCH --mem=10G
#SBATCH --output=output_bash/out_time.txt
#SBATCH --error=output_bash/err_time.txt

# ---
# Pseudo code:
# 1.Clean the bash
# 2. Load Python
# 3. load Spack
# 4. Reiderect the program to the LD_LIBRARY_PATH
# 5. Load the library with Spack
# 6. Activate the python enviroment and set enviromental variable
# 7. Run the script
# ---



# Clean the bash env
module purge
# load python
module load python/3.13.0
# load spack
module load spack/0.23
# unset the LD pre-load, and use the link in the main folder
unset LD_PRELOAD
export LD_LIBRARY_PATH="/mnt/scratch/wlnw570/libs/glu:\$LD_LIBRARY_PATH"
# load the spack py-fenicsx-dolfinx
spack load py-fenics-dolfinx
spack load py-h5py
spack load py-numpy
spack load py-petsc4py@3.22.1
# source the python enviroment where StonedFEniCSx is active
source /users/wlnw570/stoned_fenicsx_env/bin/activate
PYTHON=/users/wlnw570/stoned_fenicsx_env/bin/python
# Run the code
mpirun -n 1 "$PYTHON" -u script_run_stoned.py \
    --name_suite TDexp\
    --name_test case_debug\
    --potential_temperature 1350\
    --age_plate 30\
    --velocity_slab 5.0\
    --no_linear_wedge 1\
