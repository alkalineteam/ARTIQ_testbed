from artiq.experiment import *

import numpy as np

class TestZotino(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.zotino=self.get_device("zotino0")

        self.setattr_argument("Voltage", NumberValue(default=0))

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.zotino.init()

        self.zotino.write_dac(0, self.Voltage)  
        self.zotino.load()

        print("Zotino tested successfully!") 