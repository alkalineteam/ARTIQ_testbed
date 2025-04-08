# -*- coding: utf-8 -*-
"""
Created on Thu Mar 13 11:09:30 2025

@author: Jjw288

No I have written the code not you jordan
"""

from artiq.experiment import *
from artiq.coredevice.ttl import TTLOut
from numpy import int64


#Atom Lock code for Artiq

#On the GUI, we want to input
#Clock probe power
#Bias Field
#Rabi pulse duration
#Scan step size
#Scan range
#Scan Center

class Artiq_Resonance_Search(EnvExperiment):
    def build(self):
        self.setattr_device("core")
        self.setattr_device("sampler0")
        
        #Assign all channels
        self.blue_mot_shutter:TTLOut=self.get_device("ttl0")
        self.repump_shutter:TTLOut=self.get_device("ttl1")
        self.red_mot_shutter:TTLOut=self.get_device("ttl2")
        self.zeeman_slower_shutter:TTLOut=self.get_device("ttl3")
        self.probe_shutter:TTLOut=self.get_device("ttl4")
        self.clock_shutter:TTLOut=self.get_device("ttl5")
        self.pmt_shutter:TTLOut=self.get_device("ttl6")
        self.camera_trigger:TTLOut=self.get_device("ttl7")
        self.camera_shutter:TTLOut=self.get_device("ttl7")        
        #AD9910
        self.blue_mot_aom = self.get_device("urukul0_ch0")
        self.probe_aom = self.get_device("urukul0_ch1")
        self.zeeman_slower_aom = self.get_device("urukul0_ch2")
        self.lattice_aom = self.get_device("urukul0_ch2")
        #AD9912
        self.red_mot_aom=self.get_device("urukul1_ch0")
        self.atom_lock_aom=self.get_device("urukul1_ch1")
        self.stepping_aom=self.get_device("urukul1_ch2")
        
        #Zotino
        self.mot_coil_1=self.get_device("zotino0")
        self.mot_coil_2=self.get_device("zotino0")
        
             
        self.setattr_argument("Cycle", NumberValue(default=1))
        self.setattr_argument("Probe_ON", NumberValue(default=1))
        self.setattr_argument("Loading_Time", NumberValue(default=2000))
        self.setattr_argument("Transfer_Time", NumberValue(default=15))
        self.setattr_argument("Holding_Time", NumberValue(default=10))
        self.setattr_argument("Compression_Time", NumberValue(default=10))
        self.setattr_argument("Single_Freq_Time", NumberValue(default=20))
        self.setattr_argument("Time_of_Flight", NumberValue(default=0))
        
        
        
        #All parameters for clock spectroscopy
        self.setattr_argument("clock_probe_power", NumberValue(default=1))
        self.setattr_argument("rabi_pulse_duration", NumberValue(default=1))
        self.setattr_argument("bias_field", NumberValue(default=0.9))
        self.setattr_argument("scan_step_size", NumberValue(default=1000*Hz))  
        self.setattr_argument("scan_center_frequency", NumberValue(default=85e+6*Hz))  
        self.setattr_argument("scan_range", NumberValue(default=1e+6*MHz))
        self.setattr_argument("rabi_linewidth", NumberValue(default=30*Hz))
        self.setattr_argument("contrast", NumberValue(default=30*Hz))
        self.setattr_argument("servo_gain_1", NumberValue(default=0.3))
        self.setattr_argument("Lock_to_atoms", BooleanValue(default=False))
        
    def sequence(self)  
    
    
    
    
    
    

    
    
    
    @kernel
    def run(self):
        self.core.reset()
        self.core.break_realtime()
        
        self.sampler0.init() 
        
        #Clock scan 
        scan_start = self.scan_center_frequency - (self.scan_range/2)
        scan_end = self.scan_center_frequency + (self.scan_range/2)
        scan_frequency_values = np.arange(scan_start,scan_end,self.scan_step_size)
        
        #Define all fixed AOM frequencies
        self.probe_aom.set(frequency=200*MHz,amplitude=0.08)
        
        #sampler parameters
        n_samples = 1000
        n_channels = 1     #1 Channel means that the data will be acquired from channel 7. 2 channels would be 6,7 and so on.
        n_bursts = 3       #We will acquire 3 bursts of data and read out in a single data set for processing on the host
      
        data = [[0] * num_samples for _ in range(num_bursts)]       #preallocates arraya
        excitation_fractions = np.zeros(len(scan_frequency_values))
        
        for i in scan_frequency_values:
            
            self.stepping_aom.set(frequency=scan_frequency_values[i],amplitude=self.clock_probe_power)  #Beginning of the cycle we set our Clock laser's frequency for this step in our scan
            self.stepping_aom.off()                                                                     #Make sure clock AOM is turned off
            
            ##############################
            
            #### 1 Cycle up to Lattice ###
            
            ###############################
           
            
           
            
           
            #######################################Red MOT Compression ###############################################
           
            
           
            
           
            
           ######################################## Single Frequency #################################################
            
           
            
            
            
           
            ###################################Helmholtz Configuration################################################
           
            with parallel:
                #switch coils to Helmholtz
                
                
                self.pmt_shutter.on()      #open PMT shutter
                self.camera_shutter.on()   #open shutter of Andor iXon ultra
                self.clock_shutter.on()    #open shutter for the clock laser
                
            delay(20*ms)               #wait for coils to switch fully before clock interrogation
            
                    
            ########################################Clock Spectroscopy################################################
           
            self.stepping_aom.pulse(self.rabi_pulse_duration)      #Rabi pulse
                    
            with parallel:                        #In parallel, we set up 3 bursts of samples from the system and do all of our blue probe detections. 
                for i in range(n_bursts):         #We could also just acquire one single data set and then divide it up? might be easier to do that
                     
                    temp = [0] * n_samples         #Temporary storage for one burst
                    self.sampler0.sample(data)     #Acquire a burst of samples

                    for j in range(n_samples):     # Store each sample in the corresponding row, column = i (burst index)
                        data[j][i] = temp[j]
                    
                    delay(10 * ms)  # Adjust based on timing needs
                self.set_dataset("pmt_data", data, broadcast=True)     #This might have to be a multidimensional array 
                    
                self.probe_shutter_on()
                
                with sequential:                            
                    self.MOT_Coil_1.write_dac(0, 4.051)  #Set coils to 0A
                    self.MOT_Coil_2.write_dac(1, 4.088)
                        
                    with parallel:
                        self.MOT_Coil_1.load()
                        self.MOT_Coil_2.load()
                
                    delay(4.5*ms)  #Wait for 0 field
                
                    self.camera_trigger.on()           #Camera should acquire here
                    self.probe_aom.pulse(0.2*ms)
                    
                    self.repump_shutter.pulse(10*ms)           #Opens repump shutter
                    delay(5*ms)
                    
                    probe_aom.pulse(0.2*ms) 
                    
                    delay(10*ms)
                    
                    probe_aom.pulse(0.2*ms)            #background pulse
                    
                    
            with parallel:
                self.probe_shutter.off()
                self.clock_shutter.off()
                self.camera_shutter.off()
                
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
                
                
          
            
            
            
            
            
            
            
            
            
