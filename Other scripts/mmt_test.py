import sys
sys.path.append(r'C:\Users\QPG\Documents\eyazici_g15\drivers')
sys.path.append(r'C:\Users\QPG\Documents\eyazici_g15\base\experiment_base')
sys.path.append(r'C:\Users\QPG\Documents\eyazici_g15\base\experiment_base\fey_drivers')

from fey_experiment_base import *
from fey_utility import *
from device_manager import *


### ============================= PARAMETERS ============================= ###

'''HP 4142B'''

def hp_current_getter(SMU):
    samples = []
    for i in range(5):
        samples.append(SMU.get_current())
        time.sleep(0.05)
    return samples[-1]


# # SMU 1
# # Check init_settings for safety features
V1  = Param("V1", units = 'V', 
    getter = hp.SMU1.get_voltage,
    setter = lambda val: hp.SMU1.set_voltage(val)) if not('hp' not in globals() or hp is None) else None

I1  = Param("I1", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU1)*1e9) if not('hp' not in globals() or hp is None) else None

# # SMU 3
# # Check init_settings for safety features
V2  = Param("V2", units = 'V', 
    getter = hp.SMU3.get_voltage,
    setter = lambda val: hp.SMU3.set_voltage(val)) if not('hp' not in globals() or hp is None) else None
            
I2  = Param("I2", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU3)*1e9) if not('hp' not in globals() or hp is None) else None

# # SMU 4
# # Check init_settings for safety features
V3  = Param("V3", units = 'V', 
    getter = hp.SMU4.get_voltage,
    setter = lambda val: hp.SMU4.set_voltage(val)) if not('hp' not in globals() or hp is None) else None
            
I3  = Param("I3", units = 'nA', 
    getter = lambda: hp_current_getter(hp.SMU4)*1e9) if not('hp' not in globals() or hp is None) else None

def set_Vall(val):
    V1.setter(val)
    V2.setter(val)
    V3.setter(val)

Vall  = Param("Vall", 
              long_name = 'SMU1, SMU3, SMU4 respectively',
              units = 'V', 
    getter = hp.SMU1.get_voltage,
    setter = set_Vall) if not('hp' not in globals() or hp is None) else None



### ============================== ROUTINES ============================== ###

def set_hp_V_defaults(SMU):
    SMU.set_source_mode('Voltage')
    SMU.set_voltage_output_range(40)
    SMU.set_voltage_limit(20)
    SMU.set_voltage_safe_step(0.01)
    SMU.set_current_compliance(1e-6)
    print('SMU at {}'.format(SMU))
    print( SMU.get_unit_settings() )

def init_settings():
    print("Initializing measurement settings")
    if hp is not None:
        #    SMU1 init
        set_hp_V_defaults(hp.SMU1)
        #    SMU3 init
        set_hp_V_defaults(hp.SMU3)
        #    SMU4 init
        set_hp_V_defaults(hp.SMU4)
    time.sleep(0.1)

def set_zero():
    print("Setting to zero...")
    hp.SMU1.set_voltage(0)
    hp.SMU3.set_voltage(0)
    hp.SMU4.set_voltage(0)




### ================================ MAIN ================================ ###
DATAPATH = r'C:\Users\QPG\Documents\eyazici_g15\data\leakage_test'
# REMOTEPATH = r'Z:\Users\eyazici\_Data_0D\data_g15_2\leakage_test'
COMMENT = 'top_gate'

init_settings()

param_plots = [('SMU1 Current', V1, I1), 
                ]

sweep_params = [(V1, np.linspace(-4,-5,51)),
                ]

meas_scan(sweep_params,
          constant_params = [],
          meas_params = [I1,I2,I3],
          measdatapath=DATAPATH,
          file_comment= COMMENT,
          const_wait_time = 1, wait_before = 0.25, wait_after = 0.15,
          wait_scan_line = 1,
          wait_btw_measurements = 0.01,
          script_path = __file__,
          param_plot_specifiers = param_plots,
          remote_path = None,
          )

# set_zero()