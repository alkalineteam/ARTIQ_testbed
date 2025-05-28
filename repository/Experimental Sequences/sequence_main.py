from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64, int32
from artiq.coredevice import ad9910
from artiq.coredevice.sampler import Sampler
import numpy as np


class sequence_main(EnvExperiment):

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
        self.camera_shutter:TTLOut=self.get_device("ttl11")   

        # self.pmt_shutter:TTLOut=self.get_device("ttl10")
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
        self.setattr_argument("red_mot_compression_time", NumberValue(default=5))
        self.setattr_argument("single_frequency_time", NumberValue(default=25))
        self.setattr_argument("time_of_flight", NumberValue(default=40))

        self.setattr_argument("blue_mot_coil_1_voltage", NumberValue(default=8.0))
        self.setattr_argument("blue_mot_coil_2_voltage", NumberValue(default=7.9))
        self.setattr_argument("compressed_blue_mot_coil_1_voltage", NumberValue(default=8.62))
        self.setattr_argument("compressed_blue_mot_coil_2_voltage", NumberValue(default=8.39))
        self.setattr_argument("bb_rmot_coil_1_voltage", NumberValue(default=5.24))
        self.setattr_argument("bb_rmot_coil_2_voltage", NumberValue(default=5.22))
        self.setattr_argument("sf_rmot_coil_1_voltage", NumberValue(default=5.72))
        self.setattr_argument("sf_rmot_coil_2_voltage", NumberValue(default=5.64))
        self.setattr_argument("sf_frequency", NumberValue(default=80.92))



    @kernel
    def initialise_modules(self):
            
        delay(1000*ms)

        # Initialize the modules
        self.camera_shutter.output()
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
        self.stepping_aom.cpld.init()
        self.stepping_aom.init()

        self.sampler.init() 

        # Set the RF channels ON
        self.stepping_aom.set(frequency = 85.5* MHz)
        self.stepping_aom.set_att(16*dB)
        self.blue_mot_aom.sw.on()
        self.zeeman_slower_aom.sw.on()
        self.stepping_aom.sw.on()
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
    def blue_mot_compression(self,bmot_voltage_1,bmot_voltage_2,compress_bmot_volt_1,compress_bmot_volt_2,bmot_amp,compress_bmot_amp):

        self.zeeman_slower_aom.set(frequency=70 * MHz, amplitude=0.00)   #Turn off the Zeeman Slower
        self.zeeman_slower_shutter.off()
        self.red_mot_aom.sw.on()
        delay(4.0*ms)                                                 #wait for shutter to close

        steps_com = self.blue_mot_compression_time 
        t_com = self.blue_mot_compression_time/steps_com
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
            delay(self.broadband_red_mot_time*ms)

    @kernel
    def red_mot_compression(self,bb_rmot_volt_1,bb_rmot_volt_2,sf_rmot_volt_1,sf_rmot_volt_2,f_start,f_end,A_start,A_end):


        start_freq = f_start
        end_freq = f_end


        bb_rmot_amp = A_start
        compress_rmot_amp= A_end

        comp_time = self.red_mot_compression_time
        step_duration = 0.05
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
                    self.probe_aom.set(frequency=probe_frequency, amplitude=0.18)
                    self.probe_aom.sw.on()
                    
            delay(probe_duration)
                    
            with parallel:
                self.probe_shutter.off()
                self.camera_shutter.off()    #Camera shutter takes 26ms to open so we will open it here
                self.probe_aom.set(frequency=probe_frequency, amplitude=0.00)
                self.probe_aom.sw.off()

            delay(10*ms)

    @kernel 
    def MOT_probe(self,tof,probe_duration,probe_frequency):
            with parallel:
                self.red_mot_aom.sw.off()
                self.blue_mot_aom.sw.off()
                self.blue_mot_shutter.on()
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
                    self.blue_mot_aom.set(frequency=90*MHz, amplitude=0.06)
                    self.blue_mot_aom.sw.on()
                    
            delay(probe_duration)
                    
            with parallel:
                self.probe_shutter.off()
                self.camera_shutter.off()    #Camera shutter takes 26ms to open so we will open it here
                self.blue_mot_aom.set(frequency=90*MHz, amplitude=0.00)
                self.blue_mot_aom.sw.off()

            delay(10*ms)



    @kernel
    def clock_spectroscopy(self,aom_frequency,pulse_time,B):
         


        # self.pmt_shutter.on()
        # self.camera_shutter.on()
        self.clock_shutter.on()    

        delay(40*ms)  #wait for coils to switch

        #rabi spectroscopy pulse
        self.stepping_aom.set(frequency = aom_frequency * Hz)
        delay(pulse_time*ms)
        self.stepping_aom.set(frequency = 0 * Hz)



    @kernel
    def pmt_capture(self,sampling_duration,sampling_rate,tof):        #This function should be sampling from the PMT at the same time as the camera being triggered for seperate probe
        # self.core.break_realtime()
        sample_period = 1 / sampling_rate
        num_samples = int32(sampling_duration/sample_period)
        print(num_samples)
        samples = [[0.0 for i in range(8)] for i in range(num_samples)]
    
        with parallel:
            with sequential:
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

                delay(((tof + 3.9)*ms))

                with parallel:
                    self.camera_trigger.pulse(1*ms)
                    self.probe_aom.set(frequency=200 * MHz, amplitude=0.17)
                    self.probe_aom.sw.on()
    
                delay(3 * ms)
                    
                with parallel:
                    self.probe_shutter.off()
                    self.camera_shutter.off()    #Camera shutter takes 26ms to open so we will open it here
                    self.probe_aom.set(frequency=0*MHz, amplitude=0.00)
                    self.probe_aom.sw.off()

            with sequential:
                for j in range(num_samples):
                    self.sampler.sample(samples[j])
                    delay(sample_period*s)

        delay(sampling_duration*ms)

         
        samples_ch0 = [i[0] for i in samples]
        print(samples_ch0)
        self.set_dataset("samples", samples_ch0, broadcast=True, archive=True)


    @kernel
    def normalised_detection(self,j,excitation_fraction_list):        #This function should be sampling from the PMT at the same time as the camera being triggered for seperate probe
        self.core.break_realtime()
        sample_period = 1 / 40000      #10kHz sampling rate should give us enough data points
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

                delay(4.1*ms)     #wait for shutter to open

                with parallel:
                    self.camera_trigger.pulse(1*ms)
                    self.probe_aom.set(frequency=205 * MHz, amplitude=0.18)
                    self.probe_aom.sw.on()

                delay(2* ms)      #Ground state probe duration            
                
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
                self.probe_shutter.off()
                delay(10*ms)
                self.probe_shutter.on()
                delay(4.1*ms)


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

        # print(self.excitation_fraction(samples_ch0))
                                 

        gs = samples_ch0[0:200]
        es = samples_ch0[500:700]
        bg = samples_ch0[900:1100]

        gs_max = gs[0]
        es_max = es[0]
        bg_max = bg[0]

        # Loop through the rest of the list

        with parallel:
            for num in gs[1:]:
                if num > gs_max:
                    gs_max = num

            for num in es[1:]:
                if num > es_max:
                    es_max = num

            for num in bg[1:]:
                if num > bg_max:
                    bg_max = num
        
        # excitation_fraction = (es_max - bg_max) / ((gs_max-bg_max) + (es_max-bg_max)) 
        self.gs_list[j] = float(gs_max)
        self.es_list[j] = float(es_max)
        self.excitation_fraction_list[j] = float(j)
        # # print(excitation_fraction)
        # # ef.append(self.excitation_fraction_list)



    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.initialise_modules()

        for j in range(int(self.cycles)):          #This runs the actual sequence
            delay(100*us)


            self.blue_mot_loading(
                 bmot_voltage_1 = self.blue_mot_coil_1_voltage,
                 bmot_voltage_2 = self.blue_mot_coil_2_voltage
            )


            self.red_mot_aom.set(frequency = 80.45 *MHz, amplitude = 0.08)
            self.red_mot_aom.sw.on()


            delay((self.blue_mot_loading_time )* ms)



            self.blue_mot_compression(                           #Here we are ramping up the blue MOT field and ramping down the blue power
                bmot_voltage_1 = self.blue_mot_coil_1_voltage,
                bmot_voltage_2 = self.blue_mot_coil_2_voltage,
                compress_bmot_volt_1 = self.compressed_blue_mot_coil_1_voltage,
                compress_bmot_volt_2 = self.compressed_blue_mot_coil_2_voltage,
                bmot_amp = 0.06,
                compress_bmot_amp = 0.0035
            )

            delay(self.blue_mot_compression_time*ms)


            delay(self.blue_mot_cooling_time*ms)   #Allowing further cooling of the cloud by just holding the atoms here



            self.broadband_red_mot(                                  #Switch to low field gradient for Red MOT, switches off the blue beams
                rmot_voltage_1= self.bb_rmot_coil_1_voltage,
                rmot_voltage_2 = self.bb_rmot_coil_2_voltage
            )

            delay(self.broadband_red_mot_time*ms)

            self.red_mot_aom.set(frequency = 80.55 *MHz, amplitude = 0.06)

            delay(5*ms)

            self.red_mot_compression(                         #Compressing the red MOT by ramping down power, field ramping currently not active
                bb_rmot_volt_1 = self.bb_rmot_coil_1_voltage,
                bb_rmot_volt_2 = self.bb_rmot_coil_2_voltage,
                sf_rmot_volt_1 = self.sf_rmot_coil_1_voltage,
                sf_rmot_volt_2 = self.sf_rmot_coil_2_voltage,
                f_start = 80.6,
                f_end = 81,
                A_start = 0.03,
                A_end = 0.007
            )


            delay(self.red_mot_compression_time*ms)

    

            delay(self.single_frequency_time*ms)


            self.seperate_probe(
                tof = self.time_of_flight,
                probe_duration = 0.5* ms ,
                probe_frequency= 205 * MHz
            )


 

            self.red_mot_aom.sw.off()





            #          #Switch to Helmholtz
            # self.mot_coil_1.write_dac(0, 2.0)  
            # self.mot_coil_2.write_dac(1, 8.0)
        
            # with parallel:
            #     self.mot_coil_1.load()
            #     self.mot_coil_2.load()

            # delay(50*ms)

            
            # self.seperate_probe(
            #     tof = self.time_of_flight,
            #     probe_duration = 0.2*ms ,
            #     probe_frequency= 200 * MHz
            # )


            # self.pmt_capture(
            #     sampling_duration = 0.2,
            #     sampling_rate= 10000,
            #     tof =self.time_of_flight
            # )

            # self.normalised_detection()
            

            delay(50*ms)




            



    
