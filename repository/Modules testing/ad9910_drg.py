from artiq.experiment import *
from artiq.coredevice import ad9910
from numpy import int32


default_cfr1 = (
    (1 << 1)    # configures the serial data I/O pin (SDIO) as an input only pin; 3-wire serial programming mode
)
default_cfr2 = (
    (1 << 5)    # forces the SYNC_SMP_ERR pin to a Logic 0; this pin indicates (active high) detection of a synchronization pulse sampling error
    | (1 << 16) # a serial I/O port read operation of the frequency tuning word register reports the actual 32-bit word appearing at the input to the DDS phase accumulator (i.e. not the contents of the frequency tuning word register)
    | (1 << 24) # the amplitude is scaled by the ASF from the active profile (without this, the DDS outputs max. possible amplitude -> cracked AOM crystals)
)
# print("10987654321098765432109876543210")
# print(f"{default_cfr2:32b}")

class ad9910_drg(EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_device("urukul0_ch0") #Urukul module
        self.ad9910_0 = self.urukul0_ch0
 
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()

        delay(10*ms)

        cfr2 = (
            default_cfr2
            | (1 << 19) # enable digital ramp generator
            | (1 << 18) # enable no-dwell high functionality
            | (1 << 17) # enable no-dwell low functionality
        )
        f_start = 80*MHz                          #Starting frequency
        A_start = 0.05                             #Starting amplitude
        f_SWAP_start = 80*MHz
        f_SWAP_end = 81*MHz
        T_SWAP = 40*us           #Time spent on each step  40us corresponding to 25kHz rate
        A_SWAP = 0.08
        f_SF = 80.0*MHz          #Single frequency red MOT frequency and amplitude
        A_SF = 0.05
        f_step = (f_SWAP_end - f_SWAP_start) * 4*ns / T_SWAP

        f_start_ftw = self.ad9910_0.frequency_to_ftw(f_start)
        A_start_mu = int32(round(A_start * 0x3fff)) << 16
        f_SWAP_start_ftw = self.ad9910_0.frequency_to_ftw(f_SWAP_start)
        f_SWAP_end_ftw = self.ad9910_0.frequency_to_ftw(f_SWAP_end)
        f_step_ftw = self.ad9910_0.frequency_to_ftw((f_SWAP_end - f_SWAP_start) * 4*ns / T_SWAP)
        f_step_short_ftw = self.ad9910_0.frequency_to_ftw(f_SWAP_end - f_SWAP_start)
        A_SWAP_mu = int32(round(A_SWAP * 0x3fff)) << 16
        f_SF_ftw = self.ad9910_0.frequency_to_ftw(f_SF)
        A_SF_mu = int32(round(A_SF * 0x3fff)) << 16
        
        # ========================
        # ==== IT BEGINS HERE ====
        # ========================

        # set initial frequency and amplitude
        self.ad9910_0.write64(
            ad9910._AD9910_REG_PROFILE7,
            A_start_mu,
            f_start_ftw
        )
        delay(8*us)
        self.ad9910_0.cpld.io_update.pulse_mu(8)
        
        # enable DDS output
        self.ad9910_0.sw.on()

        # ----- Prepare for ramp -----
        # set profile parameters
        self.ad9910_0.write64(
            ad9910._AD9910_REG_PROFILE7,
            A_SWAP_mu,
            f_SWAP_start_ftw
        )

        # set ramp limits
        self.ad9910_0.write64(
            ad9910._AD9910_REG_RAMP_LIMIT,
            f_SWAP_end_ftw,
            f_SWAP_start_ftw,
        )

        # set time step
        self.ad9910_0.write32(
            ad9910._AD9910_REG_RAMP_RATE,
            ((1 << 16) | (1 << 0))
        )

        # set frequency step
        self.ad9910_0.write64(
            ad9910._AD9910_REG_RAMP_STEP,
            f_step_short_ftw,
            f_step_ftw
        )
        # set control register
        self.ad9910_0.write32(ad9910._AD9910_REG_CFR2, cfr2)

        # safety delay, try decreasing if everything works
        delay(10*us)
        
        # start ramp
        self.ad9910_0.cpld.io_update.pulse_mu(8)

        # ----- Prepare for values after end of ramp -----
        self.ad9910_0.write64(
            ad9910._AD9910_REG_PROFILE7,
            A_SF_mu,
            f_SF_ftw
        )

        # prepare control register for ramp end
        self.ad9910_0.write32(ad9910._AD9910_REG_CFR2, default_cfr2)
        # ramp duration
        delay(5*s)
        # stop ramp
        self.ad9910_0.cpld.io_update.pulse_mu(8)


        # ======================
        # ==== IT ENDS HERE ====
        # ======================

        # ------------------------------------------------------------------------
        delay(5*s)

        # self.ad9910_0.set(frequency = 80*MHz, amplitude = 0.06)
        # delay(5*s)


        # ch.experiment_trigger.off()
        delay(10*ms)