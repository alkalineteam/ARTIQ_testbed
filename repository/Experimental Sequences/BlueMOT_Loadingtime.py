from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64
from artiq.coredevice import ad9910

class BlueMOT_Loadingtime(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("sampler0")
        
        #Assign all channels
              #TTLs
        self.blue_mot_shutter:TTLOut=self.get_device("ttl4")
        self.repump_shutter_707:TTLOut=self.get_device("ttl5")
        self.zeeman_slower_shutter:TTLOut=self.get_device("ttl6")
        self.probe_shutter:TTLOut=self.get_device("ttl7")
        self.camera_trigger:TTLOut=self.get_device("ttl8")
        self.clock_shutter:TTLOut=self.get_device("ttl9")
        self.repump_shutter_679:TTLOut=self.get_device("ttl10")

        self.pmt_shutter:TTLOut=self.get_device("ttl10")
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
        #self.setattr_argument("blue_mot_loading_time", NumberValue(default=2000))
        self.setattr_argument("blue_mot_compression_time", NumberValue(default=20))
        self.setattr_argument("blue_mot_cooling_time", NumberValue(default=1000))
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

         for loading_time in range(50, 2001, 50):  # Loading time ranges from 50 to 1000ms in increments of 50
           self.blue_mot_loading_time = loading_time * ms
  
            delay(self.blue_mot_loading_time)
            print("Blue On")
            # self.blue_mot_aom.sw.off()
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
 def Sampler(self):
    self.core.break_realtime()                   #timebreak
    self.sampler0.init()                  #Initilises sampler
    n_samples = 10 
    self.set_dataset("samples",np.full(n_samples,np,nan)broadcast = true)        #creates data set 


    n_channels = 1

    self.core.break_realtime()
    for i in range (n_channels):               
        self.sampler0.set_gain_mu(7-i,0)          #sets channels gain to 0db

    smp = [0]*n_channels   

    for n in range(n_samples):
        delay(90*us)
        self.sampler0.sample_mu(smp)          #runs sampler and saves to list 
        self.mutate_dataset("samples",n,smp[0])         

        

 for j in range(10):      #Runs 10 times per cooling time
            
            ################ Blue MOT Loading ##########################
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
                
            delay(self.blue_mot_loading_time)
            
            # self.blue_mot_aom.sw.off()

            ######################## Blue MOT Compression ##############################

            self.zeeman_slower_aom.set(frequency=70 * MHz, amplitude=0.00)   #Turn off the Zeeman Slower
            self.zeeman_slower_shutter.off()
            self.red_mot_aom.sw.on()
                
            delay(4.0*ms)                                                 #wait for shutter to close

            num_steps_com = int(self.blue_mot_compression_time )             #steps of 1ms so num of steps is equivalent to length of ramp, can we get shorter time steps?
            t_com = self.blue_mot_compression_time / num_steps_com
            amp_steps = (0.06 - 0.003) / num_steps_com   #initial amplitude to final amplitude

            bmot_coil_1_low = 7.95              #Starting coil values for coil ramp
            bmot_coil_2_low = 8.0
            bmot_coil_1_high = 8.45          #End coil values for coil ramp
            bmot_coil_2_high = 8.5

            step_1 = (bmot_coil_1_high - bmot_coil_1_low) / (num_steps_com - 1)
            ramp_coil_1 = [bmot_coil_1_low + i * step_1 for i in range(num_steps_com)]

            step_2 = (bmot_coil_2_high - bmot_coil_2_low) / (num_steps_com - 1)
            ramp_coil_2 = [bmot_coil_2_low + i * step_2 for i in range(num_steps_com)]

            with parallel: 

                # # Ramping the amplitude of the blue MOT beam
                for i in range(int64(num_steps_com)):
                    amp = 0.06 - ((i+1) * amp_steps)
                    self.blue_mot_aom.set(frequency=90*MHz, amplitude=amp)
                    delay(t_com*ms)

                # Ramping the MOT coils
                for i in range(len(ramp_coil_1)):
                    self.mot_coil_1.write_dac(0, ramp_coil_1[i])    #writes coil ramp value to the DAC
                    self.mot_coil_2.write_dac(1, ramp_coil_2[i])
                    with parallel:
                        self.mot_coil_1.load()
                        self.mot_coil_2.load()
                        delay(t_com*ms)


            delay(self.blue_mot_compression_time*ms)
