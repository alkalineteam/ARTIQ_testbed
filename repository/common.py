from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64, int32
from artiq.coredevice import ad9910
from artiq.coredevice.sampler import Sampler
import numpy as np

default_cfr1 = (
    (1 << 1)    # configures the serial data I/O pin (SDIO) as an input only pin; 3-wire serial programming mode
)
default_cfr2 = (
    (1 << 5)    # forces the SYNC_SMP_ERR pin to a Logic 0; this pin indicates (active high) detection of a synchronization pulse sampling error
    | (1 << 16) # a serial I/O port read operation of the frequency tuning word register reports the actual 32-bit word appearing at the input to the DDS phase accumulator (i.e. not the contents of the frequency tuning word register)
    | (1 << 24) # the amplitude is scaled by the ASF from the active profile (without this, the DDS outputs max. possible amplitude -> cracked AOM crystals)
)

class sr1():
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

        self.sampler.init() 

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
    def red_modulation_on(self,f_start,A_start,f_SWAP_start,f_SWAP_end,T_SWAP,A_SWAP):          #state = 1 for modulation ON, 0 for modulation OFF

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
    def red_modulation_off(self,f_SF,A_SF):

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

            self.mot_coil_1.write_dac(0, rmot_voltage_1)
            self.mot_coil_2.write_dac(1, rmot_voltage_2)

            with parallel:
                self.mot_coil_1.load()
                self.mot_coil_2.load()
            delay(self.broadband_red_mot_time*ms)

    @kernel
    def red_mot_compression(self,bb_rmot_volt_1,bb_rmot_volt_2,sf_rmot_volt_1,sf_rmot_volt_2,frequency):

        bb_rmot_amp=0.05
        compress_rmot_amp=0.009

        steps_com = self.red_mot_compression_time 
        t_com = self.red_mot_compression_time/steps_com
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

    @kernel
    def mot_as_probe(self,probe_duration):
         
        self.red_mot_aom.sw.off()
        self.blue_mot_aom.sw.off()

        self.repump_shutter_679.off()
        self.repump_shutter_707.off()

        self.mot_coil_1.write_dac(0, 4.051)
        self.mot_coil_2.write_dac(1, 4.088)

        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()

        delay(4*ms)

        with parallel:
                self.camera_trigger.pulse(1*ms)
                self.blue_mot_aom.set(frequency=90 * MHz, amplitude=0.06)
                self.blue_mot_aom.sw.on()
                
        delay(probe_duration)

        self.blue_mot_aom.sw.off()

        #set coil field to zero
        #wait for probe shutter to open

        delay(10*ms)
         
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
                    self.camera_trigger.pulse(1*ms)
                    self.probe_aom.set(frequency=probe_frequency, amplitude=0.17)
                    self.probe_aom.sw.on()
                    
            delay(probe_duration * ms)
                    
            with parallel:
                self.probe_shutter.off()
                self.camera_shutter.off()    #Camera shutter takes 26ms to open so we will open it here
                self.probe_aom.set(frequency=probe_frequency, amplitude=0.00)
                self.probe_aom.sw.off()

            delay(10*ms)

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
