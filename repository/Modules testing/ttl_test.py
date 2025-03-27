from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64

class TestTTL(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.ttl:TTLOut=self.get_device("ttl10") 

        self.setattr_argument("Number_of_pulse", NumberValue(default=10))
        self.setattr_argument("Pulse_width", NumberValue(default=100))
        self.setattr_argument("Time_between_pulse", NumberValue(default=100))


    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        for i in range(int64(self.Number_of_pulse)):
            self.ttl.pulse(self.Pulse_width*ms)
            delay(self.Time_between_pulse * ms)

        print("TTL test is done")