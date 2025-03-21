from artiq.experiment import *
from artiq.coredevice import ad9910
import numpy as np
 
N = 1024
f1 = 75.*MHz
f2 = 85.*MHz
T = int(1e8)
 
class DDS_freq_ramp(EnvExperiment):
 
	def build(self):
		self.setattr_device("core")
		# self.setattr_device("urukul1_cpld") #2nd Urukul module
		self.setattr_device("urukul0_ch0") #Urukul module
		self.u = self.urukul0_ch0
 
	def prepare(self):
 
		#create list of frequencies in FTW format to write to RAM
 
		self.f = [0.]*N
		self.f_ram = [0]*N
 
		f_span = f2 - f1
		f_step = f_span / N
 
		for i in range(N):
			self.f[i] = f1+i*f_step
		self.u.frequency_to_ram(self.f,self.f_ram)
 
	@kernel
	def run(self):
		self.core.reset()
		
		'''initialize DDS channel'''
		self.u.cpld.init()
		self.u.init()
		self.u.cpld.io_update.pulse(100*ns)
		self.core.break_realtime()
		self.u.set_amplitude(1.)
		self.u.set_att(0.*dB)
		self.u.set(80.*MHz)
 
		'''prepare RAM profile:'''
		self.u.set_cfr1() #disable RAM for writing data
		self.u.cpld.io_update.pulse_mu(8) #I/O pulse to enact RAM change
		self.u.set_profile_ram(start=0, end=N-1, step=T, profile=0, mode=ad9910.RAM_MODE_CONT_BIDIR_RAMP)
		self.u.cpld.set_profile(0)
		self.u.cpld.io_update.pulse_mu(8)
 
		'''write data to RAM:'''
		delay(50*us)
		self.u.write_ram(self.f_ram)
		delay(100*us)
 
		'''enable RAM mode (enacted by IO pulse) and fix other parameters:'''
		self.u.set_cfr1(internal_profile=0,ram_destination=ad9910.RAM_DEST_FTW, ram_enable=1)
		self.u.set_amplitude(1.)
		self.u.set_att(10.*dB)
		self.u.cpld.io_update.pulse_mu(8)
 
		'''switch on DDS channel'''
		self.u.sw.on()	