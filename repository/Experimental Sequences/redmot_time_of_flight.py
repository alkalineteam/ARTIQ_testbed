from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64, int32
from artiq.coredevice import ad9910

default_cfr1 = (
    (1 << 1)    # configures the serial data I/O pin (SDIO) as an input only pin; 3-wire serial programming mode
)
default_cfr2 = (
    (1 << 5)    # forces the SYNC_SMP_ERR pin to a Logic 0; this pin indicates (active high) detection of a synchronization pulse sampling error
    | (1 << 16) # a serial I/O port read operation of the frequency tuning word register reports the actual 32-bit word appearing at the input to the DDS phase accumulator (i.e. not the contents of the frequency tuning word register)
    | (1 << 24) # the amplitude is scaled by the ASF from the active profile (without this, the DDS outputs max. possible amplitude -> cracked AOM crystals)
)

class redmot_time_of_flight(EnvExperiment):
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
        self.setattr_argument("broadband_red_mot_time", NumberValue(default=15))
        self.setattr_argument("red_mot_compression_time", NumberValue(default=10))
        self.setattr_argument("single_frequency_time", NumberValue(default=20))
        self.setattr_argument("time_of_flight", NumberValue(default=30))

        self.setattr_argument("blue_mot_coil_1_voltage", NumberValue(default=8.0))
        self.setattr_argument("blue_mot_coil_2_voltage", NumberValue(default=7.82))
        self.setattr_argument("compressed_blue_mot_coil_1_voltage", NumberValue(default=8.55))
        self.setattr_argument("compressed_blue_mot_coil_2_voltage", NumberValue(default=8.34))
        self.setattr_argument("bb_rmot_coil_1_voltage", NumberValue(default=5.3))
        self.setattr_argument("bb_rmot_coil_2_voltage", NumberValue(default=5.28))
        self.setattr_argument("sf_rmot_coil_1_voltage", NumberValue(default=5.7))
        self.setattr_argument("sf_rmot_coil_2_voltage", NumberValue(default=5.66))
        self.setattr_argument("sf_frequency", NumberValue(default=80.92))
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
    def red_modulation_on(self,f_start,A_start,f_SWAP_start,f_SWAP_end,T_SWAP,A_SWAP,f_SF,A_SF):          #state = 1 for modulation ON, 0 for modulation OFF

        self.red_mot_aom.set_att(0.0)

        cfr2 = (
            default_cfr2
            | (1 << 19) # enable digital ramp generator
            | (1 << 18) # enable no-dwell high functionality
            | (1 << 17) # enable no-dwell low functionality
        )
 
        f_step = (f_SWAP_end - f_SWAP_start) * 4*ns / T_SWAP

        f_start_ftw = self.red_mot_aom.frequency_to_ftw(f_start)
        A_start_mu = int32(round(A_start * 0x3fff)) << 16
        f_SWAP_start_ftw = self.red_mot_aom.frequency_to_ftw(f_SWAP_start)
        f_SWAP_end_ftw = self.red_mot_aom.frequency_to_ftw(f_SWAP_end)
        f_step_ftw = self.red_mot_aom.frequency_to_ftw((f_SWAP_end - f_SWAP_start) * 4*ns / T_SWAP)
        f_step_short_ftw = self.red_mot_aom.frequency_to_ftw(f_SWAP_end - f_SWAP_start)
        A_SWAP_mu = int32(round(A_SWAP * 0x3fff)) << 16
        f_SF_ftw = self.red_mot_aom.frequency_to_ftw(f_SF)
        A_SF_mu = int32(round(A_SF * 0x3fff)) << 16

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

        self.red_mot_aom.sw.on()


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

        bb_rmot_amp=0.03
        compress_rmot_amp=0.0003

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
                self.camera_trigger.pulse(2*ms)
                self.probe_aom.set(frequency=probe_frequency, amplitude=0.14)
                self.probe_aom.sw.on()
                
        delay(probe_duration)
                
        with parallel:
            self.probe_shutter.off()

            self.probe_aom.set(frequency=probe_frequency, amplitude=0.00)
            self.probe_aom.sw.off()

        delay(10*ms)



    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        self.initialise_modules()

        
             
        j=0

        for j in range(int(self.cycles)):          #This runs the actual sequence

            if j < 5:
                    
                delay(100*us)

                self.red_mot_aom.sw.off()
                self.blue_mot_loading(
                    bmot_voltage_1 = 5.0,
                    bmot_voltage_2 = 5.0
                )

                delay(self.blue_mot_loading_time* ms)

   
                self.red_modulation_on(
                    f_start = 80 * MHz,
                    A_start = 0.06,
                    f_SWAP_start = 80 * MHz,
                    f_SWAP_end = 81 * MHz,
                    T_SWAP = 40 * us,
                    A_SWAP = 0.03,
                    f_SF = 80.92 * MHz,
                    A_SF = 0.05
                )

                self.blue_mot_compression(
                    bmot_voltage_1 = 5.0,
                    bmot_voltage_2 = 5.0,
                    compress_bmot_volt_1 = 5.0,
                    compress_bmot_volt_2 = 5.0,
                    bmot_amp = 0.06,
                    compress_bmot_amp = 0.003
                )

                delay(self.blue_mot_compression_time*ms)


                delay(self.blue_mot_cooling_time*ms)   #Allowing further cooling of the cloud


                self.broadband_red_mot(
                    rmot_voltage_1= self.bb_rmot_coil_1_voltage,
                    rmot_voltage_2 = self.bb_rmot_coil_2_voltage
                )

                delay(self.broadband_red_mot_time*ms)
            

                self.red_modulation_off(                   #switch to single frequency
                    f_SF = self.sf_frequency * MHz,
                    A_SF = 0.03
                )

                self.red_mot_compression(                         #Compressing the red MOT by ramping down power, field ramping currently not active
                    bb_rmot_volt_1 = self.bb_rmot_coil_1_voltage,
                    bb_rmot_volt_2 = self.bb_rmot_coil_2_voltage,
                    sf_rmot_volt_1 = self.sf_rmot_coil_1_voltage,
                    sf_rmot_volt_2 = self.sf_rmot_coil_2_voltage,
                    frequency= self.sf_frequency
                )

                delay(self.red_mot_compression_time*ms)




                delay(self.single_frequency_time*ms)

                self.red_mot_aom.sw.off()


                self.seperate_probe(
                    tof = self.time_of_flight,
                    probe_duration = 0.2 * ms,
                    probe_frequency= 200 * MHz
                )



                delay(100*ms)

            else:




            

                delay(100*us)

                self.blue_mot_loading(
                    bmot_voltage_1 = self.blue_mot_coil_1_voltage,
                    bmot_voltage_2 = self.blue_mot_coil_2_voltage
                )

                self.red_modulation_on(
                    f_start = 80 * MHz,
                    A_start = 0.06,
                    f_SWAP_start = 80 * MHz,
                    f_SWAP_end = 81 * MHz,
                    T_SWAP = 40 * us,
                    A_SWAP = 0.03,
                    f_SF = 80.92 * MHz,
                    A_SF = 0.03
                )



                delay(self.blue_mot_loading_time* ms)




                self.blue_mot_compression(
                    bmot_voltage_1 = self.blue_mot_coil_1_voltage,
                    bmot_voltage_2 = self.blue_mot_coil_2_voltage,
                    compress_bmot_volt_1 =self.compressed_blue_mot_coil_1_voltage,
                    compress_bmot_volt_2 = self.compressed_blue_mot_coil_2_voltage,
                    bmot_amp = 0.06,
                    compress_bmot_amp = 0.003
                )



                delay(self.blue_mot_compression_time*ms)


                delay(self.blue_mot_cooling_time*ms)   #Allowing further cooling of the cloud

 

                self.broadband_red_mot(
                    rmot_voltage_1= self.bb_rmot_coil_1_voltage,
                    rmot_voltage_2 = self.bb_rmot_coil_2_voltage
                )

                delay(self.broadband_red_mot_time*ms)
            

                self.red_modulation_off(                   #switch to single frequency
                    f_SF = self.sf_frequency * MHz,
                    A_SF = 0.03
                )


                self.red_mot_compression(                         #Compressing the red MOT by ramping down power, field ramping currently not active
                    bb_rmot_volt_1 = self.bb_rmot_coil_1_voltage,
                    bb_rmot_volt_2 = self.bb_rmot_coil_2_voltage,
                    sf_rmot_volt_1 = self.sf_rmot_coil_1_voltage,
                    sf_rmot_volt_2 = self.sf_rmot_coil_2_voltage,
                    frequency= self.sf_frequency
                )

                delay(self.red_mot_compression_time*ms)

          
                delay(self.single_frequency_time*ms)


                self.seperate_probe(
                    tof = self.time_of_flight,
                    probe_duration = 0.5 * ms,
                    probe_frequency= 205 * MHz
                )




                delay(200*ms)


            



    
