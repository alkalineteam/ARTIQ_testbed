from artiq.experiment import *
from numpy import int64, int32

class TestAD9910(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.ad9910_0=self.get_device("urukul0_ch0") 
    
        self.setattr_argument("Number_of_pulse", NumberValue(default=10))
        self.setattr_argument("Pulse_width", NumberValue(default=1000)) 

    @kernel
    def run(self):
        # self.core.reset()
        self.core.break_realtime()

        self.ad9910_0.cpld.init()
        self.ad9910_0.init()

        self.ad9910_0.sw.on()
        
        self.ad9910_0.set_att(0.0)


        ''' Switch between frequencies'''
        # for i in range(int64(self.Number_of_pulse)):
        #     self.ad9910_0.set(frequency=30 * MHz, amplitude=1.0)
        #     delay(self.Pulse_width*ms)
        #     self.ad9910_0.set(frequency=90 * MHz, amplitude=1.0)
        #     delay(self.Pulse_width*ms)


        '''Single Frequency Output'''
        self.ad9910_0.set(frequency=80*MHz, amplitude=0.06)



        # self.ad9910_0.cfg_sw(True)

        # delay(1000*ms)

        # self.ad9910_0.cfg_sw(False)

        # self.ad9910_0.sw.off()

        print("AD9910 test is done")
