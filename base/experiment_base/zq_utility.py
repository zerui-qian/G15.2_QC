# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:47:52 2024

@author: eyazici
"""
import numpy as np
import datetime, os
 

def save_array_with_metadata(array, filename_prefix):
    # Save array to binary file
    array.tofile(filename_prefix + ".bin")

    # Save metadata (datatype and shape) to text file
    with open(filename_prefix + ".txt", "w") as metadata_file:
        metadata_file.write("Data Type: {}\n".format(array.dtype))
        metadata_file.write("Shape: {}\n".format(" ".join(map(str, array.shape))))

def load_array_with_metadata(filename_prefix):

    # Load metadata from text file
    with open(filename_prefix + ".txt", "r") as metadata_file:
        dtype_str = metadata_file.readline().split(": ")[1].strip()
        shape_str = metadata_file.readline().split(": ")[1].strip()
        dtype = np.dtype(dtype_str)
        shape = tuple(map(int, shape_str.split()))

    # Load array from binary file
    array = np.fromfile(filename_prefix + ".bin", dtype = dtype)
    # Reshape the array
    return array.reshape(shape).astype(dtype)


def generate_filename(comment, base_dir):
    # Create directory for today's date if it doesn't exist
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(base_dir, today)
    os.makedirs(today_dir, exist_ok=True)
    
    # Find the latest run number for today
    run_number = 1
    if os.path.exists(today_dir):
        existing_files = [f for f in os.listdir(today_dir)]
        if existing_files:
            run_numbers = [int(f.split('_')[1]) for f in existing_files if len(f.split('_'))>1]
            run_number = max(run_numbers) + 1
            
    datadir = os.path.join(today_dir, f"Run_{run_number:03d}")
    os.makedirs(datadir, exist_ok=True)
    
    # Generate filename with run number
    return os.path.join(datadir, comment)


def generate_filedir(suffix, base_dir):
    # Create directory for today's date if it doesn't exist
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    today_dir = os.path.join(base_dir, today)
    os.makedirs(today_dir, exist_ok=True)
    
    # Find the latest run number for today
    run_number = 1
    if os.path.exists(today_dir):
        existing_files = [f for f in os.listdir(today_dir)]
        if existing_files:
            run_numbers = [int(f.split('_')[1]) for f in existing_files if len(f.split('_'))>1]
            run_number = max(run_numbers) + 1
            
    datadir = os.path.join(today_dir, f"Run_{run_number:03d}_{suffix}")
    os.makedirs(datadir, exist_ok=True)
    
    return datadir

def convert_nm_eV(data):
    "https://www.kmlabs.com/en/wavelength-to-photon-energy-calculator"
    h = 6.62607015e-34
    c = 299792458
    e = 1.602176634e-19
    return  (1e12*h*c/e) / data

# def zigzag_sweep(x_arr, y_arr, axis):
#     path = []
#     if axis == 'y':
#         for y in y_arr:
#             if y % 2 == 0: # Left to right
#                 for x in x_arr: path.append((x, y))
#             else: # Right to left
#                 for x in x_arr[::-1]: path.append((x, y))
#     elif axis == 'x':
#         for x in x_arr:
#             if x % 2 == 0:
#                 for y in y_arr: path.append((x, y))
#             else:
#                 for y in y_arr[::-1]: path.append((x, y))
#     return path