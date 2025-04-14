from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64, int32
from artiq.coredevice import ad9910
from artiq.coredevice.sampler import Sampler
import numpy as np

from common.py import sr1 

default_cfr1 = (
    (1 << 1)    # configures the serial data I/O pin (SDIO) as an input only pin; 3-wire serial programming mode
)
default_cfr2 = (
    (1 << 5)    # forces the SYNC_SMP_ERR pin to a Logic 0; this pin indicates (active high) detection of a synchronization pulse sampling error
    | (1 << 16) # a serial I/O port read operation of the frequency tuning word register reports the actual 32-bit word appearing at the input to the DDS phase accumulator (i.e. not the contents of the frequency tuning word register)
    | (1 << 24) # the amplitude is scaled by the ASF from the active profile (without this, the DDS outputs max. possible amplitude -> cracked AOM crystals)
)

class sequence_main(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        
        self.sampler:Sampler = self.get_device("sampler0")
        #Assign all channels
              #TTLs
        self.blue_mot_shutter:TTLOut=self.get_device("ttl4")
        self.repump_shutter_707:TTLOut=self.get_device("ttl5")
        self.zeeman_slower_shutter:TTLOut=self.get_device("ttl6")
        self.probe_shutter:TTLOut=self.get_device("ttl7")
        self.camera_trigger:TTLOut=self.get_device("ttl8")
        self.clock_shutter:TTLOut=self.get_device("ttl9")
        self.repump_shutter_679:TTLOut=self.get_device("ttl10")
        self.camera_shutter:TTLOut=self.get_device("ttl11")   

        # self.pmt_shutter:TTLOut=self.get_device("ttl10")
        #AD9910
        self.red_mot_aom = self.get_device("urukul0_ch0")
        self.blue_mot_aom = self.get_device("urukul0_ch1")
        self.zeeman_slower_aom = self.get_device("urukul0_ch2")
        self.probe_aom = self.get_device("urukul0_ch3")
        #AD9912
        self.lattice_aom=self.get_device("urukul1_ch0")
        self.stepping_aom=self.get_device("urukul1_ch1")
        self.atom_lock_aom=self.get_device("urukul1_ch2")
               
        
        #Zotino
        self.mot_coil_1=self.get_device("zotino0")
        self.mot_coil_2=self.get_device("zotino0")
        
             
        self.setattr_argument("cycles", NumberValue(default=1))
        self.setattr_argument("blue_mot_loading_time", NumberValue(default=2000))
        self.setattr_argument("blue_mot_compression_time", NumberValue(default=20))
        self.setattr_argument("blue_mot_cooling_time", NumberValue(default=60))
        self.setattr_argument("broadband_red_mot_time", NumberValue(default=15))
        self.setattr_argument("red_mot_compression_time", NumberValue(default=10))
        self.setattr_argument("single_frequency_time", NumberValue(default=20))
        self.setattr_argument("time_of_flight", NumberValue(default=40))

        self.setattr_argument("blue_mot_coil_1_voltage", NumberValue(default=8.0))
        self.setattr_argument("blue_mot_coil_2_voltage", NumberValue(default=7.82))
        self.setattr_argument("compressed_blue_mot_coil_1_voltage", NumberValue(default=8.55))
        self.setattr_argument("compressed_blue_mot_coil_2_voltage", NumberValue(default=8.34))
        self.setattr_argument("bb_rmot_coil_1_voltage", NumberValue(default=5.3))
        self.setattr_argument("bb_rmot_coil_2_voltage", NumberValue(default=5.28))
        self.setattr_argument("sf_rmot_coil_1_voltage", NumberValue(default=5.7))
        self.setattr_argument("sf_rmot_coil_2_voltage", NumberValue(default=5.66))
        self.setattr_argument("sf_frequency", NumberValue(default=80.92))

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.sr1.initialise_modules()

        for j in range(int(self.cycles)):          #This runs the actual sequence
            delay(100*us)

            self.sr1.blue_mot_loading(
                 bmot_voltage_1 = self.blue_mot_coil_1_voltage,
                 bmot_voltage_2 = self.blue_mot_coil_2_voltage
            )

            self.sr1.red_modulation_on(
                f_start = 80 * MHz,        #Starting frequency of the ramp
                A_start = 0.06,            #initial amplitude of the ramp
                f_SWAP_start = 80 * MHz,   #Ramp lower limit
                f_SWAP_end = 81 * MHz,     #Ramp upper limit
                T_SWAP = 40 * us,          #Time spent on each step, 40us is equivalent to 25kHz modulation rate
                A_SWAP = 0.06,             #Amplitude during modulation
            )

            delay(self.blue_mot_loading_time* ms)

            self.sr1.blue_mot_compression(                           #Here we are ramping up the blue MOT field and ramping down the blue power
                bmot_voltage_1 = self.blue_mot_coil_1_voltage,
                bmot_voltage_2 = self.blue_mot_coil_2_voltage,
                compress_bmot_volt_1 = self.compressed_blue_mot_coil_1_voltage,
                compress_bmot_volt_2 = self.compressed_blue_mot_coil_2_voltage,
                bmot_amp = 0.06,
                compress_bmot_amp = 0.0035
            )

            delay(self.blue_mot_compression_time*ms)

            delay(self.blue_mot_cooling_time*ms)   #Allowing further cooling of the cloud by just holding the atoms here

            self.sr1.broadband_red_mot(                                  #Switch to low field gradient for Red MOT, switches off the blue beams
                rmot_voltage_1= self.bb_rmot_coil_1_voltage,
                rmot_voltage_2 = self.bb_rmot_coil_2_voltage
            )

            self.camera_shutter.on()    #Camera shutter takes 26ms to open so we will open it here

            delay(self.broadband_red_mot_time*ms)

            self.sr1.red_modulation_off(                   #switch to single frequency
                f_SF = self.sf_frequency * MHz,
                A_SF = 0.04
            )

            self.sr1.red_mot_compression(                         #Compressing the red MOT by ramping down power, field ramping currently not active
                bb_rmot_volt_1 = self.bb_rmot_coil_1_voltage,
                bb_rmot_volt_2 = self.bb_rmot_coil_2_voltage,
                sf_rmot_volt_1 = self.sf_rmot_coil_1_voltage,
                sf_rmot_volt_2 = self.sf_rmot_coil_2_voltage,
                frequency= self.sf_frequency
            )

            delay(self.red_mot_compression_time*ms)

            delay(self.single_frequency_time*ms)



            self.sr1.pmt_capture(
                sampling_duration = 0.2,
                sampling_rate= 10000,
                tof =self.time_of_flight
            )
            
            # self.seperate_probe(
            #     tof = self.time_of_flight,
            #     probe_duration = 0.2 ,
            #     probe_frequency= 200 * MHz
            # )

            delay(100*ms)




            



    
