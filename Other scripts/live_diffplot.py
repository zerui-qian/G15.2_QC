import sys
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\drivers')
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\base\experiment_base')
sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\base\experiment_base\fey_drivers')

from fey_experiment_base import *
from fey_utility import *
from device_manager import *

sys.path.append(r'C:\Users\QPG\Documents\zerui_g15\scripts')
from main_mmt import *


### ================================ MAIN ================================ ###

# init_settings()

ws.exposure_time = (1)
ws.num_frames = (1)

wlens = None

def diff_plot(mp):
    # mp = MultiPlotter()
    mp.initialize()
    plabel = "dR/dV liveplot"
    pwindow = PlotWindow("dR/dV liveplot", "Energy (meV)", "R difference (counts)")
    mp.add_plot(plabel, pwindow)
    # print("Added plot")
    mp.main_loop()    

mp = MultiPlotter()
tQt = threading.Thread(target=diff_plot, args=([mp]), daemon = True)
plabel = "dR/dV liveplot"

tQt.start()

time.sleep(0.1)
try:
    while (True):
        Vdiff.setter(20)
        # Vsum.setter(17)
        # Vtg.setter(1.5)
        
        if wlens is None:
            spec1 = Spec.getter().data
            wlens = Wlen.getter()
            spec1 = np.array(spec1, dtype = 'uint16')
            energies = convert_nm_eV(np.array(wlens))
            
            mp._plot_windows[plabel].xdata = energies
        else :
            spec1 = Spec.getter().data
            time.sleep(0.1)
        
        spec1 = np.array(spec1,dtype = 'uint16').mean(axis=0)[:]
        
        Vdiff.setter(18)
        # Vtg.setter(1)
        # Vsum.setter(15)

        spec2 = Spec.getter().data
        spec2 = np.array(spec2,dtype = 'uint16').mean(axis=0)[:]
        
        mp._plot_windows[plabel].ydata = (spec1 - spec2) #/ (spec2)
        mp._plot_windows[plabel].update_plot()
        
        time.sleep(1)
    mp.close()
except Exception as e:
    print("Exception caught. Closing.")
    print(e)
    mp.close()