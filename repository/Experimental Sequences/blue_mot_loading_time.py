from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
#from artiq.coredevice.sampler import Sampler 
from numpy import int64
from artiq.coredevice import ad9910

#import numpy as np 

class bluemot_loading_time(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        #self.sampler:Sampler = self.get_device("sampler")
        
        #Assign all channels
        #TTLs
        self.blue_mot_shutter:TTLOut=self.get_device("ttl4")
        self.repump_shutter_707:TTLOut=self.get_device("ttl5")
        self.zeeman_slower_shutter:TTLOut=self.get_device("ttl6")
        self.probe_shutter:TTLOut=self.get_device("ttl7")
        self.camera_trigger:TTLOut=self.get_device("ttl8")
       # self.repump_shutter_679:TTLOut=self.get_device("ttl10")
        self.camera_shutter:TTLOut=self.get_device("ttl11")  
        #AD9910
        self.blue_mot_aom = self.get_device("urukul0_ch1")
        self.zeeman_slower_aom = self.get_device("urukul0_ch2")
        self.probe_aom = self.get_device("urukul0_ch3")          
        #Zotino
        #self.mot_coil_1=self.get_device("zotino0")
        #self.mot_coil_2=self.get_device("zotino0")
        
             
        self.setattr_argument("Cycles", NumberValue(default=10))
        self.setattr_argument("Holding_Time", NumberValue(default=10))        
            
    @kernel
    def initialise(self):
        
        # Initialize the modules
        #self.sampler.init()   
        self.blue_mot_shutter.output()
        self.zeeman_slower_shutter.output()
        self.repump_shutter_707.output()
        #self.repump_shutter_679.output()
        self.probe_shutter.output()
        #self.mot_coil_1.init()
        #self.mot_coil_2.init()
        self.blue_mot_aom.cpld.init()
        self.blue_mot_aom.init()
        self.zeeman_slower_aom.cpld.init()
        self.zeeman_slower_aom.init()
        self.probe_aom.cpld.init()
        self.probe_aom.init()

        # Set the RF channels ON
        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
        self.probe_aom.sw.on()

        # Set the RF attenuation
        self.blue_mot_aom.set_att(0.0)
        self.zeeman_slower_aom.set_att(0.0)
        self.probe_aom.set_att(0.0)

        delay(500*us)

        
    @kernel 
    def run(self):

        self.initialise()
        delay (1 * s)
        for loading_time in range(50, 2001, 50):  # Loading time ranges from 50 to 2000ms in increments of 50
            
            delay(100*ms)

            for j in range(int64(self.Cycles)):     

                delay(100*ms)
                
                #Load atoms into Blue MOT 
                self.blue_mot_aom.set(frequency= 90 * MHz, amplitude=0.06)
                self.zeeman_slower_aom.set(frequency= 70 * MHz, amplitude=0.08)
                self.probe_aom.set(frequency= 200 * MHz, amplitude=0.18)

                self.blue_mot_aom.sw.on()
                self.zeeman_slower_aom.sw.on()
                
                
                #voltage_1 = 7.95
                #voltage_2 = 8.0
                #self.mot_coil_1.write_dac(0, voltage_1)
                #self.mot_coil_2.write_dac(1, voltage_2)
               
                #with parallel:
                 #   self.mot_coil_1.load()
                  #  self.mot_coil_2.load()


                with parallel: 
                    self.blue_mot_shutter.on()
                    self.probe_shutter.off()
                    self.zeeman_slower_shutter.on()
                    self.repump_shutter_707.on()
                    self.repump_shutter_679.on()


                delay(loading_time*ms)
                
                #Hold atoms in blue MOT 
                with parallel:
                    self.blue_mot_shutter.off()
                
                delay(self.Holding_Time *ms)
                
                with parallel:
                    self.blue_mot_shutter.on()
                    self.repump_shutter_707.on()
                
                #self.pmt_capture(                     #Runs sampler
                 #   sampling_duration = 0.002,
                  #  sampling_rate= 200
                   # )                     

                with parallel:
                    self.blue_mot_shutter.off()
                    self.repump_shutter_707.off()

                delay(500 *ms)
         

