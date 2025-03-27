from artiq.experiment import *
import numpy as np

class AD9910_modulation(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.ad9910_0=self.get_device("urukul0_ch0") 
        self.cpld0=self.get_device("urukul0_cpld")
    
        self.setattr_argument("Number_of_pulse", NumberValue(default=10))
        self.setattr_argument("Pulse_width", NumberValue(default=1000)) 

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.ad9910_0.cpld.init()
        self.ad9910_0.init()

        self.ad9910_0.sw.on()



        low_frequency = 80.0
        high_frequency = 81.0
        modulation_frequency = 25
        step_size = 0.01
    
        #generate list of values to be read in the RAM profile
        period = 1 / modulation_frequency
        num_steps = int(period/ step_size) #1 step is equivalent to 4 ns 
        
        t = np.linspace(0,period,num_steps,endpoint=False)
        modulation = low_frequency + (high_frequency) * 2 * np.abs(t / period - np.floor(t / period + 0.5)) #Generates all of the frequency values to be stored in the list

        self.frequency_ram_list = [0] * len(modulation)          #creates list for RAM values to be stored in later

        self.ad9910_0.set_cfr1(ram_enable=0)                         #ram needs to be set to zero to turn off frequency 
        self.cpld0.io_update.pulse(8)

        self.ad9910_0.set_profile_ram(start=0, end=len(self.asf_ram)-1,step=self.step_size, profile=0, mode=ad9910.RAM_MODE_CONT_BIDIR_RAMP) 
        # #gives start and end adresses of where to look within the RAM
        #step length, i.e. how long to run each element of the list. 1 step = 4ns
        self.cpld0.io_update.pulse_mu(8) 

        self.ad9910_0.frequency_to_ram(modulation,self.frequency_ram_list) 
        self.ad9910_0.write_ram(self.frequency_ram_list)                     #converts the quantity we gave it into RAM profile data. Fill up the empty list we defined earlier
        self.core.break_realtime()

        self.ad9910_0.set(amplitude=0.08,ram_destination=ad9910.RAM_DEST_FTW) 


        #must set the control function register ram_enable to 1 to enable ram playback
        self.ad9910_0.set_cfr1(internal_profile=0, ram_enable = 1, ram_destination=ad9910.RAM_DEST_FTW, manual_osk_external=0, osk_enable=1, select_auto_osk=0) #for frequency modulation

        self.cpld0.io_update.pulse_mu(8)

        print("Modulation test completed")