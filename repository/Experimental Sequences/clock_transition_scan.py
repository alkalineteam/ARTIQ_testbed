from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64, int32, max, float64, float32
import numpy as numpy
from artiq.coredevice import ad9910
import pandas as pd
import os
import csv
from datetime import datetime

default_cfr1 = (
    (1 << 1)    # configures the serial data I/O pin (SDIO) as an input only pin; 3-wire serial programming mode
)
default_cfr2 = (
    (1 << 5)    # forces the SYNC_SMP_ERR pin to a Logic 0; this pin indicates (active high) detection of a synchronization pulse sampling error
    | (1 << 16) # a serial I/O port read operation of the frequency tuning word register reports the actual 32-bit word appearing at the input to the DDS phase accumulator (i.e. not the contents of the frequency tuning word register)
    | (1 << 24) # the amplitude is scaled by the ASF from the active profile (without this, the DDS outputs max. possible amplitude -> cracked AOM crystals)
)

class clock_transition_scan(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        
        self.sampler:Sampler = self.get_device("sampler0")
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
        
        self.setattr_argument("scan_center_frequency_Hz", NumberValue(default=85000000 * Hz))
        self.setattr_argument("scan_range_Hz", NumberValue(default=500000 * Hz))
        self.setattr_argument("scan_step_size_Hz", NumberValue(default=1000 * Hz))
        self.setattr_argument("rabi_pulse_duration_ms", NumberValue(default= 60 * ms))
        self.setattr_argument("clock_intensity", NumberValue(default=0.05))
        self.setattr_argument("bias_field_mT", NumberValue(default=3.0))
        self.setattr_argument("blue_mot_loading_time", NumberValue(default=2000 * ms))


        
        scan_start = int32(self.scan_center_frequency_Hz - (int32(self.scan_range_Hz )/ 2))
        scan_end =int32(self.scan_center_frequency_Hz + (int32(self.scan_range_Hz ) / 2))
        self.scan_frequency_values = [float(x) for x in range(scan_start, scan_end, int32(self.scan_step_size_Hz))]
        self.cycles = len(self.scan_frequency_values)

        self.gs_list = [0.0] * self.cycles
        self.es_list = [0.0] * self.cycles
        self.excitation_fraction_list = [0.0] * self.cycles



    @kernel
    def initialise_modules(self):
            
        delay(1000*ms)

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
        # self.red_mot_aom.sw.on()
        self.probe_aom.sw.off()
        # self.lattice_aom.sw.on()

        # Set the RF attenuation
        self.blue_mot_aom.set_att(0.0)
        self.zeeman_slower_aom.set_att(0.0)
        self.probe_aom.set_att(0.0)
        self.red_mot_aom.set_att(0.0)

        delay(100*ms)

    @kernel
    def blue_mot_loading(self,bmot_voltage_1,bmot_voltage_2):                  
        self.blue_mot_aom.set(frequency= 90 * MHz, amplitude=0.06)
        self.zeeman_slower_aom.set(frequency= 70 * MHz, amplitude=0.08)

        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
    
        self.mot_coil_1.write_dac(0, bmot_voltage_1)
        self.mot_coil_2.write_dac(1, bmot_voltage_2)

        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()
            self.blue_mot_shutter.on()
            self.probe_shutter.off()
            self.zeeman_slower_shutter.on()
            self.repump_shutter_707.on()
            self.repump_shutter_679.on()
    
    @kernel
    def blue_mot_compression(self,bmot_voltage_1,bmot_voltage_2,compress_bmot_volt_1,compress_bmot_volt_2,bmot_amp,compress_bmot_amp,compression_time):

        self.zeeman_slower_aom.set(frequency=70 * MHz, amplitude=0.00)   #Turn off the Zeeman Slower
        self.zeeman_slower_shutter.off()
        self.red_mot_aom.sw.on()
        delay(4.0*ms)                                                 #wait for shutter to close

        steps_com = compression_time 
        t_com = compression_time/steps_com
        volt_1_steps = (compress_bmot_volt_1 - bmot_voltage_1)/steps_com
        volt_2_steps = (compress_bmot_volt_2 - bmot_voltage_2 )/steps_com
        amp_steps = (bmot_amp-compress_bmot_amp)/steps_com
    
        for i in range(int64(steps_com)):

            voltage_1 = bmot_voltage_1 + ((i+1) * volt_1_steps)
            voltage_2 = bmot_voltage_2 + ((i+1) * volt_2_steps)
            amp = bmot_amp - ((i+1) * amp_steps)

            self.mot_coil_1.write_dac(0, voltage_1)
            self.mot_coil_2.write_dac(1, voltage_2)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
                self.blue_mot_aom.set(frequency=90*MHz, amplitude=amp)
            
            delay(t_com*ms)

    @kernel
    def broadband_red_mot(self,rmot_voltage_1,rmot_voltage_2):      
             
        self.blue_mot_aom.set(frequency=90*MHz,amplitude=0.00)   
        self.blue_mot_aom.sw.off()                                   #Switch off blue beams
        self.repump_shutter_679.off()
        self.repump_shutter_707.off()
        self.blue_mot_shutter.off()
        delay(3.9*ms)

        self.mot_coil_1.write_dac(0, rmot_voltage_1)
        self.mot_coil_2.write_dac(1, rmot_voltage_2)

        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()
    
    @kernel
    def red_mot_compression(self,bb_rmot_volt_1,bb_rmot_volt_2,sf_rmot_volt_1,sf_rmot_volt_2,f_start,f_end,A_start,A_end,comp_time):

        start_freq = f_start
        end_freq = f_end


        bb_rmot_amp = A_start
        compress_rmot_amp= A_end

        
        step_duration = 0.1
        steps_com = int(comp_time / step_duration)  

        freq_steps = (start_freq - end_freq)/steps_com

        volt_1_steps = (sf_rmot_volt_1 - bb_rmot_volt_1)/steps_com
        volt_2_steps = (sf_rmot_volt_2 - bb_rmot_volt_2)/steps_com


        amp_steps = (bb_rmot_amp-compress_rmot_amp)/steps_com
        

        for i in range(int64(steps_com)):
            voltage_1 = bb_rmot_volt_1 + ((i+1) * volt_1_steps)
            voltage_2 = bb_rmot_volt_2 + ((i+1) * volt_2_steps)
            amp = bb_rmot_amp - ((i+1) * amp_steps)
            freq = start_freq - ((i+1) * freq_steps)

            self.mot_coil_1.write_dac(0, voltage_1)
            self.mot_coil_2.write_dac(1, voltage_2)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
                self.red_mot_aom.set(frequency = freq * MHz, amplitude = amp)
                
            
            delay(step_duration*ms)
        
    @kernel 
    def seperate_probe(self,tof,probe_duration,probe_frequency):
            with parallel:
                self.red_mot_aom.sw.off()
                self.blue_mot_aom.sw.off()
                self.repump_shutter_679.off()
                self.repump_shutter_707.off()
                self.probe_shutter.on()

            self.mot_coil_1.write_dac(0, 5.0)  
            self.mot_coil_2.write_dac(1, 5.0)
           
            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()

            delay(((tof +3.9)*ms))

            with parallel:
                    self.camera_trigger.pulse(2*ms)
                    self.probe_aom.set(frequency=205 *MHz, amplitude=0.18)
                    self.probe_aom.sw.on()
                    
            delay(probe_duration)
                    
            with parallel:
                self.probe_shutter.off()
                  #Camera shutter takes 26ms to open so we will open it here
                self.probe_aom.set(frequency=probe_frequency, amplitude=0.00)
                self.probe_aom.sw.off()

            delay(10*ms)
    @kernel
    def clock_spectroscopy(self,aom_frequency,pulse_time):                     #Switch to Helmholtz field, wait, then generate Rabi Pulse
       
        self.red_mot_aom.sw.off()
        self.stepping_aom.sw.off()

        comp_field = 1.35 * 0.14    # comp current * scaling factor from measurement
        bias_at_coil = (self.bias_field_mT - comp_field)/ 0.914   #bias field dips in center of coils due to geometry, scaling factor provided by modelling field
        current_per_coil = ((bias_at_coil) / 2.0086) / 2   
        coil_1_voltage = current_per_coil + 5.0
        coil_2_voltage = 5.0 - (current_per_coil / 0.94 )           #Scaled against coil 1
       
       
         #Switch to Helmholtz
        self.mot_coil_1.write_dac(0, coil_1_voltage)  
        self.mot_coil_2.write_dac(1, coil_2_voltage)
        
        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()

        # self.pmt_shutter.on()
        # self.camera_shutter.on()
        self.clock_shutter.on()    

        delay(50*ms)  #wait for coils to switch

        #rabi spectroscopy pulse
        self.stepping_aom.set(frequency = aom_frequency * Hz)
        self.stepping_aom.sw.on()
        delay(pulse_time*ms)
        self.stepping_aom.sw.off()
        self.stepping_aom.set(frequency = 0 * Hz)
        self.stepping_aom.sw.off()
   

    @kernel
    def normalised_detection(self,j,excitation_fraction_list):        #This function should be sampling from the PMT at the same time as the camera being triggered for seperate probe
        self.core.break_realtime()
        sample_period = 1 / 40000     #10kHz sampling rate should give us enough data points
        sampling_duration = 0.06      #30ms sampling time to allow for all the imaging slices to take place

        num_samples = int32(sampling_duration/sample_period)
        print(num_samples)
        samples = [[0.0 for i in range(8)] for i in range(num_samples)]
    
        with parallel:
    
            with sequential:
                ##########################Ground State###############################
                
                with parallel:
                    self.blue_mot_aom.sw.off()
                    self.probe_shutter.on()

                self.mot_coil_1.write_dac(0, 5.0)   #Set 0 field 
                self.mot_coil_2.write_dac(1, 5.0)

                with parallel:
                    self.mot_coil_1.load()
                    self.mot_coil_2.load()

                delay(4.1*ms)     #wait for shutter to open

                with parallel:
                    self.camera_trigger.pulse(1*ms)
                    self.probe_aom.set(frequency=205 * MHz, amplitude=0.18)
                    self.probe_aom.sw.on()

                delay(0.3* ms)      #Ground state probe duration            
                
                with parallel:
                    self.probe_shutter.off()
                    self.probe_aom.sw.off()

                delay(5*ms)                         #repumping 
               
                with parallel:
                    self.repump_shutter_679.pulse(10*ms)
                    self.repump_shutter_707.pulse(10*ms)

                delay(10*ms)                         #repumping 

                # ###############################Excited State##################################

                self.probe_shutter.on()
                delay(4.1*ms) 

                self.probe_aom.sw.on()
                delay(0.3*ms)            #Ground state probe duration
                self.probe_aom.sw.off()
                # self.probe_shutter.off()
                print("stuck")
                delay(20*ms)

                # self.probe_shutter.on()
                # delay(4.1*ms)


                #  ########################Background############################
 
                self.probe_aom.sw.on()
                delay(0.2*ms)            #Ground state probe duration
                self.probe_aom.sw.off()
                self.probe_shutter.off()

                delay(7*ms)
                
            with sequential:
                for k in range(num_samples):
                    self.sampler.sample(samples[k])
                    delay(sample_period*s)
                
        delay(sampling_duration*s)

        samples_ch0 = [i[0] for i in samples]
        

        self.set_dataset("excitation_fraction", samples_ch0, broadcast=True, archive=True)

        # print(self.excitation_fraction(samples_ch0))
                                 
        #     # Split the samples



        gs = samples_ch0[0:600]
        es = samples_ch0[700:1300]
        bg = samples_ch0[1300:1900]

        # gs_max = gs[0]
        # es_max = es[0]
        # bg_max = bg[0]

        # Loop through the rest of the list
        # with parallel:
        #     for num in gs[1:]:
        #         if num > gs_max:
        #             gs_max = num

        #     for num in es[1:]:
        #         if num > es_max:
        #             es_max = num

        #     for num in bg[1:]:
        #         if num > bg_max:
        #             bg_max = num
        

        # if es_max < bg_max:
        #     es_max = bg_max

        # numerator = es_max - bg_max
        # denominator = (gs_max - bg_max) + (es_max - bg_max)

        # if denominator != 0:
        #     excitation_fraction = numerator / denominator
        # else:
        #     excitation_fraction = float(0) # or 0.5 or some fallback value depending on experiment
        # self.gs_list[j] = float(gs_max)
        # self.es_list[j] = float(es_max)
        # self.excitation_fraction_list[j] = float(excitation_fraction)


        gs_counts = 0.0
        es_counts = 0.0
        bg_counts = 0.0

        measurement_time = 600.0 * sample_period     #set to 600 as each slice size is 600 samples at the moment,
                                                     # we should trim this tighter to the peaks to avoid added noise

        for i in gs[1:]:
            gs_counts = gs_counts + gs[i]        
            es_counts = es_counts + es[i]
            bg_counts = bg_counts + bg[i]
     

        gs_measurement = gs_counts * measurement_time         #integrates over the slice time to get the total photon counts
        es_measurement = es_counts * measurement_time
        bg_measurement = bg_counts * measurement_time 
                
        #if we want the PMT to determine atom no, we will probably want photon counts,
        # will need expected collection efficiency of the telescope,Quantum efficiency etc, maybe use the camera atom no calculation to get this


        numerator = es_measurement - bg_measurement
        denominator = (gs_measurement - bg_measurement) + (es_measurement - bg_measurement)

        if denominator != 0.0:
            excitation_fraction = numerator / denominator
        else:
            excitation_fraction = float(0) # or 0.5 or some fallback value depending on experiment
        self.gs_list[j] = float(gs_measurement)
        self.es_list[j] = float(es_measurement)
        self.excitation_fraction_list[j] = float(excitation_fraction)
        
        # # ef.append(self.excitation_fraction_list)


       


      
      

    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.initialise_modules()

        #Sequence Parameters - Update these with optimised values
        bmot_compression_time = 20 
        blue_mot_cooling_time = 70 
        broadband_red_mot_time = 10
        red_mot_compression_time = 12
        single_frequency_time = 35
        time_of_flight = 0 
        blue_mot_coil_1_voltage = 8.0
        blue_mot_coil_2_voltage = 7.9
        compressed_blue_mot_coil_1_voltage = 8.62
        compressed_blue_mot_coil_2_voltage = 8.39
        bmot_amp = 0.06
        compress_bmot_amp = 0.0035
        bb_rmot_coil_1_voltage = 5.24
        bb_rmot_coil_2_voltage = 5.22
        sf_rmot_coil_1_voltage = 5.12
        sf_rmot_coil_2_voltage = 5.11
        rmot_f_start = 80.6,
        rmot_f_end = 81,
        rmot_A_start = 0.03,
        rmot_A_end = 0.006,

        
        for j in range(int32(self.cycles)):        

            ####################################################### Blue MOT loading #############################################################

            delay(100*us)

            self.blue_mot_loading(
                 bmot_voltage_1 = blue_mot_coil_1_voltage,
                 bmot_voltage_2 = blue_mot_coil_2_voltage
            )

           
            self.red_mot_aom.set(frequency = 80.45 * MHz, amplitude = 0.08)
            self.red_mot_aom.sw.on()



            delay(self.blue_mot_loading_time* ms)

            ####################################################### Blue MOT compression & cooling ########################################################

            self.blue_mot_compression(                           #Here we are ramping up the blue MOT field and ramping down the blue power
                bmot_voltage_1 = blue_mot_coil_1_voltage,
                bmot_voltage_2 = blue_mot_coil_2_voltage,
                compress_bmot_volt_1 = compressed_blue_mot_coil_1_voltage,
                compress_bmot_volt_2 = compressed_blue_mot_coil_2_voltage,
                bmot_amp = bmot_amp,
                compress_bmot_amp = compress_bmot_amp,
                compression_time = bmot_compression_time
            )

            delay(bmot_compression_time*ms)    #Blue MOT compression time


            delay(blue_mot_cooling_time*ms)   #Allowing further cooling of the cloud by just holding the atoms here

            ########################################################### BB red MOT #################################################################

            self.broadband_red_mot(                                  #Switch to low field gradient for Red MOT, switches off the blue beams
                rmot_voltage_1= bb_rmot_coil_1_voltage,
                rmot_voltage_2 = bb_rmot_coil_2_voltage
            )

            delay(broadband_red_mot_time*ms)

            self.red_mot_aom.set(frequency = 80.55 *MHz, amplitude = 0.06)

            delay(5*ms)



            ########################################################### red MOT compression & Single Frequency ####################################################################


            self.red_mot_compression(                         #Compressing the red MOT by ramping down power, field ramping currently not active
                bb_rmot_volt_1 = bb_rmot_coil_1_voltage,
                bb_rmot_volt_2 = bb_rmot_coil_2_voltage,
                sf_rmot_volt_1 = sf_rmot_coil_1_voltage,
                sf_rmot_volt_2 = sf_rmot_coil_2_voltage,
                f_start = rmot_f_start,
                f_end = rmot_f_end,
                A_start = rmot_A_start,
                A_end = rmot_A_end,
                comp_time = red_mot_compression_time
            )

            delay(red_mot_compression_time*ms)

            delay(single_frequency_time*ms)

            self.red_mot_aom.sw.off()

            # self.seperate_probe(
            #     tof = 50,
            #     probe_duration = 1* ms ,
            #     probe_frequency= 205 * MHz
            # )

 

            #################################################################### Clock Spectroscopy ##################################################################################

            # delay(40*ms)
            self.clock_spectroscopy(
                aom_frequency = self.scan_frequency_values[j],
                pulse_time = self.rabi_pulse_duration_ms,
            )

            self.normalised_detection(j,self.excitation_fraction_list)
            
            delay(50*ms)

        self.excitation_fraction_list = self.excitation_fraction_list

        print(self.excitation_fraction_list)

        self.set_dataset("excitation_fraction_list", self.excitation_fraction_list, broadcast=True, archive=True)
        print(self.excitation_fraction_list[0:self.cycles])

        dataset = [self.scan_frequency_values,self.excitation_fraction_list,self.gs_list,self.es_list]


        self.set_dataset("Clock",dataset, broadcast=True, archive = True)

