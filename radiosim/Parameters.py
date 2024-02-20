#
# Copyright (c) 2023 Gonzalo J. Carracedo <BatchDrake@gmail.com>
#
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import pathlib
import numpy as np
from .InterpolatedSpectrum      import InterpolatedSpectrum
from .InterpolatedPowerSpectrum import InterpolatedPowerSpectrum
from .InterpolatedResponse      import InterpolatedResponse
from .BlackBodySpectrum         import BlackBodySpectrum
from .CompoundResponse          import CompoundResponse
from .AllPassResponse           import AllPassResponse
from .AllStopResponse           import AllStopResponse
from .LineSpectrum              import LineSpectrum
from .SkyResponse               import SkyResponse
from .InstrumentPartResponse    import InstrumentPartResponse, DEFAULT_DUST_EMI, DEFAULT_MIN_DUST

RADIOSIM_RELATIVE_DATA_DIR = '../data'
RADIOSIM_USE_HSIM_EMIS     = False

HARMONI_FINEST_SPAXEL_SIZE = 4       # mas
HARMONI_PIXEL_SIZE         = 15e-6   # m
HARMONI_INST_FNUM          = 17.37
HARMONI_TEL_FNUM           = 17.75

HARMONI_PX_PER_SP_ALONG    = 1       # From: HRM-00190
HARMONI_PX_PER_SP_ACROSS   = 2       # From: HRM-00190
HARMONI_PX_AREA            = HARMONI_PIXEL_SIZE * HARMONI_PIXEL_SIZE

HARMONI_AMBIENT_TEMP       = +15 + 273.15 # K
HARMONI_COOL_TEMP          = +2  + 273.15 # K
HARMONI_CRYO_TEMP          = +130.        # K
HARMONI_CRYO_DUST_TEMP     = HARMONI_CRYO_TEMP + 50.
HARMONI_CRYO_TRAP_TEMP     = HARMONI_CRYO_TEMP + 50.

# Dust properties
HARMONI_GRAY_DUST_EMISSIVITY = 0.5   # Gray
HARMONI_COLD_TRAP_EMISSIVITY = 1     # Coal black

HARMONI_MIN_DUST_FRAC        = 5e-3
HARMONI_DEFAULT_DUST_FRAC    = 1e-1
HARMONI_AR_COATING_FRAC      = 1e-2  # 1% AR coating in each surface


class Parameters():
    substrate   = "Suprasil3001_50mm_Emissivity.txt"
    mirror      = "QuantumFS500_Emissivity.txt"
    edust       = HARMONI_COLD_TRAP_EMISSIVITY       # Grey Dust covering on some optics
    mindustfrac = HARMONI_MIN_DUST_FRAC     # 0.5% dust on optical surfaces - won't be perfectly clean

    def __init__(self):
        self.stages      = {}
        self.lamps       = {}
        self.filters     = {}
        self.fibers      = {}
        self.is_coatings = {}
        self.equalizers  = {}
        self.gratings    = {}
        self.scales      = {}
        self.parts       = {}
        self.temps       = {} # Tuple containing a value and a list

        self.finest_spaxel_size_mas = HARMONI_FINEST_SPAXEL_SIZE
        self.pixel_size             = HARMONI_PIXEL_SIZE
        self.unobscured_aperture    = np.pi * (37 * .5) ** 2
        self.obscured_aperture      = 980.

        self.QE_vis =  InterpolatedResponse(
                Parameters.resolve_data_file('Psyche_CCD231-84_ESO_measured_QE.txt'),
                scale = 1e-2)
        self.QE_nir =  InterpolatedResponse(
                Parameters.resolve_data_file('H4RG_QE_design.txt'),
                scale = 1e-2)
        self.sky = SkyResponse(
                Parameters.resolve_data_file('armazones_sky.txt.gz'),
                airmass_list = [1.1, 1.3, 1.5, 2.0])
        self.sky.set_label('Sky at cerro Armazones')

        self.recalc_obscurations()

        # Temperatures
        self.define_temperature('TTel',          'Telescope',            HARMONI_AMBIENT_TEMP)
        self.define_temperature('TCal',          'Calibration module',   HARMONI_AMBIENT_TEMP)
        self.define_temperature('TCool',         'Cool zone',            HARMONI_COOL_TEMP)
        self.define_temperature('TCryo',         'Cryostat',             HARMONI_CRYO_TEMP)
        self.define_temperature('TCryoDust',     'Cryostat inner dust',  HARMONI_CRYO_DUST_TEMP)
        self.define_temperature('TCryoTrap',     'Cryostat cold traps',  HARMONI_CRYO_TRAP_TEMP)
        self.define_temperature('TCryoMech',     'Cryostat mechanisms',  HARMONI_CRYO_TEMP)
        self.define_temperature('TTrap',         'Cold traps',           HARMONI_COOL_TEMP)
        self.define_temperature('Touter_window', 'Outer window',         HARMONI_AMBIENT_TEMP - 0.2 * (HARMONI_AMBIENT_TEMP - HARMONI_COOL_TEMP))
        self.define_temperature('Tinner_window', 'Inner window',         HARMONI_COOL_TEMP - 0.2 * (HARMONI_AMBIENT_TEMP - HARMONI_COOL_TEMP))

        # Instrument parts
        dustfrac  = HARMONI_DEFAULT_DUST_FRAC
        dustfrac  = max(self.mindustfrac, dustfrac)

        ecoldtrap = HARMONI_COLD_TRAP_EMISSIVITY
        rwindow   = HARMONI_AR_COATING_FRAC

        # Telescope mirror is treated as a single mirror
        self.load_part("M1-M5", 'TTel', area_scaling=False, n_mirrors=1, t_mirror="ELT_mirror_reflectivity.txt")
        self.load_part("Offner", 'TTel', area_scaling=False, n_mirrors=4)

        self.load_part("LTAO dichroic", 'TTel', n_lenses=1, emis_lens="LTAO_0.6_dichroic.txt", dust_lens=2.*dustfrac)
        self.load_part("AO cold trap", 'TTrap', n_mirrors=1, emis_mirror=0., dust_mirror=0.03, emis_dust=ecoldtrap)
        self.load_part("Outer window", 'Touter_window', n_lenses=1, emis_scaling=0.5, dust_lens=dustfrac + self.mindustfrac)
        self.load_part("Inner window", 'Tinner_window', n_lenses=1, emis_scaling=0.5, dust_lens=2.*self.mindustfrac)
        self.load_part("Window reflected", 'TTrap', n_mirrors=1, emis_mirror=0., dust_mirror=2.*0.8*2.0*rwindow, emis_dust=ecoldtrap)
        self.load_part("FPRS", 'TCool', area_scaling=False, n_mirrors=4)
        self.load_part("SCAO dichroic", 'TCool', n_lenses=1, emis_lens="SCAO_0.8_dichroic.txt", dust_lens=2.*dustfrac)
        self.load_part("Cryo window", 'TCool', n_lenses=1, emis_scaling=0.4, dust_lens=self.mindustfrac)
        self.load_part("Cryo window inner dust", 'TCryoDust', n_mirrors=1, emis_mirror=0., dust_mirror=self.mindustfrac)
        self.load_part("Cryo window cold trap", 'TCryoTrap', n_mirrors=1, emis_mirror=0., dust_mirror=2.0*rwindow, emis_dust=ecoldtrap)

	    # Cryostat
        self.load_part("Pre-optics+IFU+Spectrograph", 'TCryoMech', n_lenses=8, n_mirrors=19)

        self.is_input_types = {
            'spect_PSD'   : ('Power spectral density', 'Wν⁻¹')
        }

        self.is_spect_types = {
            'spect_I'   : ('Spectral radiance',       'Wm⁻²sr⁻¹ν⁻¹'),
            'spect_E'   : ('Spectral irradiance',     'Wm⁻²ν⁻¹'),
            'photon_I'  : ('Photon radiance',         'm⁻²s⁻¹ν⁻¹arcsec⁻²'),
            'photon_F'  : ('Photon irradiance',       'm⁻²s⁻¹ν⁻¹'),
            'dphotondt' : ('Photon rate per pixel',   's⁻¹'),
        }

        self.ccd_spect_types = {
            'spect_I'   : ('Spectral radiance',       'Wm⁻²sr⁻¹ν⁻¹'),
            'spect_E'   : ('Spectral irradiance',     'Wm⁻²ν⁻¹'),
            'photon_I'  : ('Photon radiance',         'm⁻²s⁻¹ν⁻¹arcsec⁻²'),
            'photon_F'  : ('Photon irradiance',       'm⁻²s⁻¹ν⁻¹'),
            'dphotondt' : ('Photon rate per pixel',   's⁻¹'),
            'dedt_Px'   : ('Electron rate per pixel', 'e⁻s⁻¹'),
            'electrons' : ('Electrons per pixel',     'e⁻'),
            'counts'    : ('Counts per pixel',        'adu')
        }

        self.transmission_types = {}
        self.spect_types = {
            'is_in'        : ('IS light input', self.is_input_types),
            'is_out'       : ('Input spectra (IS or telescope)', self.is_spect_types),
            'detector'     : ('Detector', self.ccd_spect_types),
            'transmission' : ('Total transmission spectrum', self.transmission_types),
        }

    def register_transmissions(self):
        self.transmission_types['total_response'] = ('Total instrument response', 'fraction')
        self.transmission_types['sky'] = ('Sky response', 'fraction')

        for part in self.get_part_names():
            self.transmission_types['part:' + part] = (self.get_part(part), 'fraction')
        for filter in self.get_filter_names():
            self.transmission_types['filter:' + filter] = (self.get_filter(filter), 'fraction')
        for eq in self.get_equalizer_names():
            self.transmission_types['eq:' + eq] = (self.get_equalizer(eq), 'fraction')
    
    def get_transmission(self, name):
        if name in self.transmission_types:
            return self.transmission_types[name][0]
        return None

    def get_QE(self, grating):
        if grating == 'VIS':
            return self.QE_vis
        else:
            return self.QE_nir

    def set_telescope_parameters(
        self,
        diameter: float,
        area: float):

        self.unobscured_aperture    = np.pi * (diameter * .5) ** 2
        self.obscured_aperture      = area
        
        # Automatically updates the instrument parts
        self.recalc_obscurations()

    def recalc_obscurations(self):
        self.area_scaling = self.unobscured_aperture / self.obscured_aperture

        for part in self.parts.values():
            if part[1]: # Area scaling flag
                part[0].set_area_scaling(self.area_scaling)
            
    def define_temperature(self, temp, desc, default):
        self.temps[temp] = [default, desc, []]
    
    def set_temperature(self, temp, value):
        if not temp in self.temps:
            raise RuntimeError(fr"No such temperature `{temp}'")
        
        self.temps[temp][0] = value

        for part in self.temps[temp][2]:
            part.set_temperature(value)
    
    def get_temperature(self, temp):
        if not temp in self.temps:
            raise RuntimeError(fr"No such temperature `{temp}'")
        
        return self.temps[temp][0]
    
    def get_temperature_desc(self, temp):
        if not temp in self.temps:
            raise RuntimeError(fr"No such temperature `{temp}'")
        
        return self.temps[temp][1]

    def link_part_to_temperature(self, part, temp):
        if not temp in self.temps:
            raise RuntimeError(fr"No such temperature `{temp}'")
        
        self.temps[temp][2].append(part)
        part.set_temperature(self.get_temperature(temp))

    def get_temperatures(self):
        return list(self.temps.keys())
    
    def load_coating(self, key, desc, file):
        self.load_stage(key, file)
        self.is_coatings[key] = desc
    
    def load_black_coating(self, key, desc):
        self.load_black_stage(key)
        self.is_coatings[key] = desc
    
    def get_coatings(self):
        return self.is_coatings.keys()
    
    def get_coating_desc(self, key):
        return self.is_coatings[key]

    @staticmethod
    def resolve_data_file(path):
        if len(path) == 0:
            raise RuntimeError('Path is empty')
        
        if path[0] == '/' or path[0] == '.':
            return path

        dir = str(pathlib.Path(__file__).parent.resolve())

        return dir + fr'/{RADIOSIM_RELATIVE_DATA_DIR}/' + path
    
    def get_spectrum_types(self):
        return self.spect_types.keys()

    def get_spectrum_type_desc(self, type):
        if type not in self.spect_types.keys():
            return None
        return self.spect_types[type][0]

    def get_spectrums_for_type(self, type):
        if type not in self.spect_types.keys():
            return None
        return self.spect_types[type][1].keys()

    def get_spectrum_desc_for_type(self, typ, spec):
        if typ not in self.spect_types.keys():
            return None

        if spec not in self.get_spectrums_for_type(typ):
            return None

        spectrum = self.spect_types[typ][1][spec]
        if type(spectrum[0]) is str:
            return spectrum
        return (spectrum[0].get_label(), spectrum[1])

    def load_part(
      self,
      name: str,
      temp_name: str,
      area_scaling: bool    = True,
      n_mirrors: int        = 0,
      n_lenses: int         = 0,
      dust_lens: float      = 0.,
      dust_mirror: float    = DEFAULT_MIN_DUST,
      global_scaling: float = 1.,
      emis_scaling: float   = 1.,
      emis_mirror           = "QuantumFS500_Emissivity.txt",
      emis_lens             = "Suprasil3001_50mm_Emissivity.txt",
      t_mirror              = None,
      t_lens                = None,
      emis_dust: float      = DEFAULT_DUST_EMI):
        # If they are defined as strings: resolve path
        if type(emis_mirror) is str:
            emis_mirror = self.resolve_data_file(emis_mirror)

        if type(emis_lens) is str:
            emis_lens   = self.resolve_data_file(emis_lens)

        if type(t_mirror) is str:
            t_mirror    = self.resolve_data_file(t_mirror)

        if type(t_lens) is str:
            t_lens      = self.resolve_data_file(t_lens)

        temp = self.get_temperature(temp_name)
        
        part = InstrumentPartResponse(
            temp,
            self.area_scaling if area_scaling else 1,
            n_mirrors,
            n_lenses,
            dust_lens,
            dust_mirror,
            global_scaling,
            emis_scaling,
            emis_mirror,
            emis_lens,
            t_mirror,
            t_lens,
            emis_dust)
        
        part.set_label(name)
        self.link_part_to_temperature(part, temp_name)
        self.parts[name] = (part, area_scaling)

    def get_part(self, name):
        if name not in self.parts:
            raise RuntimeError('No such instrument part')
        
        return self.parts[name][0]
    
    def get_part_names(self):
        return list(self.parts.keys())

    def load_lamp(self, name, path = None, rating = None, desc = None, response = None, role = "cal", psd = False, SI = False):
        spectclass = InterpolatedPowerSpectrum if psd else InterpolatedSpectrum 
        if path is not None:
            full_path = self.resolve_data_file(path)
            spectrum = spectclass(full_path, SI = SI)
        else:
            spectrum = spectclass(response = response, SI = SI)

        if rating is not None:
            spectrum.set_nominal_power_rating(rating)
        
        if not psd:
            spectrum.set_role(role)
        self.lamps[name] = (spectrum, desc)

    def add_line_lamp(self, name, F, desc = None, T = 1000, rating = None, frel_c = 0, role = "cal"):
        spectrum = LineSpectrum(F, T, frel_c)

        if rating is not None:
            spectrum.set_nominal_power_rating(rating)
        
        spectrum.set_role(role)
        self.lamps[name] = (spectrum, desc)
        
        return spectrum

    def load_black_body_lamp(self, name, T, rating = None, desc = None, role = "cal"):
        spectrum = BlackBodySpectrum(T)

        if rating is not None:
            spectrum.set_nominal_power_rating(rating)
        
        spectrum.set_role(role)
        self.lamps[name] = (spectrum, desc)

    def get_lamp(self, name):
        if name not in self.lamps:
            return None

        return self.lamps[name][0]
    
    def get_lamp_desc(self, name):
        if name not in self.lamps:
            return None

        return self.lamps[name][1]

    def get_lamp_params(self, name):
        if name not in self.lamps:
            return None

        return self.lamps[name]

    def get_lamp_names(self):
        return list(self.lamps.keys())
    
    def load_stage(self, name, path):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path)
        response.set_label(name)
        self.stages[name] = response

    def load_black_stage(self, name):
        response = AllStopResponse()
        response.set_label(name)
        self.stages[name] = response


    def get_stage(self, name):
        if name not in self.stages:
            raise RuntimeError('No such stage filter')
        
        return self.stages[name]
    
    def get_stage_names(self):
        return list(self.stages.keys())
    
    def load_filter(self, name, path, emissivity = False):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path, emissivity = emissivity)
        response.set_label('Filter: ' + name)
        self.link_part_to_temperature(response, 'TCryoMech')
        self.filters[name] = response

    def get_filter(self, name):
        if name not in self.filters:
            return None
        return self.filters[name]
    
    def get_filter_names(self):
        return list(self.filters.keys())

    def load_fiber(self, name, path):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path)
        response.set_background(False)
        response.set_label('Fiber: ' + name)
        self.fibers[name] = response

    def load_transparent_fiber(self, name):
        response = AllPassResponse()
        response.set_label(name)
        self.fibers[name] = response

    def get_fiber(self, name):
        if name not in self.fibers:
            return None
        return self.fibers[name]
    
    def get_fiber_names(self):
        return list(self.fibers.keys())

    def load_equalizer(self, name, path):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path)
        response.set_label('Equalizer: ' + name)
        self.link_part_to_temperature(response, 'TCal')
        self.equalizers[name] = response
        return self.equalizers[name]
    
    def get_equalizer(self, name):
        if name not in self.equalizers:
            return None
        return self.equalizers[name]
    
    def get_equalizer_names(self):
        return list(self.equalizers.keys())
    
    def register_grating(self, grating, filter, equalizer, R, lambda_min, lambda_max):
        filter_obj = self.get_filter(filter)
        if filter_obj is None:
            raise RuntimeError(fr'No such passband filter: {filter}')
        
        eq_obj = self.get_equalizer(equalizer)
        if eq_obj is None:
            raise RuntimeError(fr'No such equalizer filter: {equalizer}')

        self.gratings[grating] = (filter_obj, eq_obj, R, lambda_min, lambda_max, filter)
    
    def get_grating(self, name):
        if name not in self.gratings:
            return None

        return self.gratings[name]

    def get_grating_names(self):
        return list(self.gratings.keys())
    
    def register_scale(self, scale, spaxel_x, spaxel_y):
        if type(scale) is not tuple or len(scale) != 2:
            raise RuntimeError(fr'Scales must be defined as 2-tuples')
        
        self.scales[scale] = (spaxel_x, spaxel_y)

    def get_sky_transmission(self):
        return self.sky
    
    def get_scale(self, scale):
        if scale not in self.scales:
            return None
        return self.scales[scale]
    
    def get_scales(self):
        return self.scales.keys()

    def get_ao_mode_names(self):
        return ['NOAO', 'SCAO', 'LTAO']
    
    def make_response(self, config: dict):
        grating = config['grating']
        ao      = config['ao']
        cal     = config['cal']
        airmass = config['airmass']

        fD_tel  = config['fD_tel'] if 'fD_tel' in config else None
        fD_cal  = config['fD_cal'] if 'fD_cal' in config else None
        fD_ins  = config['fD_ins'] if 'fD_ins' in config else None
        fD_fix  = config['fD_fix'] if 'fD_fix' in config else None

        response = CompoundResponse()
        response.set_label('Instrument response')
        ao       = ao.upper()
        grating  = grating.upper()
        aomodes  = ['LTAO', 'SCAO', 'NOAO']

        gr_obj = self.get_grating(grating)
        if gr_obj is None:
            raise Exception(fr'Undefined grating: {grating}')
    
        if cal:
            # Push equalizer
            response.push_back(gr_obj[1], fD_cal)
            response.push_back(self.get_part("Offner"), fD_cal)
        else:
            # Push telescope
            self.sky.set_airmass(airmass)

            response.push_back(self.sky, fD_tel)
            response.push_back(self.get_part("M1-M5"), fD_tel)
        
        if not ao in aomodes:
            raise Exception("Undefined AO configuration " + ao)

        # Put LTAO dichroic
        if ao == 'LTAO':
            response.push_back(self.get_part('LTAO dichroic'), fD_ins)
            response.push_back(self.get_part('AO cold trap'), fD_ins)
        
        # HARMONI's window has a hot and a cold side
        response.push_back(self.get_part('Outer window'), fD_ins)
        response.push_back(self.get_part('Inner window'), fD_ins)

        # We are already in the inside
        response.push_back(self.get_part('Window reflected'), fD_ins)

        # FPRS
        response.push_back(self.get_part('FPRS'), fD_tel)

        # Put SCAO dichroic
        if ao == 'SCAO':
            response.push_back(self.get_part('SCAO dichroic'), fD_ins)
        
        # Cryostat window has several parts too
        response.push_back(self.get_part('Cryo window'), fD_ins)
        response.push_back(self.get_part('Cryo window inner dust'), fD_ins)
        response.push_back(self.get_part('Cryo window cold trap'), fD_ins)

        # Cryostat
        response.push_back(self.get_part('Pre-optics+IFU+Spectrograph'), fD_fix)

        # Push grating
        response.push_back(gr_obj[0], fD_fix)

        return response

    def add_arc_lamps(self):
        self.load_lamp('Argon arc lamp', path = 'ar-psd.csv', psd = True)
        self.load_lamp('Argon arc lamp (fiber output)', path = 'ar-psd-atfiber.csv', psd = True)
        self.load_lamp('Neon arc lamp',  path = 'ne-psd.csv', psd = True)

    def load_defaults(self):
        # Load coatings
        self.load_coating('SPECTRALON',   "LabSphere's Spectralon®",   't-spectralon.csv')
        self.load_coating('SPECTRAFLECT', "LabSphere's Spectraflect®", 't-spectraflect.csv')
        self.load_coating('DIFFGOLD',     "LabSphere's Infragold®",    't-diffuse-gold.csv')
        self.load_black_coating('BLACK',  "Perfect black")

        # Load lamps
        self.add_arc_lamps()
        self.load_black_body_lamp('Black body', 3422, rating = 100)
        
        # Load fibers for lamps
        self.load_transparent_fiber("No fiber")
        self.load_fiber("Thorlabs® M35L01", "THORLABS_M35L01.csv")
        
        # Load passband filters for the different gratings
        if RADIOSIM_USE_HSIM_EMIS:
            self.load_filter("H (high)",  "H-high_grating.txt", True)
            self.load_filter("H",         "H_grating.txt", True)
            self.load_filter("HK",        "H+K_grating.txt", True)
            self.load_filter("IZ",        "Iz_grating.txt", True)
            self.load_filter("IZJ",       "Iz+J_grating.txt", True)
            self.load_filter("J",         "J_grating.txt", True)
            self.load_filter("K",         "K_grating.txt", True)
            self.load_filter("K (long)",  "K-long_grating.txt", True)
            self.load_filter("K (short)", "K-short_grating.txt", True)
            self.load_filter("VIS",       "V+R_grating.txt", True)
            self.load_filter("Z",         "z-high_grating.txt", True)
        else:
            self.load_filter("H (high)",  "t-h-high.csv")
            self.load_filter("H",         "t-h.csv")
            self.load_filter("HK",        "t-hk.csv")
            self.load_filter("IZ",        "t-iz.csv")
            self.load_filter("IZJ",       "t-izj.csv")
            self.load_filter("J",         "t-j.csv")
            self.load_filter("K",         "t-k.csv")
            self.load_filter("K (long)",  "t-k-long.csv")
            self.load_filter("K (short)", "t-k-short.csv")
            self.load_filter("VIS",       "t-vis.csv")
            self.load_filter("Z",         "t-z.csv")

        # Load equalizers
        self.load_equalizer("VIS",    "f-vis.csv")
        self.load_equalizer("LR1",    "f-lr1.csv")
        self.load_equalizer("LR2",    "f-lr2.csv")
        self.load_equalizer("MR1",    "f-mr1.csv")
        self.load_equalizer("MR2",    "f-mr2.csv")
        self.load_equalizer("MR3",    "f-mr3.csv")
        self.load_equalizer("MR4",    "f-mr4.csv")
        self.load_equalizer("HR1",    "f-hr1.csv")
        self.load_equalizer("HR2",    "f-hr2.csv")
        self.load_equalizer("HR3",    "f-hr3.csv")
        self.load_equalizer("HR4",    "f-hr4.csv")
        
        # Register available gratings
        self.register_grating("VIS", "VIS", "VIS", 3100, 0.462e-6, 0.812e-6)
        
        self.register_grating("LR1", "IZJ", "LR1", 3355, 0.811e-6, 1.369e-6)
        self.register_grating("LR2", "HK",  "LR2", 3355, 1.450e-6, 2.450e-6)
        
        self.register_grating("MR1", "IZ",  "MR1", 7104, 0.830e-6, 1.050e-6)
        self.register_grating("MR2", "J",   "MR2", 7104, 1.046e-6, 1.324e-6)
        self.register_grating("MR3", "H" ,  "MR3", 7104, 1.435e-6, 1.815e-6)
        self.register_grating("MR4", "K" ,  "MR4", 7104, 1.951e-6, 2.469e-6)
        
        self.register_grating("HR1", "Z",         "HR1", 17385, 0.827e-6, 0.903e-6)
        self.register_grating("HR2", "H (high)",  "HR2", 17385, 1.538e-6, 1.678e-6)
        self.register_grating("HR3", "K (short)", "HR3", 17385, 2.017e-6, 2.201e-6)
        self.register_grating("HR4", "K (long)",  "HR4", 17385, 2.199e-6, 2.399e-6)

        # Register scales
        self.register_scale((4, 4), HARMONI_FINEST_SPAXEL_SIZE, HARMONI_FINEST_SPAXEL_SIZE)
        self.register_scale((10, 10), 10, 10)
        self.register_scale((20, 20), 20, 20)
        self.register_scale((60, 30), 60, 30)

        self.register_transmissions()
        
