"""
===============================
===============================
Generals: 
Script to run timedependent simulation: 
1. The script will be configuring a timedependent simulation with different options:
    a. Rheology of Mantle Wedge : linear/dislocation creep+ diffusion creep (basic rheology from Van Keken)
    b. Decoupling depth : It is the parametrised depth of the weak zone
    c. Potential Temperature: 
    d. Age : The age of the plate
    e. velocity of convergence : Velocity of convergence 
    +/- change velocity overtime if the user needs additional and useless complexities. 
2. The script will have fixed parameters: initial condition with thermal diffusion, full model routine 
3. The script - hopefully - will generate a fake migrating phase field
===============================
Caveats: 
[A]: Run Time: between 0-18 Myr 
    the duration must be taylored around the velocity of the slab: if you have a slab with a 
    velocity of 10 cm and you are interested only to see the slab evolution till reaches 200 km, 
    it is completely useless running the experiments for 10e21 Myr. 
[B]: Most likely extremely young plate are not suitable for generating a reliable thermal field. 
[C]: There is no advection of material in this modelling, so the evolution of the slab 
    is parametrised with the velocity field and tracking the geometry
    -> i.e., if you want to change the velocity,you must use velocity evolution 
    that are easy to handle from mathematical point of view. 
===============================
Pseudo Code: 
a. input parameters:
    **python script_run_stoned.py \\**
    **--name_suite TDslab\\**
    **--name_test case_000\\**
    **--potential_temperature 1350 \\**
    **--velocity_slab 5.0 \\**
    **--age 30 \\**
    **--no_linear_wedge 0\\**
    
    The viscosity of the wedge is set to be 1e21 (no worries: an 90% of the parameter 
    in this kind of modelling it is fairly affecting the simulation dynamic)
    a1. Use argsparse to ingest the model with the desidered parameter 
        **I let you do the binding on this regards**
    a2. set the common configuration 
b. Configure simulation 
c. Run Simulation + output
d. Read output: 
    d1. extract data using post-process module data extractor 
    d2. read temperature and geometrical entities of the mesh 
    d3. read the time: displace the top surface of the slab and fill with phases the field
    d4. produce an h5df file with the information

Note: I try to re-use a bit of the scripts that I was using for my main projects. 
It entails that more than 60% of the code is useless, however I was too lazy to prune it out. 
For example, for setting the material properties I use the conductivity flag that I was using back 
the code is SET UP to be 3.1 which is the classical overused conductivity.
Let me know if you want more flexibility and I will promptly modify that piece of art. 
    
===============================
Written by Andrea Piccolo 21.09.2026 
"""
import argparse
import os
import time
from importlib.resources import files
from pathlib import Path

import numpy as np
from mpi4py import MPI

import post_process_module.global_var as _GVARIABLES_
from post_process_module.utils import (
    change_geometry,
    choose_material_properties,
    define_material_properties,
)

import cProfile



# --- function "wrap"


def wrap_stoned(inp, Ph, arguments: dict) -> tuple:
    """A fake wrap.

    Args:
        inp (_type_): input configuration data
        Ph (_type_): phase data base

    Raises:
        ValueError: failed attempt

    This is a quick hack solution. In the original plan, I would have been able to configure a no-race condition
    for the mesh generation and cache generation for the thermal properties. In practice, I was not able to find a proper solution.
    This should be possible, but, I am not willing to spend a few hours in this task. So, here you are the quick and dirty solution.
    TO DO: Reintegrate the h5 file routine for the thermal properties and create a control called: caching.
    """
    import copy

    from stonedfenicsx.stoned_fenicsx import stoned_fenicsx

    # Initialise the input
    attempt = 0
    success = 0
    last_error = None
    # Try to run the test, if it fails, wait for 20 seconds and try again. This is to avoid the problem of the cache that can cause the test to fail.
    # I need to solve the issue of the cache. In the future I will split the problem of mesh and cache generation, before the actual run
    # Or find a proper way to cleanly use race conditions. Meanwhile, this quick fix seems robust.

    while attempt < 3 and success == 0:
        # Copy the classes otherwise it crashes
        A = copy.deepcopy(inp)
        B = copy.deepcopy(Ph)
        try:
            print(f"Slab type is : {A.g_input.slab_type}")
            if A.g_input.slab_type == "FromFile":
                print(f"Slab type is : {A.g_input.sub_path}")
            stoned_fenicsx(A, B)
            print(f"Test was a success at {attempt}")
            success = 1
            # Copy the post processed classes
            inp = copy.deepcopy(A)
            Ph = copy.deepcopy(B)
        except Exception as e:
            # ok, understood. This method is not safe guarding the test path, this create a few issue, and error I patch
            # it. The reason that I am doing it is the following: it is not only for lazyness. I want to use the same version
            # of the code for this paper. If i start aiming the perfection, I will enter in an never ending loop that produce
            # a wonderful code, that will not have any paper attached.
            last_error = e

            time.sleep(20)  # seconds, float allowed
            attempt = attempt + 1
            print(f"Test failed at {attempt} with error: {e}")
        del A, B

    if success == 0:
        raise ValueError("Failed attempt") from last_error

    return inp, Ph
# ---
def perform_test(args: dict | None, name_suite: str = "debug") -> tuple[str, str]:
    """Configuration script of StonedFEniCSx for the time-dependent sensitivity
    tests.

    The script reads the input data from a .csv table and creates the input data for StonedFEniCSx. The script also creates the material properties dictionary and assigns it to the phases. The script also creates the input data for StonedFEniCSx and runs the simulation. The results are saved in a folder, in a number of h5 files that will be merged by other scripts.
        Args:
            args (SimpleNamespace, optional): updated Arguments of the script.
            name_suite (str, optional): Name of the test suite. Defaults to 'debug'.

        Raises:
            ValueError: _description_

        Returns:
            tuple[str,str]: general path of the tests and name of the test
    """
    # To configure the simulation, the code must ALWAYS read the input.yml file. This is a template file that contains the default values of the input data. The code will then modify the values of the input data according to the arguments passed to the script.
    from stonedfenicsx.config.input_parser import parse_input

    # Find the path of the file
    path_general = os.path.dirname(os.path.realpath(__file__))
    # Read the input file
    path_input = f"{path_general}/input_tests.yaml"
    # Set the general path for the tests
    path_general = os.path.join(path_general, "test_folder")
    # Create the test folder if does not exist
    if not os.path.exists(path_general):
        os.makedirs(path_general)

    # Parse the blue print of the test
    inp, Ph = parse_input(path_input)
    # If you are debugging, use group debug


    # controls
    # Assume that the decoupling is always active
    inp.ctrl.decoupling_ctrl = 1
    # Choose the mode of stonedFEniCSx
    inp.ctrl.steady_state = 0
    # Choose the tollerance of the picard iteration
    inp.ctrl.tol_dtemp = 1e-3
    inp.ctrl.it_max = 10


    inp.ctrl.model_shear = "NoShear"

    # Create input data - Input is a class populated by default dataset
    # A flag that generate the geometry of the benchmark
    # The input path for saving the results
    inp.ctrl_tbc.slab_age = args["age"]
    inp.ctrl_tbc.temp_max = args["Tp"]
    # Velocity of slab
    inp.ctrl_ky.v_s = np.array([args["vc"], 0], dtype=np.float64)

    # Geometrical input
    inp.g_input.cr = 40.0  # Overriding crust
    inp.g_input.lc = 0.5  # relative amount of lower crust
    inp.g_input.ocr = 6.0  # Crustal thickness
    inp.g_input.decoupling = args.get(
        "decoupling", _GVARIABLES_._DECOUPLING_
    )  # Lithospheric mantle depth
    inp.g_input.redo_mesh = [
        args.get("decoupling", _GVARIABLES_._DECOUPLING_) != _GVARIABLES_._DECOUPLING_
    ]
    inp.g_input.lab_d = inp.g_input.decoupling  # depth of the lab
    inp.g_input.ns_depth = 50  # depth of the noslip boundary condition
    inp.g_input.transition = 10  # transition delta depth -> the distance at which the transition from uncoupled and coupled flow happens
    inp.g_input.slab_type = "CustomRibe"  # type of slab geometry
    inp.g_input.resolution_normal = 10.0  # Resolution normal
    inp.g_input.resolution_refine = (
        1.5  # resolution around the slab top surface and the oceanic crust within the slab.
    )

    if args.get("plate_real") is not None:
        change_geometry(plate=args["plate_real"], args=args, inp=inp)
        inp.g_input.slab_type = "FromFile"  # type of slab geometry
        inp.g_input.sub_path = str(
            files("stonedfenicsx").resolve().parents[0]
            / "examples"
            / "data"
            / f"{args['plate_real']}_slab.pz"
        )

    define_material_properties(Ph, args)

    # Path to save the results

    inp.ctrl_io.path_save = os.path.join(
        path_general,
        f"{name_suite}",
    )
    inp.ctrl_io.test_name = f"{args['name_test']}"

    # Run the test
    profiler = cProfile.Profile()
    profiler.enable()

    inp, Ph = wrap_stoned(inp=inp, Ph=Ph, arguments=args)

    profiler.disable()
    profiler.dump_stats("stoned_profile.prof")

    return inp.ctrl_io.path_test, inp.ctrl_io.test_name
# ---
def configure_run_save():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--name_suite",
        type=str,
        help="Name of the test suite. This is a string that corresponds to the name of the test suite.",
    )
    parser.add_argument(
        "--name_test",
        type=str,
        help="Name of the test.",
    )
    parser.add_argument(
        "--potential_temperature",
        type=float,
        default=1350,
        help="Flag to run the test in steady-state or time-dependent mode. 1 = steady-state, 0 = time-dependent",
    )
    parser.add_argument(
        "--no_linear_wedge",
        type=int,
        default=1,
        help="Flag to run the test in steady-state or time-dependent mode. 1 = steady-state, 0 = time-dependent",
    )
    parser.add_argument(
        "--velocity_slab",
        type=float,
        default=1.0,
        help="velocity of the slab",
    )
    parser.add_argument(
        "--age_plate",
        type=float,
        default=20.0,
        help="Age of the slab",
    )

    args_cli = parser.parse_args()

    name_suite = args_cli.name_suite
    # Dictionary of arguments
    arguments =  {'vc':args_cli.velocity_slab,
               'Tp':args_cli.potential_temperature,
               'age':args_cli.age_plate,
               'wg_nl_eta':bool(args_cli.no_linear_wedge),
               'mat_prop':choose_material_properties(3.1),
               'name_test':args_cli.name_test}

    pathtest, _ = perform_test(args=arguments, name_suite=name_suite)

    print(f"Test completed. Results saved in {pathtest}")

    #comm = MPI.COMM_WORLD


if __name__ == "__main__":
    configure_run_save()
