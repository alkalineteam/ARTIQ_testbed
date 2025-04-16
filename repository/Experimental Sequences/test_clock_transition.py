from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64, int32, max
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

class test_clock_transition_scan(EnvExperiment):

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
    def red_modulation_on(self,f_SWAP_start,f_SWAP_end,T_SWAP,A_SWAP):          #state = 1 for modulation ON, 0 for modulation OFF

        self.red_mot_aom.set_att(0.0)

        cfr2 = (
            default_cfr2
            | (1 << 19) # enable digital ramp generator
            | (1 << 18) # enable no-dwell high functionality
            | (1 << 17) # enable no-dwell low functionality
        )
 
        f_step = (f_SWAP_end - f_SWAP_start) * 4*ns / T_SWAP

        #f_start_ftw = self.red_mot_aom.frequency_to_ftw(f_start)
        #A_start_mu = int32(round(A_start * 0x3fff)) << 16
        f_SWAP_start_ftw = self.red_mot_aom.frequency_to_ftw(f_SWAP_start)
        f_SWAP_end_ftw = self.red_mot_aom.frequency_to_ftw(f_SWAP_end)
        f_step_ftw = self.red_mot_aom.frequency_to_ftw((f_SWAP_end - f_SWAP_start) * 4*ns / T_SWAP)
        f_step_short_ftw = self.red_mot_aom.frequency_to_ftw(f_SWAP_end - f_SWAP_start)
        A_SWAP_mu = int32(round(A_SWAP * 0x3fff)) << 16


            # ----- Prepare for ramp -----
        # set profile parameters
        self.red_mot_aom.write64(
            ad9910._AD9910_REG_PROFILE7,
            A_SWAP_mu,
            f_SWAP_start_ftw
        )

        # set ramp limits
        self.red_mot_aom.write64(
            ad9910._AD9910_REG_RAMP_LIMIT,
            f_SWAP_end_ftw,
            f_SWAP_start_ftw,
        )

        # set time step
        self.red_mot_aom.write32(
            ad9910._AD9910_REG_RAMP_RATE,
            ((1 << 16) | (1 << 0))
        )

        # set frequency step
        self.red_mot_aom.write64(
            ad9910._AD9910_REG_RAMP_STEP,
            f_step_short_ftw,
            f_step_ftw
        )
        # set control register
        self.red_mot_aom.write32(ad9910._AD9910_REG_CFR2, cfr2)

        # safety delay, try decreasing if everything works
        delay(10*us)

        # start ramp
        self.red_mot_aom.cpld.io_update.pulse_mu(8)

    @kernel
    def red_modulation_off(self,f_SF,A_SF):                                      #Switch to single frequency

        f_SF_ftw = self.red_mot_aom.frequency_to_ftw(f_SF)
        A_SF_mu = int32(round(A_SF * 0x3fff)) << 16

                        # stop ramp
        # ----- Prepare for values after end of ramp -----
        self.red_mot_aom.write64(
            ad9910._AD9910_REG_PROFILE7,
            A_SF_mu,
            f_SF_ftw
        )

        # prepare control register for ramp end
        self.red_mot_aom.write32(ad9910._AD9910_REG_CFR2, default_cfr2)

        self.red_mot_aom.cpld.io_update.pulse_mu(8)

        # self.red_mot_aom.set_att(19*dB)

    @kernel
    def blue_mot_loading(self,bmot_voltage_1,bmot_voltage_2):   
        delay(100*us)

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

        delay(self.blue_mot_loading_time* ms)
    
    @kernel
    def blue_mot_compression(self,bmot_voltage_1,bmot_voltage_2,compress_bmot_volt_1,compress_bmot_volt_2,bmot_amp,compress_bmot_amp,compression_time,blue_mot_cooling_time):

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

        delay(bmot_compression_time*ms)    #Blue MOT compression time

        delay(blue_mot_cooling_time*ms)   #Allowing further cooling of the cloud by just holding the atoms here


    @kernel
    def broadband_red_mot(self,rmot_voltage_1,rmot_voltage_2,broadband_red_mot_time):      
            
             
            self.blue_mot_aom.set(frequency=90*MHz,amplitude=0.00)   
            self.blue_mot_aom.sw.off()                                   #Switch off blue beams
            self.repump_shutter_679.off()
            self.repump_shutter_707.off()
            self.blue_mot_shutter.off()

            self.mot_coil_1.write_dac(0, rmot_voltage_1)
            self.mot_coil_2.write_dac(1, rmot_voltage_2)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
     
            delay(broadband_red_mot_time*ms)
    @kernel
    def red_mot_compression(self,bb_rmot_volt_1,bb_rmot_volt_2,sf_rmot_volt_1,sf_rmot_volt_2,frequency,red_mot_compression_time):

        bb_rmot_amp=0.05
        compress_rmot_amp=0.008

        steps_com = red_mot_compression_time 
        t_com = red_mot_compression_time/steps_com
        volt_1_steps = (sf_rmot_volt_1 - bb_rmot_volt_1)/steps_com
        volt_2_steps = (sf_rmot_volt_2 - bb_rmot_volt_2)/steps_com

        amp_steps = (bb_rmot_amp-compress_rmot_amp)/steps_com
        

        for i in range(int64(steps_com)):
            voltage_1 = bb_rmot_volt_1 + ((i+1) * volt_1_steps)
            voltage_2 = bb_rmot_volt_2 + ((i+1) * volt_2_steps)
            amp = bb_rmot_amp - ((i+1) * amp_steps)

            self.mot_coil_1.write_dac(0, voltage_1)
            self.mot_coil_2.write_dac(1, voltage_2)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
                self.red_mot_aom.set(frequency = frequency * MHz, amplitude = amp)
            
            delay(t_com*ms)


        delay(red_mot_compression_time*ms)

        delay(single_frequency_time*ms)

        
        self.red_mot_aom.sw.off()

        
    @kernel 
    def seperate_probe(self,tof,probe_duration,probe_frequency):               #Only triggers the camera, and seperate probe
            with parallel:
                self.red_mot_aom.sw.off()
                self.blue_mot_aom.sw.off()
                self.repump_shutter_679.off()
                self.repump_shutter_707.off()
                self.probe_shutter.on()

            self.mot_coil_1.write_dac(0, 4.051)  
            self.mot_coil_2.write_dac(1, 4.088)
           
            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()

            delay(((tof +3.9)*ms))

            with parallel:
                    self.camera_trigger.pulse(1*ms)
                    self.probe_aom.set(frequency=probe_frequency, amplitude=0.17)
                    self.probe_aom.sw.on()
                    
            delay(probe_duration)
                    
            with parallel:
                self.probe_shutter.off()
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
        print(current_per_coil)
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

        delay(60*ms)  #wait for coils to switch

        #rabi spectroscopy pulse
        self.stepping_aom.set(frequency = aom_frequency * Hz)
        self.stepping_aom.sw.on()
        delay(pulse_time*ms)
        self.stepping_aom.sw.off()
        self.stepping_aom.set(frequency = 0 * Hz)
        self.stepping_aom.sw.off()
   
    @rpc
    def excitation_fraction(self,data,j,excitation_fraction_list):                                    #Calulates the excitation fraction from the sampler data and writes it to list for analysis later

        atom_scalar = 10000    #Scalar value to convert from Volts to Atom No, needs calibrating often

        background = numpy.max(numpy.array(data[0:200]))
        ground_state = ((numpy.max(numpy.array(data[500:700])) )- background ) * atom_scalar
        excited_state = ((numpy.max(numpy.array(data[900:1100]))) - background) *atom_scalar

        excitation_fraction = excited_state / (ground_state + excited_state) 
        print(excitation_fraction)

        excitation_fraction_list[j] = excitation_fraction

     

    @kernel
    def normalised_detection(self):        #This function should be sampling from the PMT at the same time as the camera being triggered for seperate probe
        self.core.break_realtime()
        sample_period = 1 / 20000      #10kHz sampling rate should give us enough data points
        sampling_duration = 0.06      #30ms sampling time to allow for all the imaging slices to take place

        num_samples = int32(sampling_duration/sample_period)
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

                delay(3.9*ms)     #wait for shutter to open

                with parallel:
                    self.camera_trigger.pulse(1*ms)
                    self.probe_aom.set(frequency=200 * MHz, amplitude=0.17)
                    self.probe_aom.sw.on()

                delay(0.8* ms)      #Ground state probe duration            
                
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
                delay(3.9*ms) 

                self.probe_aom.sw.on()
                delay(0.8*ms)            #Ground state probe duration
                self.probe_aom.sw.off()

                delay(20*ms)
                #  ########################Background############################
 
                self.probe_aom.sw.on()
                delay(0.8*ms)            #Ground state probe duration
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
        delay(50*ms)


       
    @rpc
    def sequence(self):
      
       #Setup frequency scan parameters
        scan_start = int32(self.scan_center_frequency_Hz - (self.scan_range_Hz/2))
        scan_end =int32(self.scan_center_frequency_Hz + (self.scan_range_Hz/2))
        scan_frequency_values = [x for x in range(scan_start, scan_end, int32(self.scan_step_size_Hz))]
        cycles = len(scan_frequency_values)

        excitation_fraction_list = [0.0] * cycles


        #Sequence Parameters - Update these with optimised values
        bmot_compression_time = 20 
        blue_mot_cooling_time = 60 
        broadband_red_mot_time = 15
        red_mot_compression_time = 10
        single_frequency_time = 15
        time_of_flight = 0 
        blue_mot_coil_1_voltage = 8.0
        blue_mot_coil_2_voltage = 7.82
        compressed_blue_mot_coil_1_voltage = 8.55
        compressed_blue_mot_coil_2_voltage = 8.34
        bmot_amp = 0.06
        compress_bmot_amp = 0.0035
        bb_rmot_coil_1_voltage = 5.3
        bb_rmot_coil_2_voltage = 5.28
        sf_rmot_coil_1_voltage = 5.7
        sf_rmot_coil_2_voltage = 5.66
        sf_frequency = 80.92 

        
        for j in range(int32(cycles)):        

            self.blue_mot_loading(
                 bmot_voltage_1 = blue_mot_coil_1_voltage,
                 bmot_voltage_2 = blue_mot_coil_2_voltage
            )

            self.red_modulation_on(
                f_SWAP_start = 80 * MHz,   #Ramp lower limit
                f_SWAP_end = 81 * MHz,     #Ramp upper limit
                T_SWAP = 40 * us,          #Time spent on each step, 40us is equivalent to 25kHz modulation rate
                A_SWAP = 0.06,             #Amplitude during modulation
            )
   

            self.blue_mot_compression(                           #Here we are ramping up the blue MOT field and ramping down the blue power
                bmot_voltage_1 = blue_mot_coil_1_voltage,
                bmot_voltage_2 = blue_mot_coil_2_voltage,
                compress_bmot_volt_1 = compressed_blue_mot_coil_1_voltage,
                compress_bmot_volt_2 = compressed_blue_mot_coil_2_voltage,
                bmot_amp = bmot_amp,
                compress_bmot_amp = compress_bmot_amp,
                compression_time = bmot_compression_time,
                blue_mot_cooling_time = blue_mot_cooling_time
            )

            


            self.broadband_red_mot(                                  #Switch to low field gradient for Red MOT, switches off the blue beams
                rmot_voltage_1= bb_rmot_coil_1_voltage,
                rmot_voltage_2 = bb_rmot_coil_2_voltage,
                broadband_red_mot_time = broadband_red_mot_time
            )



            self.red_modulation_off(                   #switch to single frequency
                f_SF = sf_frequency * MHz,
                A_SF = 0.04
            )

            self.red_mot_compression(                         #Compressing the red MOT by ramping down power, field ramping currently not active
                bb_rmot_volt_1 = bb_rmot_coil_1_voltage,
                bb_rmot_volt_2 = bb_rmot_coil_2_voltage,
                sf_rmot_volt_1 = sf_rmot_coil_1_voltage,
                sf_rmot_volt_2 = sf_rmot_coil_2_voltage,
                frequency = sf_frequency,
                red_mot_compression_time=red_mot_compression_time,
                single_frequency_time = single_frequency_time 
            )


            # delay(40*ms)
            self.clock_spectroscopy(
                aom_frequency = scan_frequency_values[j],
                pulse_time = self.rabi_pulse_duration_ms
            )

            self.normalised_detection()
            









    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.initialise_modules()

        self.sequence()
        
            
            
        


