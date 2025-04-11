from artiq.experiment import *
from artiq.coredevice.core import Core
from artiq.coredevice.ttl import TTLOut
from numpy import int64

class continuous_mode(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.core:Core

        #TTLs
        self.blue_mot_shutter:TTLOut=self.get_device("ttl4")
        self.repump_shutter_707:TTLOut=self.get_device("ttl5")
        self.zeeman_slower_shutter:TTLOut=self.get_device("ttl6")
        self.probe_shutter:TTLOut=self.get_device("ttl7")
        self.camera_trigger:TTLOut=self.get_device("ttl8")
        self.clock_shutter:TTLOut=self.get_device("ttl9")
        self.repump_shutter_679:TTLOut=self.get_device("ttl10")
        # self.pmt_shutter:TTLOut=self.get_device("ttl10")
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
               
        
        self.setattr_argument("Sequence", NumberValue(default = 0.0))
        self.setattr_argument("Cycle", NumberValue(default = 50))
        self.setattr_argument("probe_ON", BooleanValue(default = False))
        self.setattr_argument("switch_all_off",BooleanValue(default=False))
        self.setattr_argument("coils_off",BooleanValue(default=False))

        self.setattr_argument("blue_mot_frequency", NumberValue(default = 90.0))
        self.setattr_argument("blue_mot_amplitude", NumberValue(default = 0.06))
        # self.setattr_argument("BMOT_Attenuation", NumberValue(default = 0.0))

        self.setattr_argument("zeeman_frequency", NumberValue(default = 70.0))
        self.setattr_argument("zeeman_amplitude", NumberValue(default = 0.08)) 
        # self.setattr_argument("Zeeman_Attenuation", NumberValue(default = 0.0))

        self.setattr_argument("red_mot_frequency", NumberValue(default = 80.0))
        self.setattr_argument("red_mot_amplitude", NumberValue(default = 0.05)) 
        # self.setattr_argument("RMOT_Attenuation", NumberValue(default = 0.0))

        self.setattr_argument("probe_frequency", NumberValue(default = 200.0))
        self.setattr_argument("probe_amplitude", NumberValue(default = 0.18)) 
        # self.setattr_argument("Probe_Attenuation", NumberValue(default = 0.0))

        self.setattr_argument("lattice_frequency", NumberValue(default = 100.0))
        self.setattr_argument("lattice_attenuation_dB", NumberValue(default = 0.00))

        self.setattr_argument("clock_frequency", NumberValue(default = 85.0))
        self.setattr_argument("clock_attenuation_dB", NumberValue(default = 16))

        self.setattr_argument("coil_1_voltage", NumberValue(default = 7.9))
        self.setattr_argument("coil_2_voltage", NumberValue(default = 8))

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.mot_coil_1.init()
        self.mot_coil_2.init()

        # initialise AD9910
        self.blue_mot_aom.cpld.init()
        self.blue_mot_aom.init()
        self.zeeman_slower_aom.cpld.init()
        self.zeeman_slower_aom.init()
        self.red_mot_aom.cpld.init()
        self.red_mot_aom.init()
        self.probe_aom.cpld.init()
        self.probe_aom.init()

        # initialise AD9912
        self.lattice_aom.cpld.init()
        self.lattice_aom.init()
        self.atom_lock_aom.cpld.init()
        self.atom_lock_aom.init()
        self.stepping_aom.cpld.init()
        self.stepping_aom.init()


        # Switch on all DDS channels
        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
        self.red_mot_aom.sw.on()
        self.probe_aom.sw.on()
        self.lattice_aom.sw.on()
        self.atom_lock_aom.sw.on()
        self.stepping_aom.sw.on()


        # Setting attenuation for AD9910
        self.blue_mot_aom.set_att(0.0)
        self.zeeman_slower_aom.set_att(0.0)
        self.red_mot_aom.set_att(0.0)
        self.probe_aom.set_att(0.0)
       
        
        if self.coils_off == False:
            self.mot_coil_1.write_dac(0, self.coil_1_voltage)    
            self.mot_coil_2.write_dac(1, self.coil_2_voltage)
        else: 
            self.mot_coil_1.write_dac(0, 5.0)    
            self.mot_coil_2.write_dac(1, 5.0)
        
        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()
            self.repump_shutter_707.on()
            self.repump_shutter_679.on()
            self.blue_mot_shutter.on()
            self.probe_shutter.on()
            self.zeeman_slower_shutter.on()
            self.clock_shutter.on()
            self.probe_shutter.on()

            if self.probe_ON == True: 
                self.probe_shutter.on()
                self.probe_aom.set(frequency=self.probe_frequency * MHz, amplitude=self.probe_amplitude)


        self.blue_mot_aom.set(frequency= self.blue_mot_frequency * MHz, amplitude=self.blue_mot_amplitude)

        self.zeeman_slower_aom.set(frequency=self.zeeman_frequency * MHz, amplitude=self.zeeman_amplitude)

        self.red_mot_aom.set(frequency=self.red_mot_frequency * MHz, amplitude=self.red_mot_amplitude)

        self.probe_aom.set(frequency=self.probe_frequency * MHz, amplitude=self.probe_amplitude)

        self.lattice_aom.set(frequency=self.lattice_frequency * MHz)
        self.lattice_aom.set_att(self.lattice_attenuation_dB * dB)

        self.stepping_aom.set(frequency=self.clock_frequency * MHz)
        self.stepping_aom.set_att(self.clock_attenuation_dB * dB)

        delay(1000*ms)

        # if self.Sequence == 1:
        #     for i in range(int64(self.Cycle)):
        #         self.mot_coil_1.write_dac(0, 0.976)
        #         self.mot_coil_2.write_dac(1, 0.53)

        #         with parallel:
        #             self.mot_coil_1.load()
        #             self.mot_coil_2.load()
        #             self.zeeman_slower_aom.set(frequency=self.Zeeman_Frequency * MHz, amplitude=self.Zeeman_Amplitude)
        #         self.stepping_aom.sw.on()
        #         delay(1000*ms)

        #         self.mot_coil_1.write_dac(0, 2.46)
        #         self.mot_coil_2.write_dac(1, 2.23)
        #         self.zeeman_slower_aom.set(frequency=self.Zeeman_Frequency * MHz, amplitude=0.0)

        #         with parallel:
        #             self.mot_coil_1.load()
        #             self.mot_coil_2.load()
        #         self.stepping_aom.off()
        #         delay(1000*ms)

        # if self.Sequence == 2:
        #     self.mot_coil_1.write_dac(0, 2.49)
        #     self.mot_coil_2.write_dac(1, 2.27)

        #     with parallel:
        #         self.mot_coil_1.load()
        #         self.mot_coil_2.load()

        # if self.Sequence == 3:
        #     self.mot_coil_1.write_dac(0, 4.055)
        #     self.mot_coil_2.write_dac(1, 4.083)

        #     with parallel:
        #         self.mot_coil_1.load()
        #         self.mot_coil_2.load()
        

        if self.switch_all_off == True: 
            self.blue_mot_aom.sw.off()
            self.zeeman_slower_aom.sw.off()
            self.red_mot_aom.sw.off()
            self.probe_aom.sw.off()
            self.atom_lock_aom.sw.off()
            self.stepping_aom.sw.off()

        print("Parameters are set")