from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64, int32
from artiq.coredevice import ad9910
from artiq.coredevice.sampler import Sampler
import numpy as np


default_cfr1 = (
    (1 << 1)    # configures the serial data I/O pin (SDIO) as an input only pin; 3-wire serial programming mode
)
default_cfr2 = (
    (1 << 5)    # forces the SYNC_SMP_ERR pin to a Logic 0; this pin indicates (active high) detection of a synchronization pulse sampling error
    | (1 << 16) # a serial I/O port read operation of the frequency tuning word register reports the actual 32-bit word appearing at the input to the DDS phase accumulator (i.e. not the contents of the frequency tuning word register)
    | (1 << 24) # the amplitude is scaled by the ASF from the active profile (without this, the DDS outputs max. possible amplitude -> cracked AOM crystals)
)

class b_mot_loading_v3(EnvExperiment):

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
        #self.setattr_argument("blue_mot_loading_time", NumberValue(default=2000))
        self.setattr_argument("time_of_flight", NumberValue(default=40))
        self.setattr_argument("blue_mot_coil_1_voltage", NumberValue(default=8.0))
        self.setattr_argument("blue_mot_coil_2_voltage", NumberValue(default=7.82))




    @kernel
    def initialise_modules(self):
            
        delay(1000*ms)

        # Initialize the modules
        self.camera_shutter.output()
        self.camera_trigger.output()
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
        #self.lattice_aom.init()
        #self.stepping_aom.cpld.init()
        #self.stepping_aom.init()
        self.sampler.init() 

        # Set the RF channels ON
        #self.stepping_aom.set(frequency = 85.5* MHz)
        #self.stepping_aom.set_att(16*dB)
        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
        #self.stepping_aom.sw.on()
        # self.red_mot_aom.sw.on()
        self.probe_aom.sw.off()
        # self.lattice_aom.sw.on()

        # Set the RF attenuation
        self.blue_mot_aom.set_att(0.0)
        self.zeeman_slower_aom.set_att(0.0)
        self.probe_aom.set_att(0.0)
        #self.red_mot_aom.set_att(0.0)

        delay(100*ms)
   
    @kernel
    def blue_mot_loading(self,bmot_voltage_1,bmot_voltage_2):
        self.blue_mot_aom.set(frequency= 90 * MHz, amplitude=0.06)
        self.zeeman_slower_aom.set(frequency= 70 * MHz, amplitude=0.08)

        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
    
        self.mot_coil_1.write_dac(0, bmot_voltage_1)
        self.mot_coil_2.write_dac(1, bmot_voltage_2)

        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()
            self.blue_mot_shutter.on()
            self.probe_shutter.off()
            self.zeeman_slower_shutter.on()
            self.repump_shutter_707.on()
            self.repump_shutter_679.on()



    @kernel 
    def seperate_probe(self,tof,probe_duration,probe_frequency):
            with parallel:
                #self.red_mot_aom.sw.off()
                self.blue_mot_aom.sw.off()
                self.repump_shutter_679.off()
                self.repump_shutter_707.off()
                self.probe_shutter.on()

            self.mot_coil_1.write_dac(0, 5.0)  
            self.mot_coil_2.write_dac(1, 5.0)
           
            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()

            delay(((tof +3.9)*ms))

            with parallel:
                    self.camera_trigger.pulse(2*ms)
                    self.probe_aom.set(frequency=probe_frequency, amplitude=0.14)
                    self.probe_aom.sw.on()
                    
            delay(probe_duration * ms)
                    
            with parallel:
                self.probe_shutter.off()
                self.camera_shutter.off()    #Camera shutter takes 26ms to open so we will open it here
                self.probe_aom.set(frequency=probe_frequency, amplitude=0.00)
                self.probe_aom.sw.off()

            delay(10*ms)

  @kernel
    def normalised_detection(self):        #This function should be sampling from the PMT at the same time as the camera being triggered for seperate probe
        self.core.break_realtime()
        sample_period = 1 / 20000      #10kHz sampling rate should give us enough data points
        sampling_duration = 0.06      #30ms sampling time to allow for all the imaging slices to take place

        num_samples = int32(sampling_duration/sample_period)
        samples = [[0.0 for i in range(8)] for i in range(num_samples)]
    
        with parallel:
    
            with sequential:
                ##########################Ground State###############################
                
                with parallel:
                    self.blue_mot_aom.sw.off()
                    self.probe_shutter.on()

                self.mot_coil_1.write_dac(0, 5.0)   #Set 0 field 
                self.mot_coil_2.write_dac(1, 5.0)

                with parallel:
                    self.mot_coil_1.load()
                    self.mot_coil_2.load()

                delay(3.9*ms)     #wait for shutter to open

                with parallel:
                    self.camera_trigger.pulse(1*ms)
                    self.probe_aom.set(frequency=200 * MHz, amplitude=0.17)
                    self.probe_aom.sw.on()

                delay(0.2 * ms)      #Ground state probe duration            
                
                with parallel:
                    self.probe_shutter.off()
                    self.probe_aom.sw.off()

                delay(5*ms)                         #repumping 
               
                with parallel:
                    self.repump_shutter_679.pulse(10*ms)
                    self.repump_shutter_707.pulse(10*ms)

                delay(10*ms)                         #repumping 

                # ###############################Excited State##################################

                self.probe_shutter.on()
                delay(3.9*ms) 

                self.probe_aom.sw.on()
                delay(0.2*ms)            #Ground state probe duration
                self.probe_aom.sw.off()

                delay(20*ms)
                #  ########################Background############################
 
                self.probe_aom.sw.on()
                delay(0.2*ms)            #Ground state probe duration
                self.probe_aom.sw.off()
                self.probe_shutter.off()

                delay(7*ms)
                
            with sequential:
                for j in range(num_samples):
                    self.sampler.sample(samples[j])
                    delay(sample_period*s)
                

        delay(sampling_duration*s)


        samples_ch0 = [i[0] for i in samples]
        self.set_dataset("normalised_detection", samples_ch0, broadcast=True, archive=True)

    @kernel
    def pmt_capture(self,sampling_duration,sampling_rate,tof):        #This function should be sampling from the PMT at the same time as the camera being triggered for seperate probe
        # self.core.break_realtime()
        sample_period = 1 / sampling_rate
        num_samples = int32(sampling_duration/sample_period)
        print(num_samples)
        samples = [[0.0 for i in range(8)] for i in range(num_samples)]
    
        with parallel:
            with sequential:
                with parallel:
                    #self.red_mot_aom.sw.off()
                    self.blue_mot_aom.sw.off()
                    self.repump_shutter_679.off()
                    self.repump_shutter_707.off()
                    self.probe_shutter.on()

                self.mot_coil_1.write_dac(0, 5.0)  
                self.mot_coil_2.write_dac(1, 5.0)
           
                with parallel:
                    self.mot_coil_1.load()
                    self.mot_coil_2.load()

                delay(((tof + 3.9)*ms))

                with parallel:
                    self.camera_trigger.pulse(1*ms)
                    self.probe_aom.set(frequency=200 * MHz, amplitude=0.17)
                    self.probe_aom.sw.on()
    
                delay(3 * ms)
                    
                with parallel:
                    self.probe_shutter.off()
                    self.camera_shutter.off()    #Camera shutter takes 26ms to open so we will open it here
                    self.probe_aom.set(frequency=0*MHz, amplitude=0.00)
                    self.probe_aom.sw.off()

            with sequential:
                for j in range(num_samples):
                    self.sampler.sample(samples[j])
                    delay(sample_period*s)

        delay(sampling_duration*ms)

         
        samples_ch0 = [i[0] for i in samples]
        print(samples_ch0)
        self.set_dataset("samples", samples_ch0, broadcast=True, archive=True)


    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.initialise_modules()

        for blue_mot_loading_time in range(50, 2001, 50):  # Loading time ranges from 50 to 2000ms in increments of 50

            for j in range(int(self.cycles)):          #This runs the actual sequence
            
            delay(100*us)


            self.blue_mot_loading(
                 bmot_voltage_1 = self.blue_mot_coil_1_voltage,
                 bmot_voltage_2 = self.blue_mot_coil_2_voltage
            )

<<<<<<< HEAD:repository/Experimental Sequences/blue_mot_loading_v3.py
            delay(self.blue_mot_loading_time* ms)


            self.zeeman_slower_aom.sw.off()



=======

            delay(self.blue_mot_loading_time* ms)


>>>>>>> 2c237e5c31ab9de92dc65c8da138b53e29bbc71f:repository/Experimental Sequences/blue_mot_loading_v3
            self.seperate_probe(
                tof = self.time_of_flight,
                probe_duration = 0.02*ms ,
                probe_frequency= 200 * MHz
            )


            # self.pmt_capture(
            #     sampling_duration = 0.2,
            #     sampling_rate= 10000,
            #     tof =self.time_of_flight
            # )

            # self.normalised_detection()
            

            delay(200*ms)




            



    
