# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 11:20:43 2025

@author: Zerui
"""
import sys
# sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\drivers')
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\C-hBN\base\experiment_base')
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\C-hBN\base\experiment_base\zq_drivers')

from zq_experiment_base import *
from zq_utility import *
from device_manager import *

sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\C-hBN')
from main import *

#%%
### ================================ MAIN ================================ ###

# init_settings()

print('x, y, APD_counts')
for x in np.arange(33, 43, 0.2):
    for y in np.arange(30, 40, 0.2):
        SCx.setter(x), SCy.setter(y)
        counts = c_APD.getter()
        print(f'{SCx.getter():.1f}, {SCy.getter():.1f}, {counts:.1f}')
        if counts >= 0:
            user_input = input("Do you want to continue the scan? (y/n): ").strip().lower()
            if user_input == 'y':
                continue
            elif user_input == 'n':
                continue_scanning = False
                raise SystemExit
        

#%%


ws.exposure_time = (5)
ws.num_frames = (1)

def spec_plot(mp):
    mp.initialize()
    plabel = "PL scanner"
    pwindow = PlotWindow("PL scanner", "Wavelength (nm)", "Reflection (counts)")
    mp.add_plot(plabel, pwindow)
    # print("Added plot")
    mp.main_loop()

mp = MultiPlotter()
tQt = threading.Thread(target=spec_plot, args=([mp]), daemon = True)
plabel = "PL scanner"
tQt.start()

wlens = None
continue_scanning = True
count_thr = 1000
threshold_exceeded = False


time.sleep(0.1)
try:
    while (True):
        print('x', 'y')
        for x in np.arange(33, 43, 0.2):
            for y in np.arange(30, 40, 0.2):
                SCx.setter(x), SCy.setter(y)
                print(x, y)
        
                if wlens is None:
                    spec = Spec.getter().data
                    wlens = Wlen.getter()
                    spec = np.array(spec, dtype = 'uint16')
                    energies = convert_nm_eV(np.array(wlens))
            
                    mp._plot_windows[plabel].xdata = wlens
                else:
                    spec = Spec.getter().data
                    time.sleep(0.1)
        
                spec = np.array(spec,dtype = 'uint16').mean(axis=0)[:]
                mp._plot_windows[plabel].ydata = spec
                mp._plot_windows[plabel].update_plot()

                if any(spec > count_thr):
                    print(f"Scanner stopped at ({x}, {y}): count exceeded {count_thr}")
                    threshold_exceeded = True
                
                if threshold_exceeded:
                    user_input = input("Do you want to continue the scan? (y/n): ").strip().lower()
                    while threshold_exceeded:
                        spec = Spec.getter().data
                        spec = np.array(spec, dtype='uint16').mean(axis=0)[:]
                        mp._plot_windows[plabel].ydata = spec
                        mp._plot_windows[plabel].update_plot()
                        time.sleep(1) 
                        
                        if user_input == 'y': threshold_exceeded = False
                        elif user_input == 'n':
                            continue_scanning = False
                            break
                        elif user_input == '': continue
                else: time.sleep(1)
                    
            if not continue_scanning: break
        if not continue_scanning: break
    mp.close()
except Exception as e:
    print("Exception caught. Closing.")
    print(e)
    mp.close()

#%%
### ============================= APD counts ============================= ###

# init_settings()

# Initialize the MultiPlotter
mp = MultiPlotter()

def plot(mp):
    mp.initialize()
    plabel = "APD counts"
    pwindow = PlotWindow("Counts vs Time", "Time (s)", r"APD counts")
    mp.add_plot(plabel, pwindow)
    mp.main_loop()

tQt = threading.Thread(target=plot, args=([mp]), daemon=True)
tQt.start()

time.sleep(0.1)

# Live update loop
start_time = time.time()
time_data, counts_data = [], []

try:
    while True:
        current_time = time.time() - start_time  # Time elapsed since start
        counts = c_APD.getter()
        
        time_data.append(current_time)
        counts_data.append(counts)
        
        # Update plot
        mp._plot_windows["APD counts"].xdata = time_data
        mp._plot_windows["APD counts"].ydata = counts_data
        mp._plot_windows["APD counts"].update_plot()
        
except Exception as e:
    print("Exception caught. Closing.")
    print(e)
    mp.close()
    
#%% Laser power time evolution

# Initialize the MultiPlotter
mp = MultiPlotter()

def power_plot(mp):
    mp.initialize()
    plabel = "Power"
    pwindow = PlotWindow("Power vs Time", "Time (s)", r"Power ($\mu$W)")
    mp.add_plot(plabel, pwindow)
    mp.main_loop()

tQt = threading.Thread(target=power_plot, args=([mp]), daemon=True)
tQt.start()

time.sleep(0.1)

# Live update loop
start_time = time.time()
time_data, power_data = [], []

try:
    while True:
        current_time = time.time() - start_time  # Time elapsed since start
        power = P_det.getter()
        
        time_data.append(current_time)
        power_data.append(power)
        
        # Keep only the last 100 points to avoid overcrowding
        # if len(time_data) > 100:
        #     time_data.pop(0)
        #     power_data.pop(0)
        
        # Update plot
        mp._plot_windows["Power"].xdata = time_data
        mp._plot_windows["Power"].ydata = power_data
        mp._plot_windows["Power"].update_plot()
        
except Exception as e:
    print("Exception caught. Closing.")
    print(e)
    mp.close()
