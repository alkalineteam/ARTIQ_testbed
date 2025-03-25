from artiq.experiment import *
from numpy import int64

class TestAD9912(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.ad9912_0=self.get_device("urukul1_ch0") 
    
        self.setattr_argument("Number_of_pulse", NumberValue(default=10))
        self.setattr_argument("Pulse_width", NumberValue(default=1000)) 
        self.setattr_argument("attenuation", NumberValue(default=20 *dB)) 

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.ad9912_0.cpld.init()
        self.ad9912_0.init()

        self.ad9912_0.sw.on()
        
        self.ad9912_0.set_att(self.attenuation * dB)

        self.ad9912_0.set(frequency=100*MHz)

        # for i in range(int64(self.Number_of_pulse)):
        #     self.ad9912_0.set(frequency=30 * MHz)
        #     delay(self.Pulse_width*ms)
            
        #     self.ad9912_0.set(frequency=90 * MHz)
        #     delay(self.Pulse_width*ms)

        # self.ad9912_0.sw.off()

        print("AD9912 test is done")
