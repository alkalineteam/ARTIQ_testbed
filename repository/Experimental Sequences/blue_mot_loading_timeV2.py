from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from artiq.coredevice import ad9910
from numpy import int64

class blue_mot_loading_timeV2(EnvExperiment):
    def build(self):
        self.setattr_device("core")

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


        self.setattr_argument("Cycles", NumberValue(default = 1))
        self.setattr_argument("loading_time", NumberValue(default = 2000))
        self.setattr_argument("blue_mot_coil_1_voltage", NumberValue(default=8.0))
        self.setattr_argument("blue_mot_coil_2_voltage", NumberValue(default=7.82))
        self.setattr_argument("time_of_flight", NumberValue(default=40))
        

    @kernel
    def initialise_modules(self):
        delay(1000*ms)

        # Initialize the modules
        self.blue_mot_shutter.output()
        self.zeeman_slower_shutter.output()
        self.repump_shutter_707.output()
        self.repump_shutter_679.output()
        self.mot_coil_1.init()
        self.mot_coil_2.init()
        self.blue_mot_aom.cpld.init()
        self.blue_mot_aom.init()
        self.zeeman_slower_aom.cpld.init()
        self.zeeman_slower_aom.init()
        self.probe_shutter.output()

        #self.sampler.init() 
        
        # Set the channel ON
        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
        self.probe_aom.cpld.init()
        self.probe_aom.init()
        
        delay(100*ms)





    @kernel 
    def seperate_probe(self,tof,probe_duration,probe_frequency):
            with parallel:
                self.red_mot_aom.sw.off()
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
    def blue_mot_loading(self,bmot_voltage_1,bmot_voltage_2):
        self.blue_mot_aom.set(frequency = 90 * MHz, amplitude = 0.06)
        self.zeeman_slower_aom.set(frequency = 70 * MHz, amplitude = 0.08)

        self.blue_mot_aom.sw.on
        self.zeeman_slower_aom.sw.on

        self.mot_coil_1.write_dac(0, bmot_voltage_1)
        self.mot_coil_2.write_dac(1, bmot_voltage_2)


        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_1.load()
            self.mot_coil_2.load()
            self.blue_mot_shutter.on()
            self.probe_shutter.off()
            self.zeeman_slower_shutter.on()
            self.repump_shutter_707.on()
            self.repump_shutter_679.on()
       
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.initialise_modules()

        for i in range(int64(self.Cycles)):
            delay(100 *us)

            ####################  in parallel to sampler #######################
               # self.pmt_capture(
            #     sampling_duration = 0.2,
            #     sampling_rate= 10000,
            #     tof =self.time_of_flight
            # )


            # BlueMOT loading with field constant
            
            self.blue_mot_loading(
                bmot_voltage_1 = self.blue_mot_coil_1_voltage,
                bmot_voltage_2 = self.blue_mot_coil_2_voltage,

            )

            delay(self.loading_time * ms)
            print("loop")

            self.blue_mot_aom.sw.off()
            self.zeeman_slower_aom.sw.off()
            self.repump_shutter_679.off()
            self.repump_shutter_707.off()

            # self.seperate_probe(
            #     tof = 0*ms,
            #     probe_duration = 0.2*ms,
            #     probe_frequency = 200 * MHz
            # )

            delay(400*ms)
            ####################################################################################
