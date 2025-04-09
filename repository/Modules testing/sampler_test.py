from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from artiq.coredevice.sampler import Sampler

# import pandas as pd
from numpy import int32
import numpy as np
import datetime

<<<<<<< HEAD
class sampler_test(EnvExperiment):
    # "asasasasasasssasa"
    def build(self):
        self.setattr_device("core")
        self.ttl:TTLOut=self.get_device("ttl12") 
=======
class TestSampler(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.ttl:TTLOut=self.get_device("ttl4") 
>>>>>>> 45fe2ce731c300daab8e9c8a3acb89407fb4c966
        self.sampler:Sampler = self.get_device("sampler0")

        self.setattr_argument("sample_rate", NumberValue())
        self.setattr_argument("sample_number", NumberValue())

<<<<<<< HEAD
        self.setattr_argument("Number_of_pulse", NumberValue())
        self.setattr_argument("Pulse_width", NumberValue())
        self.setattr_argument("Time_between_pulse", NumberValue())

    # @rpc
    # def save_data(self, filename, data):
    #     current_time = datetime.datetime.now()
    #     current_time = str(current_time.day) + '-' + str(current_time.month) + '-' + str(current_time.year) + '_' + str(current_time.hour) + '-' + str(current_time.minute) + '-' + str(current_time.second)
    #     filenameplusdate = current_time + filename
    #     np.savetxt(filenameplusdate, data)

=======
>>>>>>> 45fe2ce731c300daab8e9c8a3acb89407fb4c966
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.sampler.init()

<<<<<<< HEAD
        delay(4000*ms)
=======
        # delay(40000*ms)
>>>>>>> 45fe2ce731c300daab8e9c8a3acb89407fb4c966

        num_samples = int32(self.sample_number)
        samples = [[0.0 for i in range(8)] for i in range(num_samples)]
        sampling_period = 1/self.sample_rate

        with parallel:
            with sequential:
                for i in range(int64(self.Number_of_pulse)):
                    self.ttl.pulse(self.Pulse_width * ms)
                    delay(self.Time_between_pulse * ms)
            with sequential:
                for j in range(num_samples):
                    self.sampler.sample(samples[j])
                    delay(sampling_period * s)

<<<<<<< HEAD
        delay(5000*ms)
=======
        # delay(5000*ms)
>>>>>>> 45fe2ce731c300daab8e9c8a3acb89407fb4c966

        sample2 = [i[0] for i in samples]
        self.set_dataset("samples", sample2, broadcast=True, archive=True)
        # self.save_data("sampler_test.csv", sample2)
        print(sample2)

        print("Sampler Test Complete")