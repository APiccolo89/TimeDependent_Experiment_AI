"""Utility functions for configuring StonedFEniCSx runs.

Includes helpers to adjust the slab geometry from a named real plate,
assign material properties per phase, and parse CLI arguments for the
driver scripts.
"""
import argparse
import os
from dataclasses import fields
from types import SimpleNamespace

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from . import global_var as _GVARIABLES_


# ---
def change_geometry(plate: str, args: SimpleNamespace, inp) -> None:
    # Read the yml configuration file
    # Adjust the g_input
    """Change the geometry of the input data according to the plate name.

    The plate name is a string that corresponds to the key of the dictionary. The dictionary is defined in the file geometric_input_real_plate.yml. The function reads the dictionary and changes the geometry of the input data according to the plate name.
        Args:
            plate (str): Name of the plate to use for the real geometry (only the basic one stored in StonedFEniCSx is available). If None, the default geometry is used.
            inp (SimpleNamespace): Input data of StonedFEniCSx
    """
    if plate != "None":
        import yaml

        with open(
            f"{os.path.dirname(os.path.dirname(os.path.realpath(__file__)))}/real_plate_configuration/geometric_input_real_plate.yml",
            "r",
        ) as f:
            dict_geom = yaml.safe_load(f)

        if plate not in dict_geom:
            raise ValueError(
                f"Plate {plate} not found in the dictionary. Available plates are: {list(dict_geom.keys())}"
            )

        geom = dict_geom[plate]
        inp.g_input.slab_tk = geom["slab_tk"]
        inp.g_input.cr = geom["cr"]
        inp.g_input.lc = geom["lc"]
        inp.g_input.ns_depth = geom["ns_depth"]
        inp.g_input.lab_d = geom["lab_d"]
        inp.g_input.resolution_refine = geom["resolution_refine"]
        inp.g_input.transition = geom["transition"]


def define_material_properties(Ph, args):
    # Set the default and fixed parameter
    # Select the type of simulation
    # Adjust the material property as a consequence
    # Print the output because I am paranoid
    """Function that construct the material properties in a programmatical way,
    using the avaiable option.

    Args:
        Ph (PhInput): The pre-processed phase database
        args (Simplenamedspace): The input parameters for the current simulation configuration

    Raises:
        ValueError: Wrong group or not-existent template
    """
    # Fixed rheology of the mantle. Usually the difference with rheologies and thermal field are minimal.
    if args['wg_nl_eta']==True:
        Ph.wedge_mantle.name_diffusion = _GVARIABLES_._NAME_DIFFUSION_CREEP_
        Ph.wedge_mantle.name_dislocation = _GVARIABLES_._NAME_DISLOCATION_CREEP_
    else:
        Ph.wedge_mantle.name_diffusion = 'Constant'
        Ph.wedge_mantle.name_dislocation = 'Constant'
        Ph.wedge_mantle.eta = 1e21
        
    # Modify the phase with the new data:
    for i in fields(Ph):
        if i.name in [
            "shear_heating_disl_law",
            "shear_heating_disl_phi",
            "shear_heating_disl_tau_min",
        ]:
            continue
        phase = getattr(Ph, i.name)

        if i.name in ["subducting_plate_mantle", "wedge_mantle", "overriding_mantle"]:
            mat_prop = args["mat_prop"]["mantle"]
        elif i.name in ["oceanic_crust"]:
            mat_prop = args["mat_prop"]["oceanic_crust"]
        elif i.name in ["overriding_upper_crust"]:
            mat_prop = args["mat_prop"]["upper_crust"]
        elif i.name in ["overriding_lower_crust"]:
            mat_prop = args["mat_prop"]["lower_crust"]
        else:
            raise ValueError(f"Phase {i.name} not recognized")

        phase.rho0 = mat_prop["rho0"]
        phase.name_capacity = mat_prop["capacity"]
        phase.name_conductivity = mat_prop["conductivity"]
        phase.name_alpha = mat_prop["alpha"]
        phase.name_density = mat_prop["density"]
        phase.radiative_conductivity = mat_prop["radiative"]
        phase.radiogenic_heat = mat_prop["radiogenic"]
        phase.cp = mat_prop["cp"]
        phase.alpha0 = mat_prop["alpha0"]
        phase.k = mat_prop["k"]

    for i in fields(Ph):
        if i.name in [
            "shear_heating_disl_law",
            "shear_heating_disl_phi",
            "shear_heating_disl_tau_min",
        ]:
            continue
        phase = getattr(Ph, i.name)
        print(f"Phase {i.name} properties:")
        print(f"       .rho0 = {phase.rho0}")
        print(f"       .name_capacity = {phase.name_capacity}")
        print(f"       .name_conductivity = {phase.name_conductivity}")
        print(f"       .name_alpha = {phase.name_alpha}")
        print(f"       .name_density = {phase.name_density}")
        print(f"       .radiative_conductivity = {phase.radiative_conductivity}")
        print(f"       .radiogenic_heat = {phase.radiogenic_heat}")
        print(f"       .k = {phase.k}")
        print(f"       .cp = {phase.cp}")
        print(f"       .alpha0 = {phase.alpha0}")


# ---
def choose_material_properties(k: float) -> dict:

    materials = ("mantle", "oceanic_crust", "upper_crust", "lower_crust")
    properties = (
        "alpha",
        "density",
        "capacity",
        "conductivity",
        "radiogenic",
        "k",
        "radiative",
        "rho0",
        "cp",
        "alpha0",
    )

    # empty skeleton
    phase_properties = {m: {p: None for p in properties} for m in materials}

    # Fixed value
    # rho0
    phase_properties["mantle"]["rho0"] = 3300.0
    phase_properties["oceanic_crust"]["rho0"] = 2800.0
    phase_properties["upper_crust"]["rho0"] = 2700.0
    phase_properties["lower_crust"]["rho0"] = 2800.0

    # k
    phase_properties["upper_crust"]["k"] = 2.5
    phase_properties["lower_crust"]["k"] = 2.5
    phase_properties["oceanic_crust"]["k"] = 2.5
    # cp & alpha
    for m in materials:
        phase_properties[m]["cp"] = 1250.0
        phase_properties[m]["alpha0"] = 3e-5

    # radiogenic heating
    phase_properties["oceanic_crust"]["radiogenic"] = 0.0
    phase_properties["upper_crust"]["radiogenic"] = 0.0
    phase_properties["lower_crust"]["radiogenic"] = 0.0
    phase_properties["mantle"]["radiogenic"] = 0.0

    if k in (3.1, 5.0):
        for m in materials:
            phase_properties[m]["alpha"] = "Constant"
            phase_properties[m]["capacity"] = "Constant"
            phase_properties[m]["density"] = "Constant"
            phase_properties[m]["conductivity"] = "Constant"
            phase_properties[m]["radiative"] = 0

        phase_properties["mantle"]["k"] = k

    elif k < 0.0:
        for m in materials:
            phase_properties[m]["radiative"] = 1.0
            phase_properties[m]["density"] = "PT"
        phase_properties["mantle"]["alpha"] = "Mantle"
        phase_properties["mantle"]["conductivity"] = "Mantle_Richards_2018"
        phase_properties["mantle"]["capacity"] = "Mantle_Bernard_Ar_199x_FO_FA"
        for m in materials:
            if m != "mantle":
                phase_properties[m]["alpha"] = "Oceanic_crust"
                phase_properties[m]["conductivity"] = "Crust_Richards_2018"
                phase_properties[m]["capacity"] = "Oceanic_crust"

            phase_properties["mantle"]["k"] = np.abs(k)

    else:
        raise ValueError("Wrong k")

    for m in materials:
        print(f"{m} properties:")
        for p in phase_properties[m]:
            print(f"       .{p} = {phase_properties[m][p]} ")

    return phase_properties


# ---
def create_case_dictionary() -> dict:
    """Small function that creates the dictionary of the cases Kind of overkill
    -> future yaml file.

    Returns:
        dict: dictionary of cases
    """
    # Main type
    main_case_dt = np.dtype(
        [
            ("k", "f8"),
            ("shear_heating", "?"),
        ]
    )

    def make_case(k, shear_heating):
        return np.array((k, shear_heating), dtype=main_case_dt)

    dict_case = {
        "k3nsh": make_case(3.1, False),
        "k5nsh": make_case(5.0, False),
        "nlnsh": make_case(-1.0, False),
        "nlcnsh": make_case(-2.0, False),
        "k3sh": make_case(3.1, True),
        "k5sh": make_case(5.0, True),
        "nlsh": make_case(-1.0, True),
        "nlpsh": make_case(-3.0, True),
        "debug": make_case(-1.0, True),
    }
    return dict_case


# ---
def print_meta_data_id_db(key_from_submission: str, cases: NDArray) -> str:

    def thermal_model(k) -> str:
        if k in (3.1, 5.0):
            str_aux = f" linear cases with k = {k}"
        elif k < 0.0:
            str_aux = "non linear thermal properties"
        else:
            raise ValueError("There is a problem ... ")
        return str_aux

    def shear_heating(sh: bool) -> str:
        if sh:
            str_aux = "Shear Heating is acive"
        else:
            str_aux = "Shear Heating is not active"

        return str_aux

    str_2_print = f"{key_from_submission} => {thermal_model(cases['k'])} and {shear_heating(cases['shear_heating'])}"

    return str_2_print


# Global flag to decide wether or not to remove the results -> debug reason.
def parse_the_argument(args: argparse.Namespace, pathtotable: str) -> dict:
    """_summary_

    Args:
        args (argparse.Namespace): argument parser
        pathtotable (str): table with the cases to run


    Returns:
        dict: updated argument dictionary with the group parameters and material properties
    """
    # Extract group:
    dict_case = create_case_dictionary()

    if args.group == "debug":
        case_index = 0
        group_sim = dict_case["debug"]
        mat_prop = choose_material_properties(group_sim["k"])
        steady_state = 1
        name_suite = "debug"
        shear_heating = group_sim["shear_heating"]
    else:
        required = ["case_index", "group", "id_batch"]
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise ValueError(
                f"missing required arguments: {', '.join('--' + m for m in missing)}"
            )

        case_index = args.case_index
        group_sim = dict_case[args.group]

        print(print_meta_data_id_db(args.group, group_sim))

        mat_prop = choose_material_properties(group_sim["k"])

        steady_state = args.steady_state
        shear_heating = group_sim["shear_heating"]

    cases = pd.read_csv(pathtotable)
    cases_columns = cases.columns
    args_test = {}
    args_test = {m: None for m in cases_columns}

    row = cases.iloc[case_index]

    for m in args_test:
        args_test[m] = row[m]

    args_test["mat_prop"] = mat_prop
    args_test["shear_heating"] = shear_heating
    args_test["steady_state"] = steady_state
    if args.plate_real != "None":
        args_test["plate_real"] = args.plate_real
    if args.shear_heating_law != "NotDefined":
        args_test["shear_heating_law"] = args.shear_heating_law
    args_test["group"] = args.group
    args_test["id_batch"] = args.id_batch
    args_test["case_index"] = args.case_index
    if group_sim['k'] == -3:
        args_test['pressure_dependency'] = 1
    else: 
        args_test['pressure_dependency'] = 0
    return args_test


# --- function "wrap"
