# Small guide using fancy words to annoy you

First, install the Python package following the instructions in the README here: [StonedFEniCSx](https://github.com/APiccolo89/StonedFenicsx).

After that, you can run your first model.

> [!NOTE]
> First, install Miniforge, so that you can use the `environment.yml` file that you find in the main repository. Then, run the tests to check whether there are any differences between operating systems.

## Run your first model

To run a test, hopefully, this command is enough:

```bash
mpirun -n 1 python -u script_run_stoned.py --name_suite MyFirstExperiments --name_test T_Arne --velocity_slab 5.0 --age_plate 33 --potential_temperature 1300 --no_linear_wedge 1
```

If the run is successful, the output will be found in:

```text
current_folder/
└── {name_suite}/
    └── {test_name}/
        └── TimeDependent.h5
```

In the following code, I show the main functions that control the configuration and execution of the tests.

```python
@timing_function
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
        help="Velocity of the slab",
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
    arguments = {
        'vc': args_cli.velocity_slab,
        'Tp': args_cli.potential_temperature,
        'age': args_cli.age_plate,
        'wg_nl_eta': bool(args_cli.no_linear_wedge),
        'mat_prop': choose_material_properties(3.1),
        'name_test': args_cli.name_test
    }

    pathtest, _ = perform_test(args=arguments, name_suite=name_suite)

    print(
        f"Test completed for group {arguments['case_index']}. "
        f"Results saved in {pathtest}"
    )

    comm = MPI.COMM_WORLD


if __name__ == "__main__":
    configure_run_save()
```

Most of the hassle is handled by a configuration script that I developed for my project. I modified the essentials so that it has the following parameters:

- `--name_suite`: macro-category of experiments (e.g. `T_non_linear`)
- `--name_test`: name of the individual test (e.g. `T_non_linear/Arne_Spang`)
- `--velocity_slab`: convergence velocity [cm/yr]
- `--potential_temperature`: mantle potential temperature (aka background mantle temperature)
- `--age_plate`: age of the plate [Myr]
- `--no_linear_wedge`: flag that tells the configuration script to use dislocation creep + diffusion creep olivine rheologies for the mantle wedge.

> [!NOTE]
> The name of the suite is simply the name of a specific group of tests featuring some common properties (e.g. non-linear wedge, linear wedge).
>
> The incoming plate age is computed using a plate model. A plate model is a fancy version of the half-space cooling model in which the background temperature is fixed at a specific depth (-130.0 km).

> [!WARNING]
> The geometry of the plate is defined using a fixed thickness.
>
> However, not all geometries have been created equal in the eyes of God: if the curvature of the slab is obscene, the thickness will be corrected by the code. For example, Mexico has an obnoxious curvature; thus, the thickness consistent with its curvature is 75 km.

## Post-processing

The post-processing routine must be integrated with the test-running routine. This will make it easier to keep track of all the metadata associated with the numerical simulation. For the earliest stage of the project, I thought that it would be beneficial to use the same arguments as `script_run_stoned.py`:

```bash
python -u script_post_processing.py --name_suite MyFirstExperiments --name_test T_Arne --velocity_slab 5.0 --age_plate 33 --potential_temperature 1300 --no_linear_wedge 1
```

This script post-processes the data and creates an HDF5 file in the `Output` folder.

The HDF5 file is organised as follows:

- `test_name`
  - `Phase`: phase array with dimensions `[r_grid, r_grid, number of timesteps]`
  - `Temp`: temperature array with dimensions `[r_grid, r_grid, number of timesteps]`
  - `Xi` & `Yi`: reference grids for the coordinates
  - `age`: age of the lithosphere [Myr]
  - `Tp`: background temperature of the mantle [deg C]
  - `vc`: velocity of the slab [cm/yr]
  - `wg_nl_eta`: Boolean indicating whether the wedge has linear or non-linear rheology
  - `time_vector`: vector containing the time of each timestep [Myr]
  - `material_property`
    - `phase` (`lower_crust`, `upper_crust`, `oceanic_crust`, ...)
      - `alpha0`: reference value of thermal expansivity [1/K]
      - `cp`: heat capacity for the given phase [J/K/kg]
      - `rho0`: density of the phase [kg/m³]
      - `k`: conductivity [W/m/K]
      - The other variables correspond to the names of the thermal-property laws.