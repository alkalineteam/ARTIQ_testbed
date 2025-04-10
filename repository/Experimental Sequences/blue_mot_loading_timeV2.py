from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from artiq.coredevice import ad9910
from numpy import int64

class bluemot_loading_time(EnvExperiment):
    def build(self):
        self.setattr_device("core")

        self.repump_shutter_707:TTLOut=self.get_device("ttl5") 
        self.blue_mot_shutter:TTLOut=self.get_device("ttl4")
        self.zeeman_slower_shutter:TTLOut=self.get_device("ttl6")

        self.blue_mot_aom = self.get_device("urukul0_ch1")
        self.zeeman_slower_aom = self.get_device("urukul0_ch2")

        self.mot_coil_1=self.get_device("zotino0")
        self.mot_coil_2=self.get_device("zotino0")

        self.setattr_argument("Cycles", NumberValue(default = 1))
        self.setattr_argument("Loading_Time", NumberValue(default = 3000))
        self.setattr_argument("Holding_Time", NumberValue(default = 10))
       
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        
        # Initialize the modules
        self.blue_mot_shutter.output()
        self.zeeman_slower_shutter.output()
        self.repump_shutter_707.output()
        self.mot_coil_1.init()
        self.mot_coil_2.init()
        self.blue_mot_aom.cpld.init()
        self.blue_mot_aom.init()
        self.zeeman_slower_aom.cpld.init()
        self.zeeman_slower_aom.init()
        
        # Set the channel ON
        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()

        self.blue_mot_aom.set_att(0.0)
        self.blue_mot_aom.set(frequency= 90 * MHz, amplitude=0.06)
        
        # Set the magnetic field constant
         voltage_1 = 7.95
         voltage_2 = 8.0
         self.mot_coil_1.write_dac(0, voltage_1)
         self.mot_coil_2.write_dac(1, voltage_2)

         self.mot_coil_1.load()
         self.mot_coil_2.load()

        delay(1000*ms)

        for i in range(int64(self.Cycles)):
            # Slice 1
            with parallel:
                self.blue_mot_shutter.on()
                self.repump_shutter_707.off()
            
            self.zeeman_slower_aom.set_att(0.0)
            self.zeeman_slower_aom.set(frequency= 70 * MHz, amplitude=0.08)

            delay(self.Loading_Time* ms)

            # Slice 2
            with parallel:
                self.blue_mot_shutter.off()

            delay(self.Holding_Time * ms)

            #Slice 3
            with parallel:
                self.blue_mot_shutter.on()
                self.repump_shutter_707.on()

            with parallel:
                self.blue_mot_shutter.off()
                self.repump_shutter_707.off()

            delay(500 * ms)
