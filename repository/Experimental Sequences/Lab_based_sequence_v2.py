from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64
from artiq.coredevice import ad9910

class Lab_based_Clock_Sequence_v2(EnvExperiment):
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
 


  

    # @kernel
    # def seperate_probe_imaging(self):         #imaging with seperate probe

    #     self.probe_shutter.on()
    #     self.mot_coil_1.write_dac(0, 4.051)
    #     self.mot_coil_2.write_dac(1, 4.088)
    #     with parallel:
    #         self.mot_coil_1.load()
    #         self.mot_coil_2.load()

    #     delay((self.Time_of_Flight +4)*ms)

    #     with parallel:
    #             self.camera_trigger.on()
    #             self.probe.set(frequency=200*MHz, amplitude=0.08)
                
    #     delay(0.5 *ms)
                
    #     with parallel:
    #         self.camera_trigger.off()
    #         self.probe_shutter.off()
    #         self.probe_aom.set(frequency=200*MHz, amplitude=0.00)
    #     #set coil field to zero
    #     #wait for probe shutter to open

    #     delay(10*ms)


    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

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
        self.probe_aom.sw.off()
       # self.lattice_aom.sw.on()

        # Set the RF attenuation
        self.blue_mot_aom.set_att(0.0)
        self.zeeman_slower_aom.set_att(0.0)
        self.probe_aom.set_att(0.0)
        self.red_mot_aom.set_att(0.0)

        #Set the profiles for 689 modulation and single frequency
       


        # Frequency_Modulation = 25000	# In Hz

        # start_freq = 80.0*MHz
        # end_freq = 81.0*MHz
        # N = 500
        # T = int((1 / (N*Frequency_Modulation)) /4e-9)

        # f = [0.]*N
        # f_ram = [0]*N
 
        # f_span = end_freq - start_freq
        # f_step = f_span / N 	
 
        # for i in range(N):
        #     f[i] = start_freq+i*f_step
		
        # self.red_mot_aom.frequency_to_ram(f, f_ram)

        # '''initialize DDS channel'''
        # self.red_mot_aom.cpld.init()
        # self.red_mot_aom.init()
        # self.red_mot_aom.cpld.io_update.pulse(100*ns)
        # self.core.break_realtime()
        # self.red_mot_aom.set_att(0.0*dB)
        # self.red_mot_aom.cpld.set_profile(1)		
        # self.red_mot_aom.set(frequency=80.92*MHz, amplitude=0.05, profile=1)
        # self.red_mot_aom.cpld.io_update.pulse_mu(8)

        # '''prepare RAM profile:'''
        # self.red_mot_aom.set_cfr1() #disable RAM for writing data
        # self.red_mot_aom.cpld.io_update.pulse_mu(8) #I/O pulse to enact RAM change
        # self.red_mot_aom.set_profile_ram(start=0, end=N-1, step=T, profile=0, mode=ad9910.RAM_MODE_CONT_BIDIR_RAMP)
        # self.red_mot_aom.cpld.set_profile(0)
        # self.red_mot_aom.cpld.io_update.pulse_mu(8)

        # '''write data to RAM:'''
        # delay(50*us)
        # self.red_mot_aom.write_ram(f_ram)
        # delay(100*us)

        # '''enable RAM mode (enacted by IO pulse) and fix other parameters:'''
        # self.red_mot_aom.set_cfr1(internal_profile=0, ram_destination=ad9910.RAM_DEST_FTW, ram_enable=1 ,manual_osk_external=0,osk_enable=1,select_auto_osk=0)
        # self.red_mot_aom.set_amplitude(0.0)
        # self.red_mot_aom.cpld.io_update.pulse_mu(8)

        # '''switch on DDS channel'''
        # self.red_mot_aom.sw.on()	



        print("run finished")

        for j in range(int(self.cycles)):          #This runs the actual sequence
            
            delay(1*ms)

            ################ Blue MOT Loading ##########################
            self.blue_mot_aom.set(frequency= 90 * MHz, amplitude=0.06)
            self.zeeman_slower_aom.set(frequency= 70 * MHz, amplitude=0.08)
            # self.probe_aom.set(frequency= 200 * MHz, amplitude=0.18)

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
                
            delay(self.blue_mot_loading_time* ms)
            # self.blue_mot_aom.sw.off()

            ######################## Blue MOT Compression ##############################

            self.zeeman_slower_aom.set(frequency=70 * MHz, amplitude=0.00)   #Turn off the Zeeman Slower
            self.zeeman_slower_shutter.off()
            self.red_mot_aom.sw.on()

            print("Hello")
                
            delay(4.0*ms)                                                 #wait for shutter to close

            # num_steps_com = int(self.blue_mot_compression_time )             #steps of 1ms so num of steps is equivalent to length of ramp, can we get shorter time steps?
            # t_com = self.blue_mot_compression_time / num_steps_com
            # amp_steps = (0.06 - 0.003) / num_steps_com   #initial amplitude to final amplitude

            # bmot_coil_1_low = 7.95              #Starting coil values for coil ramp
            # bmot_coil_2_low = 8.0
            # bmot_coil_1_high = 8.45          #End coil values for coil ramp
            # bmot_coil_2_high = 8.5

            # step_1 = (bmot_coil_1_high - bmot_coil_1_low) / (num_steps_com - 1)
            # ramp_coil_1 = [bmot_coil_1_low + i * step_1 for i in range(num_steps_com)]

            # step_2 = (bmot_coil_2_high - bmot_coil_2_low) / (num_steps_com - 1)
            # ramp_coil_2 = [bmot_coil_2_low + i * step_2 for i in range(num_steps_com)]

            # with parallel: 

            #     # # Ramping the amplitude of the blue MOT beam
            #     for i in range(int(num_steps_com)):
            #         amp = 0.06 - ((i+1) * amp_steps)
            #         self.blue_mot_aom.set(frequency=90*MHz, amplitude=amp)
            #         delay(t_com*ms)

            #     # Ramping the MOT coils
            #     for i in range(len(ramp_coil_1)):
            #         self.mot_coil_1.write_dac(0, ramp_coil_1[i])    #writes coil ramp value to the DAC
            #         self.mot_coil_2.write_dac(1, ramp_coil_2[i])
            #         with parallel:
            #             self.mot_coil_1.load()
            #             self.mot_coil_2.load()
            #             delay(t_com*ms)



            bm_voltage_1 = 8.0
            bm_voltage_2 = 8.0
            voltage_1_com = 8.5
            voltage_2_com = 8.5
            blue_amp = 0.06
            amp_com = 0.00
            steps_com = self.blue_mot_compression_time 
            t_com = self.blue_mot_compression_time/steps_com
            volt_1_steps = (bm_voltage_1 - voltage_1_com)/steps_com
            volt_2_steps = (bm_voltage_2 - voltage_2_com)/steps_com
            amp_steps = (blue_amp-amp_com)/steps_com

            with parallel:
                for i in range(int64(steps_com)):
                    voltage_1 = voltage_1 - volt_1_steps
                    voltage_2 = voltage_2 - volt_2_steps
                    self.mot_coil_1.write_dac(0, voltage_1)
                    self.mot_coil_2.write_dac(1, voltage_2)
                    with parallel:
                        self.mot_coil_1.load()
                        self.mot_coil_2.load()
                    delay(t_com*ms)


                       #     # # Ramping the amplitude of the blue MOT beam

                for i in range(int64(steps_com)):
                    amp_steps = (0.06 - 0.003)/steps_com
                    amp = 0.06 - ((i+1) * amp_steps)
                    self.blue_mot_aom.set(frequency=90*MHz, amplitude=amp)
                    delay(t_com*ms)

            print("Hello 2")

            delay(self.blue_mot_compression_time*ms)

            delay(3000*ms)

        ###################### Broadband Red MOT ############################
        # self.blue_mot_aom.set(frequency=90*MHz,amplitude=0.00)   
        # self.blue_mot_aom.sw.off()                                   #Switch off blue beams
        # self.blue_mot_shutter.off()

        # voltage_1 = 5.3       #Broadband red mot at 5.3G/cm    #Coils are 18 G/cm/A 
        # voltage_2 = 5.3

        # self.mot_coil_1.write_dac(0, voltage_1)
        # self.mot_coil_2.write_dac(1, voltage_2)

        # with parallel:
        #     self.mot_coil_1.load()
        #     self.mot_coil_2.load()
        # delay(self.broadband_red_mot_time*ms)

        # ######################### Red MOT Compression ##########################

        # num_steps_com = int(self.red_mot_compression_time )             #steps of 1ms so num of steps is equivalent to length of ramp, can we get shorter time steps?
        # t_com = self.red_mot_compression_time / num_steps_com
        # amp_steps = (0.05 - 0.003) / num_steps_com   #initial amplitude to final amplitude

        # #we want to ramp the field from 5G/cm to 13G/cm

        # rmot_coil_1_low = 5.3              #Starting coil values for coil ramp
        # rmot_coil_2_low = 5.3
        # rmot_coil_1_high = 5.72          #End coil values for coil ramp
        # rmot_coil_2_high = 5.72

        # step_1 = (rmot_coil_1_high - rmot_coil_1_low) / (num_steps_com - 1)
        # ramp_coil_1 = [rmot_coil_1_low + i * step_1 for i in range(num_steps_com)]

        # step_2 = (rmot_coil_2_high - rmot_coil_2_low) / (num_steps_com - 1)
        # ramp_coil_2 = [rmot_coil_2_low + i * step_2 for i in range(num_steps_com)]


        # # with parallel: 

        #     # # Ramping the amplitude of the blue MOT beam
        #     # for i in range(int64(num_steps_com)):
        #     #     amp = 0.08 - ((i+1) * amp_steps)
        #     #     self.blue_mot_aom.set(frequency=90*MHz, amplitude=amp)
        #     # delay(t_com*ms)


        #     # Ramping the MOT coils
        # for i in range(len(ramp_coil_1)):
        #     self.mot_coil_1.write_dac(0, ramp_coil_1[i])    #writes coil ramp value to the DAC
        #     self.mot_coil_2.write_dac(1, ramp_coil_2[i])
        #     with parallel:
        #         self.mot_coil_1.load()
        #         self.mot_coil_2.load()
        #         delay(t_com*ms)


        # delay(self.red_mot_compression_time*ms)
  
        # ##################### Single Frequency ##################################

        # self.red_mot_aom.set_cfr1()     
        # self.red_mot_aom.cpld.io_update.pulse_mu(8)
        # delay(8*us)
        # self.red_mot_aom.cpld.set_profile(1)     
        # self.red_mot_aom.cpld.io_update.pulse_mu(8)
        # delay(8*us)
     
        # # self.red_mot_aom.cpld.io_update.pulse_mu(8)
