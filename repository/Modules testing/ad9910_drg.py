from artiq.experiment import *
from artiq.coredevice import ad9910
from mqva_control.experiment import MQVAExperiment
from mqva_control.tools import log

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

class Sequence(MQVAExperiment):

    def build(self):
        MQVAExperiment.build(self, config_dir="configs")
        self._pmmanager.configure_artiq_methods(self)

    def prepare(self, ch):
        log("INFO", "Preparing experiment")
        super().prepare(ch)

    @kernel
    def experiment(self, ch, sequence_type=""):
        log("INFO", "Starting experiment")
        delay(10*ms)
        ch.experiment_trigger.on()
        cfr2 = (
            default_cfr2
            | (1 << 19) # enable digital ramp generator
            | (1 << 18) # enable no-dwell high functionality
            | (1 << 17) # enable no-dwell low functionality
        )
        f_start = 168*MHz
        A_start = 0.3
        f_SWAP_start = 180*MHz
        f_SWAP_end = 190*MHz
        T_SWAP = 10*us
        A_SWAP = 0.48
        f_SF = 175*MHz
        A_SF = 0.05
        f_step = (f_SWAP_end - f_SWAP_start) * 4*ns / T_SWAP

        f_start_ftw = ch.dds1.channel.frequency_to_ftw(f_start)
        A_start_mu = int32(round(A_start * 0x3fff)) << 16
        f_SWAP_start_ftw = ch.dds1.channel.frequency_to_ftw(f_SWAP_start)
        f_SWAP_end_ftw = ch.dds1.channel.frequency_to_ftw(f_SWAP_end)
        f_step_ftw = ch.dds1.channel.frequency_to_ftw((f_SWAP_end - f_SWAP_start) * 4*ns / T_SWAP)
        f_step_short_ftw = ch.dds1.channel.frequency_to_ftw(f_SWAP_end - f_SWAP_start)
        A_SWAP_mu = int32(round(A_SWAP * 0x3fff)) << 16
        f_SF_ftw = ch.dds1.channel.frequency_to_ftw(f_SF)
        A_SF_mu = int32(round(A_SF * 0x3fff)) << 16
        
        # print("CFR1", ch.dds1.channel.read32(ad9910._AD9910_REG_CFR1))
        # delay(300*ms)
        # print("CFR2", ch.dds1.channel.read32(ad9910._AD9910_REG_CFR2))
        # delay(300*ms)
        # ========================
        # ==== IT BEGINS HERE ====
        # ========================

        # set initial frequency and amplitude
        ch.dds1.channel.write64(
            ad9910._AD9910_REG_PROFILE7,
            A_start_mu,
            f_start_ftw
        )
        ch.dds1.channel.cpld.io_update.pulse_mu(8)
        # enable DDS output
        ch.dds1.channel.sw.on()
        # trigger scope
        ch.trigger.pulse_nd(200*ns)
        # ----- Prepare for ramp -----
        # set profile parameters
        ch.dds1.channel.write64(
            ad9910._AD9910_REG_PROFILE7,
            A_SWAP_mu,
            f_SWAP_start_ftw
        )
        # set ramp limits
        ch.dds1.channel.write64(
            ad9910._AD9910_REG_RAMP_LIMIT,
            f_SWAP_end_ftw,
            f_SWAP_start_ftw,
        )
        # set time step
        ch.dds1.channel.write32(
            ad9910._AD9910_REG_RAMP_RATE,
            ((1 << 16) | (1 << 0))
        )
        # set frequency step
        ch.dds1.channel.write64(
            ad9910._AD9910_REG_RAMP_STEP,
            f_step_short_ftw,
            f_step_ftw
        )
        # set control register
        ch.dds1.channel.write32(ad9910._AD9910_REG_CFR2, cfr2)
        # safety delay, try decreasing if everything works
        delay(100*us)
        # start ramp
        ch.dds1.channel.cpld.io_update.pulse_mu(8)
        # trigger scope
        ch.trigger.pulse_nd(200*ns)
        # ----- Prepare for values after end of ramp -----
        ch.dds1.channel.write64(
            ad9910._AD9910_REG_PROFILE7,
            A_SF_mu,
            f_SF_ftw
        )
        # prepare control register for ramp end
        ch.dds1.channel.write32(ad9910._AD9910_REG_CFR2, default_cfr2)
        # ramp duration
        delay(600*us)
        # stop ramp
        ch.dds1.channel.cpld.io_update.pulse_mu(8)
        # trigger scope
        ch.trigger.pulse_nd(200*ns)

        # ======================
        # ==== IT ENDS HERE ====
        # ======================
        # print("CFR1", ch.dds1.channel.read32(ad9910._AD9910_REG_CFR1))
        # delay(300*ms)
        # print("CFR2", ch.dds1.channel.read32(ad9910._AD9910_REG_CFR2))
        # delay(300*ms)
        # ------------------------------------------------------------------------
        delay(100*us)
        ch.dds1.channel.sw.off()
        ch.experiment_trigger.off()
        delay(10*ms)