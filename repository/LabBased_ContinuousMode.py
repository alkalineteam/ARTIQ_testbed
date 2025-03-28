from artiq.experiment import *
from artiq.coredevice.core import Core
from artiq.coredevice.ttl import TTLOut
from numpy import int64

class Everything_ON(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.core:Core

        #TTLs
        self.blue_mot_shutter:TTLOut=self.get_device("ttl0")
        self.repump_shutter:TTLOut=self.get_device("ttl1")
        self.red_mot_shutter:TTLOut=self.get_device("ttl2")
        self.zeeman_slower_shutter:TTLOut=self.get_device("ttl3")
        self.probe_shutter:TTLOut=self.get_device("ttl4")
        self.clock_shutter:TTLOut=self.get_device("ttl5")
        self.pmt_shutter:TTLOut=self.get_device("ttl6")
        self.camera_trigger:TTLOut=self.get_device("ttl7")
        self.camera_shutter:TTLOut=self.get_device("ttl7")        
        #AD9910
        self.blue_mot_aom = self.get_device("urukul0_ch0")
        self.probe_aom = self.get_device("urukul0_ch1")
        self.zeeman_slower_aom = self.get_device("urukul0_ch2")
        self.lattice_aom = self.get_device("urukul0_ch2")
        #AD9912
        self.red_mot_aom=self.get_device("urukul1_ch0")
        self.atom_lock_aom=self.get_device("urukul1_ch1")
        self.stepping_aom=self.get_device("urukul1_ch2")
               
               #Zotino
        self.mot_coil_1=self.get_device("zotino0")
        self.mot_coil_2=self.get_device("zotino0")
               
        
        self.setattr_argument("Sequence", NumberValue(default = 0.0))
        self.setattr_argument("Cycle", NumberValue(default = 50))

        self.setattr_argument("BMOT_Frequency", NumberValue(default = 90.0))
        self.setattr_argument("BMOT_Amplitude", NumberValue(default = 0.07))
        # self.setattr_argument("BMOT_Attenuation", NumberValue(default = 0.0))

        self.setattr_argument("Zeeman_Frequency", NumberValue(default = 70.0))
        self.setattr_argument("Zeeman_Amplitude", NumberValue(default = 0.35)) 
        # self.setattr_argument("Zeeman_Attenuation", NumberValue(default = 0.0))

        self.setattr_argument("RMOT_Frequency", NumberValue(default = 80.0))
        self.setattr_argument("RMOT_Amplitude", NumberValue(default = 0.13)) 
        # self.setattr_argument("RMOT_Attenuation", NumberValue(default = 0.0))

        self.setattr_argument("Probe_Frequency", NumberValue(default = 200))
        self.setattr_argument("Probe_Amplitude", NumberValue(default = 0.17)) 
        # self.setattr_argument("Probe_Attenuation", NumberValue(default = 0.0))

        self.setattr_argument("Clock_Frequency", NumberValue(default = 85.0))
        self.setattr_argument("Clock_Attenuation", NumberValue(default = 0.0))

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.mot_coil_1.init()
        self.mot_coil_2.init()
        self.blue_mot_aom.cpld.init()
        self.blue_mot_aom.init()
        self.zeeman_slower_aom.cpld.init()
        self.zeeman_slower_aom.init()
        self.red_mot_aom.cpld.init()
        self.red_mot_aom.init()
        self.probe_aom.cpld.init()
        self.probe_aom.init()
        self.clock_aom.cpld.init()
        self.clock_aom.init()

        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
        self.red_mot_aom.sw.on()
        self.probe_aom.sw.on()
        self.clock_aom.sw.on()

        self.blue_mot_aom.set_att(0.0)
        self.zeeman_slower_aom.set_att(0.0)
        self.red_mot_aom.set_att(0.0)
        self.probe_aom.set_att(0.0)
        self.stepping_aom.set_att(self.Clock_Attenuation)

        self.mot_coil_1.write_dac(0, 0.976)    
        self.mot_coil_2.write_dac(1, 0.53)
        
        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()
            self.repump_shutter.on()
            self.blue_mot_shutter.on()
            self.red_mot_shutter.on()
            self.zeeman_slower_shutter.on()

        self.blue_mot_aom.set(frequency= self.BMOT_Frequency * MHz, amplitude=self.BMOT_Amplitude)

        self.zeeman_slower_aom.set(frequency=self.Zeeman_Frequency * MHz, amplitude=self.Zeeman_Amplitude)

        self.red_mot_aom.set(frequency=self.RMOT_Frequency * MHz, amplitude=self.RMOT_Amplitude)

        self.probe_aom.set(frequency=self.Probe_Frequency * MHz, amplitude=self.Probe_Amplitude)

        self.stepping_aom.set(frequency=self.Clock_Frequency * MHz)

        delay(1000*ms)

        if self.Sequence == 1:
            for i in range(int64(self.Cycle)):
                self.mot_coil_1.write_dac(0, 0.976)
                self.mot_coil_2.write_dac(1, 0.53)

                with parallel:
                    self.mot_coil_1.load()
                    self.mot_coil_2.load()
                    self.zeeman_slower_aom.set(frequency=self.Zeeman_Frequency * MHz, amplitude=self.Zeeman_Amplitude)
                self.stepping_aom.sw.on()
                delay(1000*ms)

                self.mot_coil_1.write_dac(0, 2.46)
                self.mot_coil_2.write_dac(1, 2.23)
                self.zeeman_slower_aom.set(frequency=self.Zeeman_Frequency * MHz, amplitude=0.0)

                with parallel:
                    self.mot_coil_1.load()
                    self.mot_coil_2.load()
                self.stepping_aom.off()
                delay(1000*ms)

        if self.Sequence == 2:
            self.mot_coil_1.write_dac(0, 2.49)
            self.mot_coil_2.write_dac(1, 2.27)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()

        if self.Sequence == 3:
            self.mot_coil_1.write_dac(0, 4.055)
            self.mot_coil_2.write_dac(1, 4.083)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
        
        print("Parameters are set")