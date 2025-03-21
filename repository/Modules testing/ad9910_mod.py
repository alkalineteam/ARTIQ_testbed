from artiq.experiment import *
from numpy import int64

class AD9910_mod(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.ad9910_0=self.get_device("urukul0_ch0") 
    
        # self.setattr_argument("Cycles", NumberValue(default=10))
        # self.setattr_argument("Pulse_width", NumberValue(default=1000)) 

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.ad9910_0.cpld.init()
        self.ad9910_0.init()

        self.ad9910_0.sw.on()
        
        self.ad9910_0.set_att(0.0)

        # # for i in range(int64(self.Cycles)):
        # start_freq = 80.0 * MHz
        # end_freq = 85.0 * MHz
        # steps = (end_freq - start_freq) / 5
        # freq = start_freq

        # for i in range(int64(10)):
        #     for i in range (int64(5)):                
        #         self.ad9910_0.set(frequency = freq * MHz, amplitude = 1.0)
        #         delay(steps * ms)
        #         print(freq)
        #         freq += steps



        # # self.ad9910_0.sw.off()

        self.ad9910_0.set(frequency = 80 * MHz, amplitude = 1.0)

        print("AD9910 test is done")
