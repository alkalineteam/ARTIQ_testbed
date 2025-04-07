from artiq.experiment import *
from artiq.coredevice.core import Core
from artiq.coredevice.ad9910 import AD9910
from artiq.coredevice.urukul import CPLD
from artiq.experiment import EnvExperiment
from artiq.experiment import NumberValue
from numpy import int64, float64
import numpy as np

class red_mod_rpc(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.core:Core
        self.Single_Freq=self.get_device("urukul0_ch0")

        self.setattr_argument("Cycles", NumberValue(default=1))
        self.setattr_argument("Start_Freq", NumberValue(default=80.0, unit="MHz", precision=3))
        self.setattr_argument("End_Freq", NumberValue(default=81.0, unit="MHz", precision=3))
        self.setattr_argument("Modulation_Freq", NumberValue(default=0.025, unit="MHz", precision=3))

    # @rpc
    # def set_time_step(self) -> int64:
    #     self.time_step = (1 / self.Modulation_Freq) * 1e6 # microseconds
    #     return int64(self.time_step)

    # def set_freq_step(self):
    #     self.freq_step = ((self.End_Freq - self.Start_Freq))/ (self.set_time_step())  # MHz
    #     return float64(self.freq_step) * 1e-6
    

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        delay(500*ms)

        self.Single_Freq.cpld.init()
        self.Single_Freq.init()
        self.Single_Freq.sw.on()
        delay(500*ms)


        time_step = (1 / (self.Modulation_Freq * 1e-6))
        freq_step = self.Modulation_Freq * 1e-6

        # t1 = self.core.get_rtio_counter_mu()

        for i in range(10000):
            freq_start = self.Start_Freq * 1e-6
            freq_end = self.End_Freq * 1e-6

            # Ramp Up
            for i in range(41):
                self.Single_Freq.set(frequency=freq_start*MHz, amplitude=1.0, phase=0.0)
                delay(time_step*us)
                freq_start += freq_step

            #     print(freq_start)
            # print("---------")

            # Ramp Down
            # for i in range(5):
            #     self.Single_Freq.set(frequency=freq_end*MHz, amplitude=1.0, phase=0.0)
            #     delay(time_step*us)
            #     freq_end -= freq_step

            #     print(freq_end)



        # t2 = self.core.get_rtio_counter_mu()

        # print((t2 - t1) * 1e-6)
        
        # print(self.Single_Freq.get_frequency() * 1e-6, "MHz") 
        # 
            