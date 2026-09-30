"""
---
1. Read the test and extract the relevant data
    a. Generate a quadrangular grid, and refined grid
2. Use the geometrical information related to the top of the slab
    a. Tracking and generating polygon to fill the resolved grid 
    b. Create the phase field and the temperature field
    c. Produce an h5df file with the information regarding the evolution of the system
    d. Produce pictures. 
    
Written by Andrea Piccolo, 22.09.2026
---
Scope: this script is a test case scenario. The idea is to build up the main routine, testing them
then integrating in the post-processing routine. This will serve as a main test of this small
package. 
---

"""

import argparse
from importlib.resources import files
from pathlib import Path

import h5py
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

import post_process_module.global_var as _GVARIABLES_
from post_process_module.data_extractor import Test
from post_process_module.utils import choose_material_properties

# --- 
# --- 
_DICTIONARY_ATTRIBUTES_H5_ = {'vc':'Velocity of convergence of the slab [cm/yr]',
               'Temp': 'Temperature array [deg C]',
              'Phase':'Phase array: 0: background;1: Lithosphere;2:Oceanic crust',
               'Tp': 'Mantle potential temperature [deg C]',
               'Age': 'Age of the plate [Myr]',
               'wg_nl_eta': 'Flag non linear wedge [int/bool]',
               'Xi':'Grid with x values of the regular grid [km]',
               'Yi':'Grid with y values of the regular grid [km]',
                }               
# --- 
def save_data_(g,v,name:str)->None:
    # Check if the instance is string and operate accordingly 
    
    # If the name exist, remove the field, then recreate. 
    if name in g:
        del g[name]
        
    if isinstance(v, str):
        g.create_dataset(
            name,
            data=v,
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
    else: 
        g.create_dataset(
            name,
            data=v
        )
    # Save a description of the data, Initially i wanted to put a description for each of the value
    # However, having so much redundant garbage is pretty much useless: I will centralised the dictionary, with a mock 
    # dataset called reference. 
    #dts.attrs["description"] = _DICTIONARY_ATTRIBUTES_H5_[name]

# --- 
def save_mat_prop(grp, mat_prop:dict)->None:
    """Create the material property object
    to save in the dataset

    Args:
        grp (_type_): the group (i.e., test name)
        mat_prop (dict): the dictionary of the material properties
    """
    sub_grp = grp.create_group('material_property')
    
    
    for i in mat_prop.keys():
        sub_sub = sub_grp.create_group(i)
        dict_sub = mat_prop[i]
        for j in dict_sub.keys():
            save_data_(sub_sub,dict_sub[j],j)
            print(f'creating {j} in {i}')
            
# ---
def read_test_data():
    """This is a script to post-process the data. 
    Now, since the idea is to save soon after the run, I
    integrate the same parsed arguments of the run script. 
    So, during the early state of the project, just write
    down the command that you use for specific tests, and then
    use them for the post-processing script :) 
    """
    
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

    # Dictionary of arguments
    arguments =  {'vc':args_cli.velocity_slab,
               'Tp':args_cli.potential_temperature,
               'age':args_cli.age_plate,
               'wg_nl_eta':bool(args_cli.no_linear_wedge),
               'mat_prop':choose_material_properties(3.1),
               'name_test':args_cli.name_test}
    
    # Assuming that you are saving the file in the same repository
    pt = Path(__file__).resolve().parents[0] 
    # Change the name for obvious reason 
    pt = pt/'test_folder'/f"{args_cli.name_suite}/{arguments['name_test']}"
    # Build up the path for saving your output
    pt_save = Path(__file__).resolve().parents[0] / 'Output'
    # Create the path - it automatically creates the path
    pt_save.mkdir(parents=True,exist_ok=True)
    # Create the Test Data Set 
    test = Test(pt,td=True)
    # Extract the array of phase and temp 
    # This array has a shape of [r_grid,r_grid,n_timestep]
    test.update_temp_phase_field(td=True
                                 ,flag_full=True
                                 ,vc=arguments['vc']
                                 ,oc_tk=6.0,dc=80.0)
    Xi = test.MeshData.Xi
    
    Yi = test.MeshData.Yi 
    
    time = np.array(test.Data_raw.TimeDependent.time_list,dtype=np.float32)
    # In the future I will add all the reading of the metadata, 
    # my idea is to run this function after the completion of the test
    # such that these data are safely stored, for now, it 
    # is a manual operation es tut mir leid. 
    
    with h5py.File(f"{pt_save}/{args_cli.name_suite}.h5",'a') as f:
        # Remove the old group, if the routine is re-run
        if arguments['name_test'] in f:
            del f[arguments['name_test']]
        
        grp = f.create_group(arguments['name_test'])
        for key in arguments:
            value = arguments[key]
            if isinstance(value, str):
                grp.create_dataset(
                    key,
                    data=value,
                    dtype=h5py.string_dtype(encoding="utf-8"),
                )
            elif key == "mat_prop":
                save_mat_prop(grp,arguments['mat_prop'])
            else:
                save_data_(grp,value,key)
                print(f"creating {key} for {arguments['name_test']}")
        save_data_(grp,test.Phase,'Phase')
        save_data_(grp,test.temp,'Temp')
        save_data_(grp,Xi,'Xi')
        save_data_(grp,Yi,'Yi')
        save_data_(grp,time,'time_vector')
            
    print('Test has been post-processed and assimilated in the centralised database')
    print('Rest in Peace')

# --- 

if __name__ == '__main__':
    read_test_data()


