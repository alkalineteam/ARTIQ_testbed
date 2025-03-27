from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64
from artiq.coredevice import ad9910

class Lab_based_Clock_Sequence(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        
        #Assign all channels
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
        
             
        self.setattr_argument("cycles", NumberValue(default=1))
        self.setattr_argument("blue_mot_loading_time", NumberValue(default=2000))
        self.setattr_argument("blue_mot_compression_time", NumberValue(default=20))
        self.setattr_argument("blue_mot_cooling_time", NumberValue(default=60))
        self.setattr_argument("broadband_red_mot_time", NumberValue(default=10))
        self.setattr_argument("red_mot_compression_time", NumberValue(default=20))
        self.setattr_argument("single_frequency_time", NumberValue(default=30))
        self.setattr_argument("time_of_flight", NumberValue(default=30))
 

    @kernel
    def initialise(self):
        
        # Initialize the modules
      #  self.camera_shutter.output()
        self.camera_trigger.output()
        self.blue_mot_shutter.output()
      #  self.red_mot_shutter.output()
        self.zeeman_slower_shutter.output()
        self.repump_shutter_707.output()
        self.repump_shutter_679.output()
        self.probe_shutter.output()
        self.clock_shutter.output()
     #   self.pmt_shutter.output()
        self.mot_coil_1.init()
        self.mot_coil_2.init()
        self.blue_mot_aom.cpld.init()
        self.blue_mot_aom.init()
        self.zeeman_slower_aom.cpld.init()
        self.zeeman_slower_aom.init()
        self.probe_aom.cpld.init()
        self.probe_aom.init()
        self.red_mot_aom.cpld.init()
        self.red_mot_aom.init()
        self.lattice_aom.cpld.init()
        self.lattice_aom.init()

        # Set the RF channels ON
        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
        self.red_mot_aom.sw.on()
        self.probe_aom.sw.on()
       # self.lattice_aom.sw.on()

        # Set the RF attenuation
        self.blue_mot_aom.set_att(0.0)
        self.zeeman_slower_aom.set_att(0.0)
        self.probe_aom.set_att(0.0)
        self.red_mot_aom.set_att(0.0)

        #Set the profiles for 689 modulation and single frequency
        delay(500*us)

    @kernel
    def dds_profile_init(self):
         
        Frequency_Modulation = 25000	# In Hz

        start_freq = 80.0*MHz
        end_freq = 81.0*MHz
        N = 500
        T = int((1 / (N*Frequency_Modulation)) /4e-9)

        f = [0.]*N
        f_ram = [0]*N
 
        f_span = end_freq - start_freq
        f_step = f_span / N 	
 
        for i in range(N):
            f[i] = start_freq+i*f_step
		
        self.red_mot_aom.frequency_to_ram(f, f_ram)

        self.red_mot_aom.cpld.init()
        self.red_mot_aom.init()
        self.red_mot_aom.cpld.io_update.pulse(100*ns)
        self.core.break_realtime()
        self.red_mot_aom.set_att(0.0*dB)
        self.red_mot_aom.cpld.set_profile(1)		
        self.red_mot_aom.set(frequency=80.92*MHz, amplitude=0.05, profile=1)
        self.red_mot_aom.cpld.io_update.pulse_mu(8)

        '''prepare RAM profile:'''
        self.red_mot_aom.set_cfr1() #disable RAM for writing data
        self.red_mot_aom.cpld.io_update.pulse_mu(8) #I/O pulse to enact RAM change
        self.red_mot_aom.set_profile_ram(start=0, end=N-1, step=T, profile=0, mode=ad9910.RAM_MODE_CONT_BIDIR_RAMP)
        self.red_mot_aom.cpld.set_profile(0)
        self.red_mot_aom.cpld.io_update.pulse_mu(8)
 
        '''write data to RAM:'''
        delay(50*us)
        self.red_mot_aom.write_ram(f_ram)
        delay(100*us)
 
        '''enable RAM mode (enacted by IO pulse) and fix other parameters:'''
        self.red_mot_aom.set_cfr1(internal_profile=0, ram_destination=ad9910.RAM_DEST_FTW, ram_enable=1 ,manual_osk_external=0,osk_enable=1,select_auto_osk=0)
        self.red_mot_aom.set_amplitude(0.05)
        self.red_mot_aom.cpld.io_update.pulse_mu(8)
  
    
    def blue_mot_loading(self):               #Loading the Atoms into the Blue MOT
         # blue_amp = 0.08
            self.blue_mot_aom.set(frequency= 90 * MHz, amplitude=0.06)
            self.zeeman_slower_aom.set(frequency= 70 * MHz, amplitude=0.08)
            self.probe_aom.set(frequency= 200 * MHz, amplitude=0.18)

            self.blue_mot_aom.sw.on()
            self.zeeman_slower_aom.sw.on()
            
            
            voltage_1 = 7.95
            voltage_2 = 8.0
            self.mot_coil_1.write_dac(0, voltage_1)
            self.mot_coil_2.write_dac(1, voltage_2)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
                self.blue_mot_shutter.on()
                self.probe_shutter.off()
                self.zeeman_slower_shutter.on()
                self.repump_shutter_707.on()
                self.repump_shutter_679.on()
               

            
            # self.blue_mot_aom.sw.off()
            self.red_mot_aom.cpld.set_profile(0)
            self.red_mot_aom.cpld.io_update.pulse_mu(8)
            self.red_mot_aom.sw.on()

    @kernel
    def blue_mot_compression(self):           #We compress the Blue MOT here by ramping up the magnetic field gradient and ramping down the optical power
            
        
        self.zeeman_slower_aom.set(frequency=70 * MHz, amplitude=0.00)   #Turn off the Zeeman Slower, could ramp this down too?
        self.zeeman_slower_shutter.off()
            
     
        delay(4.0*ms)                                                 #wait for shutter to close

        num_steps_com = int(self.blue_mot_compression_time )             #steps of 1ms so num of steps is equivalent to length of ramp, can we get shorter time steps?
        t_com = self.blue_mot_compression_time / num_steps_com
        amp_steps = (0.08 - 0.003) / num_steps_com   #initial amplitude to final amplitude


        bmot_coil_1_low = 7.95              #Starting coil values for coil ramp
        bmot_coil_2_low = 8.0
        bmot_coil_1_high = 8.45          #End coil values for coil ramp
        bmot_coil_2_high = 8.5

        step_1 = (bmot_coil_1_high - bmot_coil_1_low) / (num_steps_com - 1)
        ramp_coil_1 = [bmot_coil_1_low + i * step_1 for i in range(num_steps_com)]

        step_2 = (bmot_coil_2_high - bmot_coil_2_low) / (num_steps_com - 1)
        ramp_coil_2 = [bmot_coil_2_low + i * step_2 for i in range(num_steps_com)]


        # with parallel: 

            # # Ramping the amplitude of the blue MOT beam
            # for i in range(int64(num_steps_com)):
            #     amp = 0.08 - ((i+1) * amp_steps)
            #     self.blue_mot_aom.set(frequency=90*MHz, amplitude=amp)
            # delay(t_com*ms)


            # Ramping the MOT coils
        for i in range(len(ramp_coil_1)):
            self.mot_coil_1.write_dac(0, ramp_coil_1[i])    #writes coil ramp value to the DAC
            self.mot_coil_2.write_dac(1, ramp_coil_2[i])
            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
                delay(t_com*ms)


        delay(self.blue_mot_compression_time*ms)

    @kernel
    def broadband_red_mot(self):              #We will turn on the Red MOT beams after the loading phase, then as soon as atoms are cool enough they will begin to cool under the red transition

        self.blue_mot_aom.set(frequency=90*MHz,amplitude=0.00)
        self.blue_mot_shutter.off()

        voltage_1 = 2.46
        voltage_2 = 2.23

        self.mot_coil_1.write_dac(0, voltage_1)
        self.mot_coil_2.write_dac(1, voltage_2)

        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()
        delay(self.broadband_red_mot_time*ms)

    @kernel
    def red_mot_compression(self):            #Ramping up the field from 5 G/cm to 13 G/cm and then reducing red optical power from 26mW/cm^2 to 114uW/cm^2   

            num_steps_com = self.red_mot_compression_time              #steps of 1ms so num of steps is equivalent to length of ramp, can we get shorter time steps?
            t_com = self.red_mot_compression_time / num_steps_com
            amp_steps = (0.08 - 0.003) / num_steps_com   #initial amplitude to final amplitude


            rmot_coil_1_low = 4              #Starting coil values for coil ramp
            rmot_coil_2_low = 4
            rmot_coil_1_high = 2.7           #End coil values for coil ramp
            rmot_coil_2_high = 2.7

            ramp_coil_1 = np.linspace(rmot_coil_1_low,rmot_coil_1_high,num_steps_com)      #Generate values for coil ramp
            ramp_coil_2 = np.linspace(rmot_coil_2_low,rmot_coil_2_high,num_steps_com)

            with parallel: 
           
                for i in range(int64(num_steps_com)):        # Ramping down the amplitude of the red MOT beam
                    amp = 0.08 - ((i+1) * amp_steps)
                    self.red_mot_aom.set_amplitude(amp)
                    delay(t_com*ms)

                for i in range(len(ramp_coil_1)):                   # Ramping the MOT coils
                    self.mot_coil_1.write_dac(0, ramp_coil_1[i])    #w rites coil ramp value to the DAC
                    self.mot_coil_2.write_dac(1, ramp_coil_2[i])
                    with parallel:
                        self.mot_coil_1.load()
                        self.mot_coil_2.load()
                    delay(t_com*ms)

            delay(self.red_mot_compression_time*ms)

    @kernel
    def single_frequency_red_mot(self):       #Turn off the broadband_modulation for the red beam
        self.red_mot_aom.cpld.set_profile(0)
        self.ad9910_0.cpld.io_update.pulse_mu(8)
 
        
        
        # self.red_mot_aom.set(amplitude=0.08,frequency=self.rmot_single_frequency*MHz)      #Turns off the modulation of the 
        # self.red_mot_aom.set_cfr1(ram_enable=0)

        delay(self.single_frequency_time)
        self.red_mot_aom.sw.off

    @kernel
    def seperate_probe_imaging(self):         #imaging with seperate probe

        self.probe_shutter.on()
        self.mot_coil_1.write_dac(0, 4.051)
        self.mot_coil_2.write_dac(1, 4.088)
        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()

        delay((self.Time_of_Flight +4)*ms)

        with parallel:
                self.camera_trigger.on()
                self.probe.set(frequency=200*MHz, amplitude=0.08)
                
        delay(0.5 *ms)
                
        with parallel:
            self.camera_trigger.off()
            self.probe_shutter.off()
            self.probe_aom.set(frequency=200*MHz, amplitude=0.00)
        #set coil field to zero
        #wait for probe shutter to open

        delay(10*ms)

    def red_modulation_on(self,low_frequency,high_frequency,modulation_frequency,step_size):
        self.core.break_realtime()
        
        #generate list of values to be read in the RAM profile
        period = 1 / modulation_frequency
        num_steps = int(period/ step_size) #1 step is equivalent to 4 ns 
        
        t = np.linspace(0,period,num_steps,endpoint=False)
        modulation = low_frequency + (high_frequency) * 2 * np.abs(t / period - np.floor(t / period + 0.5)) #Generates all of the frequency values to be stored in the list

        self.frequency_ram_list = [0] * len(modulation)          #creates list for RAM values to be stored in later

        self.dds.set_cfr1(ram_enable=0)                         #ram needs to be set to zero to turn off frequency 
        self.cpld0.io_update.pulse(8)

        self.dds.set_profile_ram(start=0, end=len(self.asf_ram)-1,step=self.step_size, profile=0, mode=ad9910.RAM_MODE_CONT_BIDIR_RAMP) 
        # #gives start and end adresses of where to look within the RAM
        #step length, i.e. how long to run each element of the list. 1 step = 4ns
        self.cpld0.io_update.pulse_mu(8) 

        self.dds.frequency_to_ram(modulation,self.frequency_ram_list) 
        self.dds.write_ram(self.frequency_ram_list)                     #converts the quantity we gave it into RAM profile data. Fill up the empty list we defined earlier
        self.core.break_realtime()

        self.dds.set(amplitude=0.08,ram_destination=ad9910.RAM_DEST_FTW) 


        #must set the control function register ram_enable to 1 to enable ram playback
        self.dds.set_cfr1(internal_profile=0, ram_enable = 1, ram_destination=ad9910.RAM_DEST_FTW, manual_osk_external=0, osk_enable=1, select_auto_osk=0) #for frequency modulation

        self.cpld0.io_update.pulse_mu(8)

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        
        # self.dds_profile_init()
        self.initialise()  
        delay(2*ms)
        for j in range(int64(self.cycles)):          #This runs the actual sequence
                delay(1*ms)
                print(j)
                @kernel                         #Maybe this @kernel could fix the code not looping
                self.blue_mot_loading()

                self.blue_mot_shutter.off()

                self.camera_trigger.pulse(100*ms)
                delay(500 * ms)

            # if self.blue_mot_compression_time() == 0.0:            #If we are giving the time of a slice to be 0, then we will not run the slice but instead just image with the separate probe
            #     self.seperate_probe_imaging                      #this stat
            #     continue
             
            # self.blue_mot_aom.sw.off()
 
            # with parallel:
                # self.blue_mot_compression()                    #We compress the blue MOT and turn on the red beam's on to start transferring atoms across
    
            # if self.blue_mot_cooling_time == 0: 
            #     self.seperate_probe_imaging
            #     continue

            # delay(self.blue_mot_cooling_time*ms)

            # if self.broadband_red_mot_time() == 0: 
            #     self.seperate_probe_imaging
            #     continue
             
            # self.broadband_red_mot()
            
            # if self.red_mot_compression_time == 0: 
            #     self.seperate_probe_imaging
            #     continue
             
            # self.red_mot_compression()
            
            # if self.single_frequency_time == 0:
            #     self.seperate_probe_imaging
            #     continue

            # self.single_frequency_red_mot()


            # self.seperate_probe_imaging()
