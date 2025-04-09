from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64
from artiq.coredevice import ad9910

import numpy as np 

class BlueMOT_Loadingtime(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("sampler0")
        
        #Assign all channels
              #TTLs
        self.blue_mot_shutter:TTLOut=self.get_device("ttl4")
        self.repump_shutter_707:TTLOut=self.get_device("ttl5")
        self.zeeman_slower_shutter:TTLOut=self.get_device("ttl6")
        self.probe_shutter:TTLOut=self.get_device("ttl7")
        self.camera_trigger:TTLOut=self.get_device("ttl8")
        self.clock_shutter:TTLOut=self.get_device("ttl9")
        self.repump_shutter_679:TTLOut=self.get_device("ttl10")

        #self.pmt_shutter:TTLOut=self.get_device("ttl10")
        # self.camera_trigger:TTLOut=self.get_device("ttl11")
        # self.camera_shutter:TTLOut=self.get_device("ttl12")        
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
        #self.setattr_argument("blue_mot_loading_time", NumberValue(default=2000))
        self.setattr_argument("blue_mot_compression_time", NumberValue(default=20))
        self.setattr_argument("blue_mot_cooling_time", NumberValue(default=1000))
        self.setattr_argument("broadband_red_mot_time", NumberValue(default=10))
        self.setattr_argument("red_mot_compression_time", NumberValue(default=20))
        self.setattr_argument("single_frequency_time", NumberValue(default=30))
        self.setattr_argument("time_of_flight", NumberValue(default=30))
            
            
    @kernel
    def initialise(self):
        
        # Initialize the modules
      #  self.camera_shutter.output()
        #self.camera_trigger.output()
        self.sampler0.init()   
        self.blue_mot_shutter.output()
      #  self.red_mot_shutter.output()
        self.zeeman_slower_shutter.output()
        self.repump_shutter_707.output()
        self.repump_shutter_679.output()
        self.probe_shutter.output()
        #self.clock_shutter.output()
     #   self.pmt_shutter.output()
        self.mot_coil_1.init()
        self.mot_coil_2.init()
        self.blue_mot_aom.cpld.init()
        self.blue_mot_aom.init()
        self.zeeman_slower_aom.cpld.init()
        self.zeeman_slower_aom.init()
        self.probe_aom.cpld.init()
        self.probe_aom.init()
        #self.red_mot_aom.cpld.init()
        #self.red_mot_aom.init()
        #self.lattice_aom.cpld.init()
       # self.lattice_aom.init()

        # Set the RF channels ON
        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
       # self.red_mot_aom.sw.on()
        self.probe_aom.sw.on()
       # self.lattice_aom.sw.on()

        # Set the RF attenuation
        self.blue_mot_aom.set_att(0.0)
        self.zeeman_slower_aom.set_att(0.0)
        self.probe_aom.set_att(0.0)
        #self.red_mot_aom.set_att(0.0)

        #Set the profiles for 689 modulation and single frequency
        delay(500*us)

    def blue_mot_loading(self):               #Loading the Atoms into the Blue MOT
         # blue_amp = 0.08

            delay(10*ms)
            self.blue_mot_aom.set(frequency= 90 * MHz, amplitude=0.06)
            self.zeeman_slower_aom.set(frequency= 70 * MHz, amplitude=0.08)
            self.probe_aom.set(frequency= 200 * MHz, amplitude=0.18)

            self.blue_mot_aom.sw.on()
            self.zeeman_slower_aom.sw.on()
            
            voltage_1 = 7.95
            voltage_2 = 8.0
            self.mot_coil_1.write_dac(0, voltage_1)
            self.mot_coil_2.write_dac(1, voltage_2)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
                self.blue_mot_shutter.on()
                self.probe_shutter.off()
                self.zeeman_slower_shutter.on()
                self.repump_shutter_707.on()
                self.repump_shutter_679.on()

            print("Blue On")
            # self.blue_mot_aom.sw.off()
    @kernel
    def Sampler(self):

        self.core.break_realtime()                   #timebreak
        n_samples = 2000
        self.set_dataset("samples",np.full(n_samples,np.nan), broadcast = True)        #creates data set 

        n_channels = 1
    
        self.core.break_realtime()
    
        for i in range(n_channels):               
           self.sampler0.set_gain_mu(7-i,0)          #sets channels gain to 0db

        smp = [0]*n_channels   

        for n in range(n_samples):
            self.sampler0.sample_mu(smp)          #runs sampler and saves to list 
            self.mutate_dataset("samples",n,smp[0])        
            delay(90*us)

    @kernel 
    def run(self):


        self.initialise()
        for loading_time in range(50, 2001, 50):  # Loading time ranges from 50 to 1000ms in increments of 50
            
            delay(100*ms)

            for j in range(10):      #Runs 10 times per cooling time

                delay(100*ms)
                
                ################ Blue MOT Loading ##########################
                self.blue_mot_aom.set(frequency= 90 * MHz, amplitude=0.06)
                self.zeeman_slower_aom.set(frequency= 70 * MHz, amplitude=0.08)
                self.probe_aom.set(frequency= 200 * MHz, amplitude=0.18)

                self.blue_mot_aom.sw.on()
                self.zeeman_slower_aom.sw.on()
                
                
                voltage_1 = 7.95
                voltage_2 = 8.0
                self.mot_coil_1.write_dac(0, voltage_1)
                self.mot_coil_2.write_dac(1, voltage_2)

                with parallel:
                    self.mot_coil_1.load()
                    self.mot_coil_2.load()


                with parallel: 
                    self.blue_mot_shutter.on()
                    self.probe_shutter.off()
                    self.zeeman_slower_shutter.on()
                    self.repump_shutter_707.on()
                    self.repump_shutter_679.on()


                delay(loading_time*ms)
                # sample here
                self.Sampler()
         

