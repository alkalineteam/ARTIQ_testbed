from artiq.experiment import *
from artiq.coredevice import ad9910
from numpy import int64


Frequency_Modulation = 25000	# In Hz

start_freq = 80.0*MHz
end_freq = 81.0*MHz

N = int64((end_freq - start_freq) / Frequency_Modulation)
#T = 64000100
T = 20
 
class AD9910_RAM(EnvExperiment):
 
	def build(self):
		self.setattr_device("core")
		# self.setattr_device("urukul1_cpld") #2nd Urukul module
		self.setattr_device("urukul0_ch0") #Urukul module
		self.ad9910_0 = self.urukul0_ch0

		#self.ad9910_1 = self.setattr_device("urukul0_ch1")
 
	def prepare(self):
 
		#create list of frequencies in FTW format to write to RAM
 
		self.f = [0.]*N
		self.f_ram = [0]*N
 
		f_span = end_freq - start_freq
		f_step = f_span / N 	# 0.025, in case of 25KHz
 
		for i in range(N):
			self.f[i] = start_freq+i*f_step
		print(self.f)
		
		self.ad9910_0.frequency_to_ram(self.f, self.f_ram)
		print(self.f_ram)
 
	@kernel
	def run(self):
		self.core.reset()

		self.core.break_realtime()

		# self.ad9910_1.cpld.init()
		# self.ad9910_1.init()
		# self.ad9910_1.sw.on()

		
		self.ad9910_0.set(frequency=80*MHz, amplitude=1.0)
		
		'''initialize DDS channel'''
		self.ad9910_0.cpld.init()
		self.ad9910_0.init()
		self.ad9910_0.cpld.io_update.pulse(100*ns)
		self.core.break_realtime()
		self.ad9910_0.set_att(0.0*dB)
		self.ad9910_0.cpld.set_profile(1)
		
		self.ad9910_0.set(frequency=84.0*MHz, amplitude=1.0, profile=1)
		self.ad9910_0.cpld.io_update.pulse_mu(8)

		'''prepare RAM profile:'''
		self.ad9910_0.set_cfr1() #disable RAM for writing data
		self.ad9910_0.cpld.io_update.pulse_mu(8) #I/O pulse to enact RAM change
		self.ad9910_0.set_profile_ram(start=0, end=N-1, step=T, profile=0, mode=ad9910.RAM_MODE_CONT_BIDIR_RAMP)
		self.ad9910_0.cpld.set_profile(0)
		self.ad9910_0.cpld.io_update.pulse_mu(8)
 
		'''write data to RAM:'''
		delay(50*us)
		self.ad9910_0.write_ram(self.f_ram)
		delay(100*us)
 
		'''enable RAM mode (enacted by IO pulse) and fix other parameters:'''
		self.ad9910_0.set_cfr1(internal_profile=0, ram_destination=ad9910.RAM_DEST_FTW, ram_enable=1,manual_osk_external=0,osk_enable=1,select_auto_osk=0)
		self.ad9910_0.set_amplitude(1.0)
		# self.ad9910_0.set_att(0.0*dB)
		# self.ad9910_0.set_frequency(80*MHz)
		self.ad9910_0.cpld.io_update.pulse_mu(8)
 
		'''switch on DDS channel'''
		self.ad9910_0.sw.on()	

		delay(5000 * ms)
		# print(self.ad9910_0.get(profile=1))
		print("Testing done!")
		self.ad9910_0.cpld.set_profile(1)
		self.ad9910_0.cpld.io_update.pulse_mu(8)
		'''switch on single-tone mode'''
		
		self.ad9910_0.cpld.set_profile(1)

		

		print("Testing done!")