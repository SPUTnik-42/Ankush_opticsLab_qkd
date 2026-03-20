import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import math
from pathlib import Path
from scipy.stats import lognorm, test
clr = ['r', 'b-.', 'g--', 'r--', 'g.-','b.','g.'] #different line styles and colors 
matplotlib.rcParams.update({
    "font.family": "serif",
    "mathtext.fontset": "cm",   # Use Computer Modern for math
})


class SPDC_Source:
    """
    Simulates a spontaneous parametric down converter entangled photon source for BBM92 protocol.
    """
    def __init__(self, mu):
        """
        Initialize the photon source with mean photon number mu.
        
        Args:
            mu (float): Mean photon number per pulse
        """
        self.mu = mu


class Channel:
    """
    Represents the quantum channel between Alice and Bob.
    Includes both fiber and FSO (Free Space Optical) channel modeling options.
    """
    def __init__(self, base_efficiency, distance=0,mode="fiber",fiber_attenuation=0.2, weather="very clear",  atmos_visibility=40,
                 beam_waist=0.01, receiver_diameter=0.3):
        """
        Initialize the channel with distance-dependent efficiency.
        
        Args:
            base_efficiency (float): Base channel transmission efficiency without distance (0-1)
            distance (float): Channel distance in kilometers
            mode (str): Channel mode - "fiber" or "fso"
            weather (str): Weather condition for FSO channel (e.g., "very clear", "clear", "partly clear", "hazy", "foggy")
            beam_waist (float): Beam waist (radius) at the transmitter in meters for FSO channel
            receiver_diameter (float): Diameter of the receiver aperture in meters for FSO channel
            visibility (float): Visibility in kilometers for atmospheric attenuation calculation in FSO channel. 
            if weather is given, visibility is determined based on weather conditions by default.
        """
        self.base_efficiency = base_efficiency
        self.distance = distance
        if weather is not None:
            self.weather = weather.lower()  # Convert to lowercase for case-insensitive comparison
        else:
            self.weather = None
        self.fiber_attenuation = fiber_attenuation  # Fiber attenuation in dB/km for fiber channel
        
        # FSO specific parameters with default values
        self.receiver_diameter = receiver_diameter     # Diameter of receiver aperture in meters
        self.beam_waist = beam_waist                   # the initial radius of the beam
        self.visibility = atmos_visibility             # Visibility in kilometers for atmospheric attenuation calculation


        # Set mode and calculate efficiency
        self.mode = mode.lower()  # Convert to lowercase for case-insensitive comparison
        self.efficiency = self.calculate_efficiency()
        self.attenuation = fiber_attenuation #only when mode is fiber otherwise it will be updated in calculate_fso_efficiency method in line 151 
    
    def calculate_efficiency(self):
        """
        Calculate the actual channel efficiency based on distance and mode.
        
        Returns:
            float: Actual channel efficiency after distance attenuation
        """
        if self.mode == "fiber":
            return self.calculate_fiber_efficiency()
        elif self.mode == "fso":
            return self.calculate_fso_efficiency()
        else:
            raise ValueError(f"Unknown channel mode: {self.mode}")
    
    def calculate_fiber_efficiency(self):
        """
        Calculate efficiency for fiber optic channel.
        
        Returns:
            float: Channel efficiency for fiber
        """
        # Calculate attenuation in dB
        attenuation_db = self.distance * self.fiber_attenuation
        
        # Convert to transmission efficiency: 10^(-attenuation_db/10)
        distance_factor = 10**(-attenuation_db/10)
        
        # Total efficiency is base efficiency times distance factor
        return self.base_efficiency * distance_factor  # Return both efficiency and attenuation in dB/km for reference
    
    def calculate_fso_efficiency(self):
        """
        Calculate efficiency for FSO channel based on provided model.
        
        Returns:
            float: Channel efficiency for FSO
        """
        # For zero distance, return direct efficiency without atmospheric effects
        if self.distance <= 1e-6:  # Effectively zero
            return self.base_efficiency 
    
        # Calculate geometrical loss factor
        rayleigh_range = (math.pi * self.beam_waist**2) / (1550e-9)  # Rayleigh range for 1550 nm wavelength
        beam_diameter_at_receiver = self.beam_waist* math.sqrt(1 + ((self.distance*1000)/rayleigh_range)**2) 
        geo_factor = 1 - math.exp(-2 * (self.receiver_diameter / ( beam_diameter_at_receiver))**2)  # Geometric loss factor

        #caLculate visibility and q(size distribution of particles) based on weather conditions
        if self.weather is not None:
            if self.weather == "very clear":
                self.visibility = 40  
            elif self.weather == "clear":
                self.visibility = 20
            elif self.weather == "partly clear":
                self.visibility = 10
            elif self.weather == "very hazy":
                self.visibility = 2
            elif self.weather == "hazy":
                self.visibility = 3
            elif self.weather == "partly hazy":
                self.visibility = 4
            elif self.weather == "very foggy":
                self.visibility = 0.1
            elif self.weather == "foggy":
                self.visibility = 0.5
            elif self.weather == "partly foggy":
                self.visibility = 0.7
            else:
                raise ValueError(f"Unknown weather condition: {self.weather}")

        if self.visibility <= 0.5:
            q = 0.
        elif self.visibility <= 1 and self.visibility > 0.5:
            q = self.visibility-0.5
        elif self.visibility <= 6 and self.visibility > 1:
            q = 0.16*self.visibility+0.34
        elif self.visibility <= 50 and self.visibility > 6:
            q = 1.3
        elif self.visibility > 50:
            q = 1.6

        #calculate atmospheric loss factor , beer-lambert law
        wavelength_in_nm = 1550  # Assuming 1550 nm wavelength for FSO
        atmos_attenuation_coefficient = (3.91/self.visibility) * (wavelength_in_nm/550)**(-q)  # Convert attenuation to per km
        atmos_loss = math.exp(-atmos_attenuation_coefficient * self.distance)

        # attenuation in dB per km
        atmos_loss_per_km = math.exp(-atmos_attenuation_coefficient * 1.0)  # Loss for 1 km
        atmos_attenuation_db_per_km = 10*math.log10(1/atmos_loss_per_km)
        self.attenuation=round(atmos_attenuation_db_per_km,2)

        #Effect of turbulence
        refractive_index_structure_parameter=5e-18  # Example value for C_n^2 in m^(-2/3)
        scintillation_index =1.23*refractive_index_structure_parameter* (((2*np.pi)/1550e-9)**(7/6)) * (self.distance*1000)**(11/6)    
        mu = -scintillation_index/2 # mean of log of random variable I
        sigma = math.sqrt(scintillation_index) # standard deviation of log of random variable I
        random_turbulence_data = np.random.lognormal(mean=mu, sigma=sigma, size=1000)

                
        # Calculate overall transmission efficiency
        total_efficiency_data =atmos_loss*geo_factor*random_turbulence_data*self.base_efficiency
        
        return  total_efficiency_data 
    
    def update_distance(self, distance):
        """
        Update the channel distance and recalculate efficiency.
        
        Args:
            distance (float): New channel distance in kilometers
        """
        self.distance = distance
        self.efficiency = self.calculate_efficiency()
    
    def update_mode(self, mode):
        """
        Update the channel mode and recalculate efficiency.
        Default FSO parameters are automatically used when switching to FSO mode.
        
        Args:
            mode (str): New channel mode ("fiber" or "fso")
        """
        if mode not in ["fiber", "fso"]:
            raise ValueError(f"Unsupported channel mode: {mode}. Use 'fiber' or 'fso'.")
            
        self.mode = mode
        self.efficiency = self.calculate_efficiency()
    
    def set_fso_parameters(self, beam_waist=None, receiver_diameter=None, weather=None,
                          atmos_visibility=None):
        """
        Update FSO-specific parameters. Only updates the parameters that are provided.
        
        Args:
            beam_waist (float, optional): Beam waist (radius) in meters
            receiver_diameter (float, optional): Diameter of receiver aperture in meters
            beam_divergence (float, optional): Beam divergence angle in radians
        """
        if beam_waist is not None:
            self.beam_waist = beam_waist
        if receiver_diameter is not None:
            self.receiver_diameter = receiver_diameter
        if weather is not None:
            self.weather = weather.lower()  # Update weather condition and recalculate visibility
        if atmos_visibility is not None:
            self.visibility = atmos_visibility

        # Recalculate efficiency if in FSO mode
        if self.mode == "fso":
            self.efficiency = self.calculate_efficiency()

class Detector:
    """
    Represents a threshold detector with noise characteristics.
    """
    def __init__(self, efficiency, dark_count_rate, afterpulsing_prob=0.02):
        """
        Initialize detector with its characteristics.
        
        Args:
            efficiency (float): Detector efficiency (0-1)
            dark_count_rate (float): Dark count rate per pulse
            time_window (float): Detection time window in seconds
        """
        self.efficiency = efficiency
        self.dark_count_rate = dark_count_rate
        self.p_dark = dark_count_rate
        
        # Detector afterpulsing probability
        self.afterpulsing_prob = afterpulsing_prob



class BBM92Simulator:
    """
    Simulates the BBM92 QKD protocol with SPDC source.
    Supports both fiber and FSO channels.
    """
    def __init__(self, mu, alice_detector_efficiency,bob_detector_efficiency, 
                alice_channel_base_efficiency,bob_channel_base_efficiency, 
                alice_dark_count_rate=6.02e-6, bob_dark_count_rate=6.02e-6,
                alice_distance=50, alice_fiber_attenuation=0.2,
                bob_distance=50,bob_fiber_attenuation=0.2, 
                channel_mode="fiber",
                beam_waist=0.01, receiver_diameter=0.3, weather="very clear",atmos_visibility=40,
                intrinsic_detector_error_rate=0.015,bidirection_error_correction_efficiency=1.22,
                repetition_rate=249e6,bandwidth=200e9, pmd_coefficient=5e-13, is_decoherence=True):  
        """
        Initialize the BB84 simulator.
        
        Args:
            mu (float): Mean photon number
            Alice_detector_efficiency (float): Alice's detector efficiency
            Bob_detector_efficiency (float): Bob's detector efficiency
            alice_channel_base_efficiency (float): Base efficiency of quantum channel for Alice
            bob_channel_base_efficiency (float): Base efficiency of quantum channel for Bob
            Alice_dark_count_rate (float): Dark count rate in counts per second for Alice's detector
            dark_count_rate (float): Dark count rate in counts per second for Bob's detector
            Alice_distance (float): Distance between Alice and source in kilometers
            Bob_distance (float): Distance between Bob and source in kilometers
            attenuation (float): Fiber attenuation coefficient in dB/km
            channel_mode (str): Channel mode - "fiber" or "fso"
            intrinsic_detector_error_rate (float):(0-1)Here we 
            assume that Alice and Bob use detectors with the same characteristics.
            bidirection_error_correction_efficiency (float): Efficiency factor for error correction (e.g., 1.16 for bidirectional error correction)
            frequency bandwidth of laser(Hz) = 200e9(default)
            PMD Coefficient(tau_0) in units of picosecond/sqrt(km)= 0.5 
            is decoherence(only needed for fiber calculations):True or False
        """
        self.source = SPDC_Source(mu)
        self.mu = mu
        self.alice_channel = Channel(alice_channel_base_efficiency, alice_distance, channel_mode,alice_fiber_attenuation, 
                                weather=weather,
                                beam_waist=beam_waist,
                                receiver_diameter=receiver_diameter,
                                atmos_visibility=atmos_visibility,)
        self.bob_channel = Channel(bob_channel_base_efficiency, bob_distance,channel_mode, bob_fiber_attenuation,
                                weather=weather,
                                beam_waist=beam_waist,
                                receiver_diameter=receiver_diameter,
                                atmos_visibility=atmos_visibility,)        
        self.alice_detector = Detector(alice_detector_efficiency, alice_dark_count_rate)
        self.bob_detector = Detector(bob_detector_efficiency, bob_dark_count_rate)
        self.repetition_rate = repetition_rate  # Default pulse rate: 249MHz
        self.channel_mode = channel_mode
        self.intrinsic_detector_error_rate = intrinsic_detector_error_rate
        self.bidirection_error_correction_efficiency = bidirection_error_correction_efficiency
        self.pmd_coefficient=pmd_coefficient
        self.bandwidth=bandwidth
        self.is_decoherence=is_decoherence
    
    def update_alice_distance(self, alice_distance):
        """
        Update the distance between Alice and Source and recalculate channel efficiency and overall detection efficiency.
        
        Args:
            distance (float): New distance in kilometers
        """
        self.alice_distance = alice_distance
        self.alice_channel.update_distance(alice_distance)

    def update_bob_distance(self, bob_distance):
        """
        Update the distance between source and Bob and recalculate channel efficiency and overall detection efficiency.
        
        Args:
            distance (float): New distance in kilometers
        """
        self.bob_distance = bob_distance
        self.bob_channel.update_distance(bob_distance)
    
    def update_channel_mode(self, mode):
        """
        Update the channel mode (fiber or FSO).
        
        Args:
            mode (str): New channel mode ("fiber" or "fso")
        """
        self.channel_mode = mode
        self.alice_channel.update_mode(mode)
        self.bob_channel.update_mode(mode)
    
    def set_fso_parameters(self, beam_waist=None, receiver_diameter=None, 
                          weather=None, atmos_visibility=None):
        """
        Update FSO-specific parameters in the channel.
        
        Args:
            beam_waist (float, optional): Beam waist (radius) in meters
            receiver_diameter (float, optional): Diameter of receiver aperture in meters
            weather (str, optional): Weather condition for FSO channel (e.g., "very clear", "clear", "partly clear", "hazy", "foggy")
            atmos_visibility (float, optional): Visibility in kilometers for atmospheric attenuation calculation in FSO channel. If weather is given, visibility is determined based on weather conditions by default.
        """
        self.alice_channel.set_fso_parameters(
            beam_waist, receiver_diameter, 
            weather, atmos_visibility
        )
        self.bob_channel.set_fso_parameters(
            beam_waist, receiver_diameter, 
            weather, atmos_visibility
        )
    
    def update_mu(self, mu):
        """
        Update the mean photon number.
        
        Args:
            mu (float): New mean photon number
        """
        self.mu = mu
        self.source = SPDC_Source(mu)

    def overall_alice_detection_efficiency(self):
        """
        returns Alice overall detection efficiency = channel efficiency * detector efficiency

        It takes into account the channel losses,detector efficiencies,couplingefficiencies,and losses inside the detector box.
        
        """
        return (self.alice_channel.efficiency)*(self.alice_detector.efficiency)
    
    def overall_bob_detection_efficiency(self):
        """
        returns Bob overall detection efficiency = channel efficiency * detector efficiency

        It takes into account the channel losses,detector efficiencies,coupling efficiencies,and losses inside the detector box.
        
        """
        return (self.bob_channel.efficiency)*(self.bob_detector.efficiency)  

    def phase_error_in_decoherence(self):
                # ---------- Compute I(Z) ----------
        if self.alice_distance==0:
            z_a=0.1
        else:z_a=self.alice_distance

        if self.bob_distance==0:
            z_b=0.1
        else:z_b=self.bob_distance


        
        delta_omega_A = self.bandwidth
        delta_omega_B = self.bandwidth
        pi=math.pi
        tau0=self.pmd_coefficient
        alpha1 = (8 * (delta_omega_A**2 + delta_omega_B**2)) / (
            pi * delta_omega_A**2 * delta_omega_B**2 * tau0**2 * z_a
        )
        alpha2 =(8 * (delta_omega_A**2 + delta_omega_B**2)) / (
            pi * delta_omega_A**2 * delta_omega_B**2 * tau0**2 * z_b
        )

        A = alpha1 * alpha2 + alpha1 + alpha2

        R = (
            (alpha1 * alpha2) ** (3 / 2)
            * (
                6 * np.sqrt(A)
                + (A + 3) * pi
                + 2 * (A + 3) * np.arctan(1 / np.sqrt(A))
            )
        ) / (A ** (5 / 2) * pi)

        phase_error_in_decoherence =0.5 * (1 - R)
        return phase_error_in_decoherence
    
    def calculate_raw_key_rate(self):
        """
        Calculate the raw key rate (before sifting).

        It is the gain of the n-photon pair Qn, which is the product of probability to get an n-photon pair out 
        of a PDC source and yield of a n photon pair , is given by Q_mu=∑n=0∞ Q_n =∑n=0∞ Pn*Yn
        
        Returns:
            float: Raw key rate in bit per pulse
        """
        η_A = self.overall_alice_detection_efficiency()
        η_B = self.overall_bob_detection_efficiency()
        Y0_A = self.alice_detector.p_dark
        Y0_B = self.bob_detector.p_dark
        lmbda = self.mu / 2
        term1 = (1 - Y0_A) / (1 + η_A * lmbda)**2
        term2 = (1 - Y0_B) / (1 + η_B * lmbda)**2
        term3 = ((1 - Y0_A) * (1 - Y0_B))/(1 + η_A * lmbda + η_B * lmbda - η_A * η_B * lmbda)**2
        return 1 - term1 - term2 + term3

    
    def calculate_quantum_bit_error_rate(self):
            
        """
        The error probability for the state |n-m,m⟩|m,n-m⟩ is
        e_nm=e_0-((e_0-e_d)/Y_n)(((1-η_A)^(n-m)-(1-η_A)^m)((1-η_B)^(n-m)-(1-η_B)^m))
        In general, for an n-photon-pair state |ϕ_n⟩
        the error rate is given by 
        e_n= (1/(n+1))∑m=0n e_nm
        where e_0=1/2 is the error rate of background counts, e_d is the intrinsic detector error rate, and Y_n is the yield of a n-photon pair state.

        The overall QBER is given by Eμ=∑n=0∞ e_n*Y_n*P_n, where Qn is the gain of a n-photon pair state. 
       """
        e_d= self.intrinsic_detector_error_rate
        η_A = self.overall_alice_detection_efficiency()
        η_B = self.overall_bob_detection_efficiency()
        Q_lambda = self.calculate_raw_key_rate()
        lmbda = self.mu / 2
        e_0= 0.5 # Error rate of background counts (dark counts)
        
        if self.channel_mode =="fso":

            num = 2 * (e_0 - e_d) *  η_A * η_B * lmbda * (1 + lmbda)
            
            denom = ((1 +  η_A * lmbda) *(1 + η_B * lmbda) *(1 + η_A * lmbda + η_B * lmbda - η_A * η_B * lmbda))
            
            bit_error_rate= (e_0 * Q_lambda - num/ denom)/Q_lambda
            phase_error_rate=bit_error_rate
            return bit_error_rate,phase_error_rate
        
        elif self.channel_mode=="fiber":
            if self.is_decoherence==False:
                num = 2 * (e_0 - e_d) *  η_A * η_B * lmbda * (1 + lmbda)
                
                denom = ((1 +  η_A * lmbda) *(1 + η_B * lmbda) *(1 + η_A * lmbda + η_B * lmbda - η_A * η_B * lmbda))
                
                bit_error_rate= (e_0 * Q_lambda - num/ denom)/Q_lambda
                phase_error_rate=bit_error_rate
                return bit_error_rate,phase_error_rate 
            else:
                num1 = 2 * (e_0 - e_d) *  η_A * η_B * lmbda * (1 + lmbda)
                denom = ((1 +  η_A * lmbda) *(1 + η_B * lmbda) *(1 + η_A * lmbda + η_B * lmbda - η_A * η_B * lmbda)) 
                bit_error_rate= (e_0 * Q_lambda - num1/ denom)/Q_lambda

                net_detector_error_rate=self.intrinsic_detector_error_rate+self.phase_error_in_decoherence()
                num2 = 2 * (e_0 - net_detector_error_rate) *  η_A * η_B * lmbda * (1 + lmbda)
                phase_error_rate= (e_0 * Q_lambda - num2/ denom)/Q_lambda

                return bit_error_rate,phase_error_rate 
        else:
            raise ValueError(f"Unknown channel mode: {self.mode}")



    
    def binary_entropy_function(self, p):
        """
        Binary entropy function H(p) = -p*log2(p) - (1-p)*log2(1-p).
        
        Args:
            p (float): Probability (0 <= p <= 1)
            
        Returns:
            float: Binary entropy value
        """
        bool_array = (p == 0) | (p == 1)
        result = np.where(bool_array, 0, -p * np.log2(p) - (1 - p) * np.log2(1 - p))
        return result
    
    def calculate_skr(self):
        """
        Calculate the secret key rate (SKR).
        skr=q{raw_key_rate[1-f(𝛿_b)H(𝛿_b)-H(𝛿_p)]}
           =q{raw_key_rate[1-f(qber)H(qber)-H(qber)]}
        
        Returns:
            float: Secret key rate per pulse
        """
        #Bi-directional error correction efficiency factor (e.g., 1.22 for bidirectional error correction)
        ec_eff = self.bidirection_error_correction_efficiency
        
        # Calculate QBER (E_μ)
        bit_error_rate,phase_error_rate = self.calculate_quantum_bit_error_rate() # Convert from percentage to fraction
        
        # Basis reconciliation factor for BBM92 is 0.5 since only half of the bits are kept after sifting
        q = 0.5
        
        # Calculate overall gain (Q_μ) - probability of detection per pulse
        Q_mu = self.calculate_raw_key_rate()

        #Secure key rate per pulse is given by:
        SKR_per_pulse = q* Q_mu * (1 - ec_eff * self.binary_entropy_function(bit_error_rate) - self.binary_entropy_function(phase_error_rate))
        
        # Calculate the final secret key rate 
        skr = SKR_per_pulse * self.repetition_rate
        
        return  skr
    

def plot_qber_vs_distance(mu=0.1, distance_values=None, position_of_source="middle",
                   alice_detector_efficiency=0.145,bob_detector_efficiency=0.145,
                   alice_channel_base_efficiency=1, bob_channel_base_efficiency=1,
                   alice_dark_count_rate=6.02e-6, bob_dark_count_rate=6.02e-6, channel_mode="fiber",fiber_attenuation_list=[0.18,0.21,0.24],
                   weather_list=("very clear","clear","partly clear","hazy","foggy"), atmos_visibility_list=[40,30,20,10,5],is_decoherence=True, save_fig=False, **kwargs):
    """
    Plot QBER vs distance.
    
    Args:
        distance_values (list, optional): List of distance values to simulate in kilometers
        position_of_source (str, optional): Position of source - "middle" or "alice"
        alice_detector_efficiency (float, optional): Alice's detector efficiency
        bob_detector_efficiency (float, optional): Bob's detector efficiency
        bob_channel_base_efficiency (float, optional): Bob's base channel efficiency
        alice_channel_base_efficiency (float, optional): Alice's base channel efficiency
        alice_dark_count_rate (float, optional): Alice's dark count rate in counts per pulse
        bob_dark_count_rate (float, optional): Bob's dark count rate in counts per pulse
        channel_mode (str, optional): Channel mode - "fiber" or "fso"
        fso_params (dict, optional): Custom FSO parameters if needed
    """
    if distance_values is None:
        distance_values = np.linspace(0, 120, 100)
    qber_values_list = []
    ber_values_list=[]
    per_values_list=[]
    attenuation_list = []


    if channel_mode == "fso":

        plt.figure(figsize=(8,5))

        if (weather_list is None or len(weather_list) == 0) and (atmos_visibility_list is None or len(atmos_visibility_list) == 0):
            weather_list = ["very clear", "clear", "partly clear", "hazy", "foggy"]
        
        if len(weather_list) > 0:
            for weather in weather_list:
                qber_values=[]
                
                simulator = BBM92Simulator(
                    mu=mu,
                    alice_detector_efficiency=alice_detector_efficiency,
                    bob_detector_efficiency=bob_detector_efficiency,
                    alice_channel_base_efficiency=alice_channel_base_efficiency,
                    bob_channel_base_efficiency=bob_channel_base_efficiency,
                    alice_dark_count_rate=alice_dark_count_rate,
                    bob_dark_count_rate=bob_dark_count_rate,
                    alice_distance=0,#will be updated in the loop
                    bob_distance=0,#will be updated in the loop
                    channel_mode=channel_mode, weather=weather, **kwargs
                )
                
                simulator.set_fso_parameters(weather=weather)
                
                for distance in distance_values:
                    if position_of_source == "middle":
                        alice_distance = distance / 2
                        bob_distance = distance/ 2
                    elif position_of_source == "alice":
                        alice_distance = 0
                        bob_distance = distance
                    else: raise ValueError(f"Invalid position_of_source: {position_of_source}. Use 'middle' or 'alice'.")
                    simulator.update_alice_distance(alice_distance)
                    simulator.update_bob_distance(bob_distance)
                    bit_error_rate,phase_error_rate=simulator.calculate_quantum_bit_error_rate()
                    qber = np.mean(bit_error_rate)
                    qber_values.append(qber)
                qber_values_list.append(qber_values)
                attenuation_list.append(simulator.bob_channel.attenuation)

            for i in range(len(weather_list)):
                plt.plot(distance_values, qber_values_list[i], clr[i], linewidth=2, label=f'({weather_list[i]} weather,{attenuation_list[i]} dB/km)')
            

        if (weather_list is None or len(weather_list) == 0) and len(atmos_visibility_list) > 0:
            for visibility in atmos_visibility_list:
                qber_values=[]
                simulator = BBM92Simulator(
                    mu=mu,
                    alice_detector_efficiency=alice_detector_efficiency,
                    bob_detector_efficiency=bob_detector_efficiency,
                    alice_channel_base_efficiency=alice_channel_base_efficiency,
                    bob_channel_base_efficiency=bob_channel_base_efficiency,
                    alice_dark_count_rate=alice_dark_count_rate,
                    bob_dark_count_rate=bob_dark_count_rate,
                    alice_distance=0,#will be updated in the loop
                    bob_distance=0,#will be updated in the loop
                    channel_mode=channel_mode, weather=None, atmos_visibility=visibility, **kwargs
                )
                
                simulator.set_fso_parameters(weather=None, atmos_visibility=visibility)
                
                for distance in distance_values:
                    if position_of_source == "middle":
                        alice_distance = distance / 2
                        bob_distance = distance/ 2
                    elif position_of_source == "alice":
                        alice_distance = 0
                        bob_distance = distance
                    else: raise ValueError(f"Invalid position_of_source: {position_of_source}. Use 'middle' or 'alice'.")
                    simulator.update_alice_distance(alice_distance)
                    simulator.update_bob_distance(bob_distance)
                    bit_error_rate,phase_error_rate=simulator.calculate_quantum_bit_error_rate()
                    qber = np.mean(bit_error_rate)
                    qber_values.append(qber)
                qber_values_list.append(qber_values)
                
                attenuation_list.append(simulator.bob_channel.attenuation)
            for i in range(len(atmos_visibility_list)):
                plt.plot(distance_values, qber_values_list[i], clr[i], linewidth=2, label=f'(attenuation {attenuation_list[i]} dB/km),visibility up to {atmos_visibility_list[i]} km')
                plt.grid(False)
        plt.xlabel('Distance (km)', fontsize=11)
        plt.ylabel('QBER per pulse', fontsize=11)
        plt.title(f'QBER vs Distance ({channel_mode.upper()} channel)',fontsize=11)
        plt.xticks(fontsize=11)
        plt.yticks(np.linspace(0,0.7,8),fontsize=11)
        plt.xlim(0,np.max(distance_values))
        plt.ylim(0,0.7)
        plt.axhline(0.11, color="orange", linestyle="--", alpha=0.7,label="QBER 11% thresold")
        plt.axhline(0.5, linestyle="--", alpha=0.6)
        plt.legend(loc="upper right")
        # if save_fig:
        # #     save_path = Path("C:\Users\Public\Documents")/f"qber_vs_distance_{channel_mode}.pdf"
        # #     plt.savefig(save_path, bbox_inches="tight", dpi=300)
        # plt.show()
    if channel_mode == "fiber":
        if is_decoherence==True:
            deco="presence"
        else:
            deco="absent"
        attenuation_list=fiber_attenuation_list 
        for attenuation in attenuation_list:
            qber_values=[]
            ber_values=[]
            per_values =[]
            simulator = BBM92Simulator(
                mu=mu,
                alice_detector_efficiency=alice_detector_efficiency,
                bob_detector_efficiency=bob_detector_efficiency,
                alice_channel_base_efficiency=alice_channel_base_efficiency,
                bob_channel_base_efficiency=bob_channel_base_efficiency,
                alice_dark_count_rate=alice_dark_count_rate,
                bob_dark_count_rate=bob_dark_count_rate,
                alice_distance=0,#will be updated in the loop
                bob_distance=0,#will be updated in the loop
                channel_mode=channel_mode, bob_fiber_attenuation=attenuation, alice_fiber_attenuation=attenuation,is_decoherence=is_decoherence, **kwargs
            )
            
            for distance in distance_values:
                if position_of_source == "middle":
                    alice_distance = distance / 2
                    bob_distance = distance/ 2
                elif position_of_source == "alice":
                    alice_distance = 0
                    bob_distance = distance
                else: raise ValueError(f"Invalid position_of_source: {position_of_source}. Use 'middle' or 'alice'.")
                simulator.update_alice_distance(alice_distance)
                simulator.update_bob_distance(bob_distance)
                bit_error_rate,phase_error_rate=simulator.calculate_quantum_bit_error_rate()
                ber = np.mean(bit_error_rate)
                per = np.mean(phase_error_rate)
                qber=(ber+per)/2
                ber_values.append(ber)
                per_values.append(per)
                qber_values.append(qber)
            qber_values_list.append(qber_values)
            ber_values_list.append(ber_values)
            per_values_list.append(per_values)
        plt.figure(figsize=(8,5))
        for i in range(len(attenuation_list)):
            plt.plot(distance_values, qber_values_list[i], clr[i], linewidth=2, label=f'(fiber attenuation {attenuation_list[i]} dB/km)')
        plt.grid(False)
        plt.xlabel('Distance (km)', fontsize=11)
        plt.ylabel('QBER per pulse', fontsize=11)
        plt.title(f'QBER vs Distance in {channel_mode.upper()} channel(in {deco} of decoherence)',fontsize=11)
        plt.axhline(0.11, color="orange", linestyle="--", alpha=0.7,label="QBER 11% thresold")
        plt.axhline(0.5, linestyle="--", alpha=0.6)
        plt.legend()
        plt.xticks(fontsize=11)
        plt.yticks(fontsize=11)
        plt.xlim(0,np.max(distance_values))
        plt.ylim(0,0.7)
        # if save_fig:
        # #     save_path = Path("C:\Users\Public\Documents")/f"qber_vs_distance_{channel_mode}.pdf"
        # #     plt.savefig(save_path, bbox_inches="tight", dpi=300)
        # plt.show()

        if simulator.is_decoherence==True:
            plt.figure(figsize=(8,5))
            
            plt.plot(distance_values, qber_values_list[2], clr[1], linewidth=2, label=f'(Overall QBER)')
            plt.plot(distance_values, ber_values_list[2], clr[2], linewidth=2, label=f'(Bit error rate)')
            plt.plot(distance_values,per_values_list[2], clr[3], linewidth=2, label=f'(phase error rate)')
            
            plt.grid(False)
            #plt.axhline(y=7, color='orange', linestyle='--', label='QBER 7% Threshold')
            plt.xlabel('Distance (km)', fontsize=11)
            plt.ylabel('QBER per pulse', fontsize=11)
            plt.title(f'QBER vs Distance in {channel_mode.upper()} channel (in presence of decoherence)',fontsize=11)
            plt.legend( loc="upper right")
            plt.xticks(fontsize=11)
            plt.yticks(fontsize=11)
            plt.xlim(0,np.max(distance_values))
            plt.ylim(0,0.7)
            # if save_fig:
            # #     save_path = Path("C:\Users\Public\Documents")/f"qber_vs_distance_{channel_mode}.pdf"
            # #     plt.savefig(save_path, bbox_inches="tight", dpi=300)
            # plt.show()
                # ---------- QBER threshold ----------
            QBER_th = 0.11
            E3=np.array(qber_values_list[2])
            Z_vals=distance_values

            # Find crossing point (first time E3 >= threshold)
            idx_th = np.where(E3 >= QBER_th)[0][0]
            Z_th = Z_vals[idx_th]
            E_th = E3[idx_th]


            # Mark QBER threshold crossing
            plt.axhline(QBER_th, color="red", linestyle="--", alpha=0.7, label="QBER Threshold")

            plt.scatter(Z_th, E_th, color="red", zorder=7)
            plt.annotate(
                f"Threshold reached\nZ = {Z_th:.0f} Km\nE = {E_th:.2f}",
                xy=(Z_th, E_th),
                xytext=(Z_th * 0.6, E_th + 0.05),
                arrowprops=dict(arrowstyle="->", color="red"),
            )

            plt.axhline(0.5, linestyle="--", alpha=0.6)
            

    return None



def plot_skr_vs_distance(mu=0.1, distance_values=None, position_of_source="middle",
                   alice_detector_efficiency=0.145,bob_detector_efficiency=0.145,
                   alice_channel_base_efficiency=1, bob_channel_base_efficiency=1,
                   alice_dark_count_rate=6.02e-6, bob_dark_count_rate=6.02e-6, channel_mode="fiber",fiber_attenuation_list=[0.18,0.21,0.24],
                   weather_list=("very clear","clear","partly clear","hazy","foggy"), atmos_visibility_list=[40,30,20,10,5], save_fig=False, log_scale=False, **kwargs):
    """
    Plot Secret Key Rate vs distance.
    
    Args:
        distance_values (list, optional): List of distance values to simulate in kilometers
        time_window (float, optional): Detection time window in seconds
        mu (float, optional): Mean photon number
        detector_efficiency (float, optional): Detector efficiency
        channel_base_efficiency (float, optional): Base channel efficiency
        dark_count_rate (float, optional): Dark count rate in counts per second
        channel_mode (str, optional): Channel mode - "fiber" or "fso"
        fso_params (dict, optional): Custom FSO parameters if needed
    """
    if distance_values is None:
        distance_values = np.linspace(0, 120, 100)
    skr_values_list = []
    attenuation_list = []

    plt.figure(figsize=(8,5))
    if channel_mode == "fso":
        if (weather_list is None or len(weather_list) == 0) and (atmos_visibility_list is None or len(atmos_visibility_list) == 0):
            weather_list = ["very clear", "clear", "partly clear", "hazy", "foggy"]
        
        if len(weather_list) > 0:
            for weather in weather_list:
                skr_values=[]
                
                simulator = BBM92Simulator(
                    mu=mu,
                    alice_detector_efficiency=alice_detector_efficiency,
                    bob_detector_efficiency=bob_detector_efficiency,
                    alice_channel_base_efficiency=alice_channel_base_efficiency,
                    bob_channel_base_efficiency=bob_channel_base_efficiency,
                    alice_dark_count_rate=alice_dark_count_rate,
                    bob_dark_count_rate=bob_dark_count_rate,
                    alice_distance=0,#will be updated in the loop
                    bob_distance=0,#will be updated in the loop
                    channel_mode=channel_mode, weather=weather, **kwargs
                )
                
                simulator.set_fso_parameters(weather=weather)
                
                for distance in distance_values:
                    if position_of_source == "middle":
                        alice_distance = distance / 2
                        bob_distance = distance/ 2
                    elif position_of_source == "alice":
                        alice_distance = 0
                        bob_distance = distance
                    else: raise ValueError(f"Invalid position_of_source: {position_of_source}. Use 'middle' or 'alice'.")
                    simulator.update_alice_distance(alice_distance)
                    simulator.update_bob_distance(bob_distance)
                    skr = np.mean(simulator.calculate_skr())
                    skr_values.append(skr)
                skr_values_list.append(skr_values)
                attenuation_list.append(simulator.bob_channel.attenuation)

            for i in range(len(weather_list)):
                if log_scale:
                    plt.semilogy(distance_values, skr_values_list[i], clr[i], linewidth=2, label=f'({weather_list[i]} weather,{attenuation_list[i]} dB/km)')
                else:
                    plt.plot(distance_values, skr_values_list[i], clr[i], linewidth=2, label=f'({weather_list[i]} weather,{attenuation_list[i]} dB/km)')

        if (weather_list is None or len(weather_list) == 0) and len(atmos_visibility_list) > 0:
            for visibility in atmos_visibility_list:
                skr_values=[]
                simulator = BBM92Simulator(
                    mu=mu,
                    alice_detector_efficiency=alice_detector_efficiency,
                    bob_detector_efficiency=bob_detector_efficiency,
                    alice_channel_base_efficiency=alice_channel_base_efficiency,
                    bob_channel_base_efficiency=bob_channel_base_efficiency,
                    alice_dark_count_rate=alice_dark_count_rate,
                    bob_dark_count_rate=bob_dark_count_rate,
                    alice_distance=0,#will be updated in the loop
                    bob_distance=0,#will be updated in the loop
                    channel_mode=channel_mode, weather=None, atmos_visibility=visibility, **kwargs
                )
                
                simulator.set_fso_parameters(weather=None, atmos_visibility=visibility)
                
                for distance in distance_values:
                    if position_of_source == "middle":
                        alice_distance = distance / 2
                        bob_distance = distance/ 2
                    elif position_of_source == "alice":
                        alice_distance = 0
                        bob_distance = distance
                    else: raise ValueError(f"Invalid position_of_source: {position_of_source}. Use 'middle' or 'alice'.")
                    simulator.update_alice_distance(alice_distance)
                    simulator.update_bob_distance(bob_distance)
                    skr = np.mean(simulator.calculate_skr())
                    skr_values.append(skr)
                skr_values_list.append(skr_values)
                
                attenuation_list.append(simulator.bob_channel.attenuation)
            for i in range(len(atmos_visibility_list)):
                if log_scale:
                    plt.semilogy(distance_values, skr_values_list[i], clr[i], linewidth=2, label=f'(attenuation {attenuation_list[i]} dB/km),visibility up to {atmos_visibility_list[i]} km')
                else:
                    plt.plot(distance_values, skr_values_list[i], clr[i], linewidth=2, label=f'(attenuation {attenuation_list[i]} dB/km),visibility up to {atmos_visibility_list[i]} km')

    if channel_mode == "fiber":
        attenuation_list=fiber_attenuation_list 
        for attenuation in attenuation_list:
            skr_values=[]
            simulator = BBM92Simulator(
                mu=mu,
                alice_detector_efficiency=alice_detector_efficiency,
                bob_detector_efficiency=bob_detector_efficiency,
                alice_channel_base_efficiency=alice_channel_base_efficiency,
                bob_channel_base_efficiency=bob_channel_base_efficiency,
                alice_dark_count_rate=alice_dark_count_rate,
                bob_dark_count_rate=bob_dark_count_rate,
                alice_distance=0,#will be updated in the loop
                bob_distance=0,#will be updated in the loop
                channel_mode=channel_mode, bob_fiber_attenuation=attenuation, alice_fiber_attenuation=attenuation, **kwargs
            )
            
            for distance in distance_values:
                if position_of_source == "middle":
                    alice_distance = distance / 2
                    bob_distance = distance/ 2
                elif position_of_source == "alice":
                    alice_distance = 0
                    bob_distance = distance
                else: raise ValueError(f"Invalid position_of_source: {position_of_source}. Use 'middle' or 'alice'.")
                simulator.update_alice_distance(alice_distance)
                simulator.update_bob_distance(bob_distance)
                skr = np.mean(simulator.calculate_skr())
                skr_values.append(skr)
            skr_values_list.append(skr_values)
        for i in range(len(attenuation_list)):
            if log_scale:
                plt.semilogy(distance_values, skr_values_list[i], clr[i], linewidth=2, label=f'(fiber attenuation {attenuation_list[i]} dB/km)')
            else:
                plt.plot(distance_values, skr_values_list[i], clr[i], linewidth=2, label=f'(fiber attenuation {attenuation_list[i]} dB/km)')

    plt.grid(False)
    plt.xlabel('Distance (km)', fontsize=11)
    plt.ylabel('Secret Key Rate (per second)', fontsize=11)
    plt.title(f'Secret Key Rate vs Distance ({channel_mode.upper()} channel)',fontsize=11)
    #plt.title(f'Quantum Bit Error Rate vs Distance ({channel_mode.upper()} channel)',fontsize=25)
    plt.legend()
    plt.xticks(fontsize=11)
    plt.yticks(fontsize=11)
    plt.xlim(0, max(distance_values))
    # if save_fig:
    #     save_path = Path("C:\Users\Public\Documents")/f"qber_vs_distance_{channel_mode}.pdf"
    #     plt.savefig(save_path, bbox_inches="tight", dpi=300)
    # plt.show()
        
    
    return None


if __name__ == '__main__':
    plot_qber_vs_distance(mu=0.1, distance_values=np.linspace(0, 350, 300),
                    alice_detector_efficiency=0.15,
                    bob_detector_efficiency=0.15,
                    bob_channel_base_efficiency=1.0,
                    alice_channel_base_efficiency=1.0,
                    position_of_source="middle",fiber_attenuation_list=[0.18,0.21,0.24],
                    channel_mode="fso",weather_list=("very clear","clear","partly clear","hazy"),atmos_visibility_list=[40,30,20,10,5],
                    save_fig=True)
    plot_qber_vs_distance(mu=0.1, distance_values=np.linspace(0, 800, 300),
                    alice_detector_efficiency=0.15,
                    bob_detector_efficiency=0.15,
                    bob_channel_base_efficiency=1.0,
                    alice_channel_base_efficiency=1.0,
                    position_of_source="middle",fiber_attenuation_list=[0.18,0.21,0.24],
                    channel_mode="fiber",weather_list=("very clear","clear","partly clear","hazy"),atmos_visibility_list=[40,30,20,10,5],
                    save_fig=True)

    ##skr vs distance plot test

    plot_skr_vs_distance(mu=0.1, distance_values=np.linspace(0, 400, 400),
                    alice_detector_efficiency=0.145,
                    bob_detector_efficiency=0.145,
                    bob_channel_base_efficiency=1.0,
                    alice_channel_base_efficiency=1.0,
                    position_of_source="middle",fiber_attenuation_list=[0.18,0.21,0.24],
                    channel_mode="fiber",weather_list=("very clear","clear","partly clear","hazy"),atmos_visibility_list=[40,30,20,10,5],
                    save_fig=True, log_scale=True)

    plot_skr_vs_distance(mu=0.1, distance_values=np.linspace(0, 200, 300),
                    alice_detector_efficiency=0.145,
                    bob_detector_efficiency=0.145,
                    bob_channel_base_efficiency=1.0,
                    alice_channel_base_efficiency=1.0,
                    position_of_source="middle",fiber_attenuation_list=[0.18,0.21,0.24],
                    channel_mode="fso",weather_list=("very clear","clear","partly clear","hazy"),atmos_visibility_list=[40,30,20,10,5],
                    save_fig=True, log_scale=True)


    def optimal_mu_vs_intrinsic_detector_error():
        """Plot optimal μ vs intrinsic detector error for given values."""
        mu_opt_list_values = []
        Alice_detector_efficiencies_to_test = [0.0001, 0.5, 1.0]
        for eta_A in Alice_detector_efficiencies_to_test:
            eta_B = 0.01
            Y_0A = 0
            Y_0B = 0
            q = 0.5
            f = 1.22

            def binary_entropy(x):
                x = np.clip(x, 1e-12, 1-1e-12)
                return -x*np.log2(x) - (1-x)*np.log2(1-x)

            def gain(lambda_):
                term1 = (1 - Y_0A) / (1 + eta_A * lambda_)**2
                term2 = (1 - Y_0B) / (1 + eta_B * lambda_)**2
                term3 = ((1 - Y_0A)*(1 - Y_0B)) / \
                        (1 + eta_A*lambda_ + eta_B*lambda_ - eta_A*eta_B*lambda_)**2
                return 1 - term1 - term2 + term3

            def qber(lambda_, e_d):
                Q = gain(lambda_)
                numerator = 2*(0.5 - e_d)*eta_A*eta_B*lambda_*(1+lambda_)
                denominator = (1 + eta_A*lambda_) * (1 + eta_B*lambda_) * \
                            (1 + eta_A*lambda_ + eta_B*lambda_ - eta_A*eta_B*lambda_)
                return 0.5 - numerator/(denominator*Q)

            def skr(lambda_, e_d):
                Q = gain(lambda_)
                E = qber(lambda_, e_d)
                return q * Q * (1 - f*binary_entropy(E) - binary_entropy(E))

            # Sweep intrinsic detector error
            e_d_values = np.linspace(0.001, 0.1, 50)
            mu_opt_list = []

            for e_d in e_d_values:
                lambda_values = np.linspace(0.001, 0.25, 2000)
                R_values = [skr(l, e_d) for l in lambda_values]
                best_lambda = lambda_values[np.argmax(R_values)]
                mu_opt_list.append(2*best_lambda)
            mu_opt_list_values.append(mu_opt_list)
        plt.figure(figsize=(8,5))
        for i in range(len(mu_opt_list_values)):
            plt.plot(e_d_values, mu_opt_list_values[i], linewidth=2.0, label=f'Alice detector efficiency = {Alice_detector_efficiencies_to_test[i]}')
        plt.xlabel("Intrinsic detector error rate ("+r'$e_d$'+")", fontsize=14)
        plt.ylabel("Optimal μ")
        plt.title("Optimal μ vs Intrinsic Detector Error Rate")
        plt.xticks(np.arange(0.0, 0.11, 0.01))
        plt.yticks(np.arange(0.0, 0.26, 0.05))
        plt.legend()
        plt.xlim(0, 0.1)
        plt.ylim(0, 0.25)
        plt.grid()
        # plt.show()
    optimal_mu_vs_intrinsic_detector_error()

    #scintillation index versus distance plot for different refractive index structure parameters
    plt.figure(figsize=(8,5))
    refractive_index_structure_parameter_list=[5e-18, 
                                              1e-17,  
                                              2e-17,
                                              4e-17]  
    i=0
    for refractive_index_structure_parameter in refractive_index_structure_parameter_list:
        y=str(refractive_index_structure_parameter).split('e')

        scintillation_index_list = []
        distance_list = list(range(0, 51, 5))  # Example distances from 1 km to 100 km
        i+=1
        for distance in distance_list: 
            scintillation_index =1.23*refractive_index_structure_parameter* (((2*np.pi)/1550e-9)**(7/6)) * (distance*1000)**(11/6)
            scintillation_index_list.append(scintillation_index)
            
        plt.plot(distance_list, scintillation_index_list,clr[i],linewidth=2,)
        plt.xlabel("Distance (km)", fontsize=14)
        plt.ylabel(f"Scintillation Index "+ (r'$\sigma^2_{I} $'), fontsize=16)
        plt.xticks(distance_list)
        plt.yticks(np.linspace(0, 1.2, 6))  # Adjust y-ticks based on max scintillation index
        plt.xlim(0,max(distance_list))
        plt.ylim(0,np.max(scintillation_index_list))

    plt.title("Scintillation Index vs Distance")
    plt.legend([r'$\sigma^2_{I} = $' +  y[0] + r'$\times 10^{'+y[1]+'}$' + r'$m^{-2/3}$' for y in [str(refractive_index_structure_parameter).split('e') for refractive_index_structure_parameter in refractive_index_structure_parameter_list]])
    plt.show()
