from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64, int32
import numpy as np
from artiq.coredevice import ad9910

default_cfr1 = (
    (1 << 1)    # configures the serial data I/O pin (SDIO) as an input only pin; 3-wire serial programming mode
)
default_cfr2 = (
    (1 << 5)    # forces the SYNC_SMP_ERR pin to a Logic 0; this pin indicates (active high) detection of a synchronization pulse sampling error
    | (1 << 16) # a serial I/O port read operation of the frequency tuning word register reports the actual 32-bit word appearing at the input to the DDS phase accumulator (i.e. not the contents of the frequency tuning word register)
    | (1 << 24) # the amplitude is scaled by the ASF from the active profile (without this, the DDS outputs max. possible amplitude -> cracked AOM crystals)
)

class atom_servo(EnvExperiment):

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
        
        self.setattr_argument("scan_center_frequency_Hz", NumberValue(default=85000000 * Hz))
        self.setattr_argument("scan_range_Hz", NumberValue(default=500000 * Hz))
        self.setattr_argument("scan_step_size_Hz", NumberValue(default=1000 * Hz))
        self.setattr_argument("rabi_pulse_duration_ms", NumberValue(default= 60 * ms))
        self.setattr_argument("clock_intensity", NumberValue(default=0.05))
        self.setattr_argument("bias_field_current", NumberValue(default=3.0))
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
            # voltage_1 = bb_rmot_volt_1 + ((i+1) * volt_1_steps)
            # voltage_2 = bb_rmot_volt_2 + ((i+1) * volt_2_steps)
            amp = bb_rmot_amp - ((i+1) * amp_steps)

            # self.mot_coil_1.write_dac(0, voltage_1)
            # self.mot_coil_2.write_dac(1, voltage_2)

            with parallel:
                # self.mot_coil_1.load()
                # self.mot_coil_2.load()
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
    def clock_spectroscopy(self,aom_frequency,pulse_time,I,B):
         
         #Switch to Helmholtz
        self.mot_coil_1.write_dac(0, 5.0 - B)  
        self.mot_coil_2.write_dac(1, 5.0 + B)
        
        with parallel:
            self.mot_coil_1.load()
            self.mot_coil_2.load()

        self.pmt_shutter.on()
        self.camera_shutter.on()
        self.clock_shutter.on()    

        delay(20*ms)  #wait for coils to switch

        #rabi spectroscopy pulse
        self.stepping_aom.set(frequency = aom_frequency * Hz, amplitude = I)
        delay(pulse_time*ms)
        self.stepping_aom.set(frequency = 0 * Hz, amplitude = I)



    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.initialise_modules()

        #Setup frequency scan parameters

        scan_start = self.scan_center_frequency - (self.scan_range/2)
        scan_end = self.scan_center_frequency - (self.scan_range/2)
        scan_frequency_values = np.arange(scan_start,scan_end,self.scan_step_size)


        #Sequence Parameters - Update these with optimised values

        bmot_compression_time = 20 
        blue_mot_cooling_time = 60 
        broadband_red_mot_time = 15
        red_mot_compression_time = 10
        single_frequency_time = 15
        time_of_flight = 0 
        
        blue_mot_coil_1_voltage = 8.0
        blue_mot_coil_2_voltage = 7.9
        compressed_blue_mot_coil_1_voltage = 8.55
        compressed_blue_mot_coil_2_voltage = 8.48
        bmot_amp = 0.06
        compress_bmot_amp = 0.0035


        bb_rmot_coil_1_voltage = 5.3
        bb_rmot_coil_2_voltage = 5.25
        sf_rmot_coil_1_voltage = 5.8
        sf_rmot_coil_2_voltage = 5.75

        sf_frequency = 80.92    


        for j in range(int(scan_frequency_values)):          #first we need to scan across the clock transition to acquire the lock

            delay(100*us)

            self.blue_mot_loading(
                 bmot_voltage_1 = blue_mot_coil_1_voltage,
                 bmot_voltage_2 = blue_mot_coil_2_voltage
            )

            self.red_modulation_on(
                f_start = 80 * MHz,        #Starting frequency of the ramp
                A_start = 0.06,            #initial amplitude of the ramp
                f_SWAP_start = 80 * MHz,   #Ramp lower limit
                f_SWAP_end = 81 * MHz,     #Ramp upper limit
                T_SWAP = 40 * us,          #Time spent on each step, 40us is equivalent to 25kHz modulation rate
                A_SWAP = 0.06,             #Amplitude during modulation
            )

            delay(self.blue_mot_loading_time* ms)

            self.blue_mot_compression(                           #Here we are ramping up the blue MOT field and ramping down the blue power
                bmot_voltage_1 = blue_mot_coil_1_voltage,
                bmot_voltage_2 = blue_mot_coil_2_voltage,
                compress_bmot_volt_1 = compressed_blue_mot_coil_1_voltage,
                compress_bmot_volt_2 = compressed_blue_mot_coil_2_voltage,
                bmot_amp = bmot_amp,
                compress_bmot_amp = compress_bmot_amp
                compression_time = bmot_compression_time
            )

            delay(bmot_compression_time*ms)    #Blue MOT compression time

            delay(blue_mot_cooling_time*ms)   #Allowing further cooling of the cloud by just holding the atoms here

            self.broadband_red_mot(                                  #Switch to low field gradient for Red MOT, switches off the blue beams
                rmot_voltage_1= bb_rmot_coil_1_voltage,
                rmot_voltage_2 = bb_rmot_coil_2_voltage
            )

            delay(broadband_red_mot_time*ms)

            self.red_modulation_off(                   #switch to single frequency
                f_SF = sf_frequency * MHz,
                A_SF = 0.04
            )

            self.red_mot_compression(                         #Compressing the red MOT by ramping down power, field ramping currently not active
                bb_rmot_volt_1 = bb_rmot_coil_1_voltage,
                bb_rmot_volt_2 = bb_rmot_coil_2_voltage,
                sf_rmot_volt_1 = sf_rmot_coil_1_voltage,
                sf_rmot_volt_2 = sf_rmot_coil_2_voltage,
                frequency = sf_frequency
            )

            delay(red_mot_compression_time*ms)

            delay(single_frequency_time*ms)
            

            self.clock_spectroscopy(
                frequency = scan_frequency_values[j]
                pulse_time = self.rabi_pulse_duration
                I = self.clock_intensity
                B = self.bias_field_current

            )

            self.seperate_probe(
                tof = time_of_flight,
                probe_duration = 0.2 * ms,
                probe_frequency= 200 * MHz
            )




            delay(10*ms)




                        #process the 3 pulses
            ground_state = data[:,0] - data[:,3]
            excited_state = data[:,1] - data[:,3]
                    
            excitation_fraction = excited_state / (ground_state + excited_state)
            excitation_fractions[i] = excitation_fraction
                
                #Should read PMT signal from here
        plt.plot(frequency_scan_values, excitation_fractions)        #plot of all the excitation fractions
        resonance_peak_frequency = np.argmax(excitation_fractions)
        print("Clock transition frequency found at: " + resonance_peak_frequency)      
                
                
        if self.lock_to_transition == False:  
            break
        else: 
                """Generate the Thue-Morse sequence up to index n."""
            n = 2628288                                                # How many seconds there are in a month
            thue_morse = [0]
            while len(thue_morse) <= n:
                thue_morse += [1 - bit for bit in thue_morse] 
            clock_frequency = resonance_peak_frequency
            feedback_aom = 
            while 1:
                
                if thue_morse == 0:
                    f_low = resonance_peak_frequency - (self.rabi_linewidth/2)
                    ex_fraction_low = clock_spectroscopy(f_low)                   #Run Clock spectroscopy sequence at this frequency
                         
                    
                else if thue_morse == 1:
                    f_high = resonance_peak_frequency + (self.rabi_linewidth/2)
                    ex_fraction_high = clock_spectroscopy.run(f_high)    #Run 1 experimental cycle with this as the clock frquency
                    #Run Clock spectroscopy sequence on high-side
                
                
                if count % 2 == 0:              # Every other cycle generate correction
                    #Calculate error signal and then make correction
                    error_signal = ex_fraction_high - ex_fraction_low
                    
                    frequency_correction = (self.gain_1/(0.8*self.contrast*self.rabi_pulse_duration)) * error_signal   # This is the first servo loop
                    feedback_aom += frequency_correction
                    atom_lock_aom.set(frequency= )
                    
                    
                    #write to text file
                    
                count =+ 1
            
            #Setup thue-morse sequence with very large number of values so we run indefinitely
            #step to one side of the transistion, perfom spectroscopy.
            
            
                
#To get the actual lock,                 
                
                
          
            
            



    
