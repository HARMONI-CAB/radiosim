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
from .InterpolatedSpectrum import InterpolatedSpectrum
from .InterpolatedResponse import InterpolatedResponse
from .BlackBodySpectrum    import BlackBodySpectrum
from .CompoundResponse     import CompoundResponse
from .LineSpectrum         import LineSpectrum

RADIOSIM_RELATIVE_DATA_DIR = '../data'
HARMONI_FINEST_SPAXEL_SIZE = 4.14    # mas
HARMONI_PIXEL_SIZE         = 13.3e-6 # m
HARMONI_PX_PER_SP_ALONG    = 1       # From: HRM-00190
HARMONI_PX_PER_SP_ACROSS   = 2       # From: HRM-00190
HARMONI_PX_AREA            = HARMONI_PIXEL_SIZE * HARMONI_PIXEL_SIZE

class Parameters():
    def __init__(self):
        self.stages      = {}
        self.lamps       = {}
        self.filters     = {}
        self.is_coatings = {}
        self.equalizers  = {}
        self.gratings    = {}
        self.scales      = {}

        self.finest_spaxel_size_mas = HARMONI_FINEST_SPAXEL_SIZE
        self.pixel_size             = HARMONI_PIXEL_SIZE

        self.load_coating('SPECTRALON',   "LabSphere's Spectralon®",   't-spectralon.csv')
        self.load_coating('SPECTRAFLECT', "LabSphere's Spectraflect®", 't-spectraflect.csv')
        self.load_coating('DIFFGOLD',     "LabSphere's Infragold®",    't-diffuse-gold.csv')

        self.load_stage('Cryostat',      't-cryostat.csv')
        self.load_stage('Detector',      't-detector.csv')
        
        self.load_stage('Fibers*',       't-fprs.csv')
        self.load_stage('Offner',        't-fprs.csv')

        self.load_stage('FPRS',          't-fprs.csv')
        self.load_stage('LTAO Dichroic', 't-ltao-d.csv')
        self.load_stage('SCAO Dichroic', 't-scao-d.csv')
        self.load_stage('Misalignments', 't-misalignment.csv')
        self.load_stage('Preoptics',     't-preoptics.csv')
        self.load_stage('Spectrograph',  't-spectrograph.csv')
        self.load_stage('IFU',           't-ifu.csv')

        self.is_spect_types = {
            'spect_E'   : ('Spectral irradiance',     'Wm⁻²ν⁻¹'),
            'photon_F'  : ('Specific photon flux',    'm⁻²s⁻¹ν⁻¹'),
        }

        self.ccd_spect_types = {
            'spect_E'   : ('Spectral irradiance',     'Wm⁻²ν⁻¹'),
            'photon_F'  : ('Specific photon flux',    'm⁻²s⁻¹ν⁻¹'),
            'dedt_Px'   : ('Electron rate per pixel', 'e⁻s⁻¹'),
            'electrons' : ('Electrons per pixel',     'e⁻'),
            'counts'    : ('Counts per pixel',        'adu')
        }

        self.transmission_types = {}

        for stage in self.get_stage_names():
            self.transmission_types[stage] = (stage, 'fraction')
        
        self.spect_types = {
            'is_out'       : ('Input spectra (IS or telescope)', self.is_spect_types),
            'detector'     : ('Detector', self.ccd_spect_types),
            'transmission' : ('Total transmission spectrum', self.transmission_types),
        }

    def load_coating(self, key, desc, file):
        self.load_stage(key, file)
        self.is_coatings[key] = desc
    
    def get_coatings(self):
        return self.is_coatings.keys()
    
    def get_coating_desc(self, key):
        return self.is_coatings[key]

    def resolve_data_file(self, path):
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

    def get_spectrum_desc_for_type(self, type, spec):
        if type not in self.spect_types.keys():
            return None

        if spec not in self.get_spectrums_for_type(type):
            return None

        return self.spect_types[type][1][spec]
    
    def load_lamp(self, name, path = None, rating = None, desc = None, response = None, role = "cal", SI = False):
        if path is not None:
            full_path = self.resolve_data_file(path)
            spectrum = InterpolatedSpectrum(full_path)
        else:
            spectrum = InterpolatedSpectrum(response = response, SI = SI)

        if rating is not None:
            spectrum.set_nominal_power_rating(rating)
        
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

    def get_stage(self, name):
        if name not in self.stages:
            raise RuntimeError('No such stage filter')
        
        return self.stages[name]
    
    def get_stage_names(self):
        return list(self.stages.keys())
    
    def load_filter(self, name, path):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path)
        response.set_label('Filter: ' + name)
        self.filters[name] = response

    def get_filter(self, name):
        if name not in self.filters:
            return None
        return self.filters[name]
    
    def get_filter_names(self):
        return list(self.filters.keys())
    
    def load_equalizer(self, name, path):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path)
        response.set_label('Equalizer: ' + name)
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

    def get_scale(self, scale):
        if scale not in self.scales:
            return None
        return self.scales[scale]
    
    def get_scales(self):
        return self.scales.keys()

    def get_ao_mode_names(self):
        return ['NOAO', 'SCAO', 'LTAO']
    
    def make_response(self, grating, ao, cal):
        response = CompoundResponse()
        response.set_label('Instrument response')
        ao       = ao.upper()
        grating  = grating.upper()
        
        if ao == "SCAO":
            response.push_back(self.get_stage("SCAO Dichroic"))
        elif ao == "LTAO":
            response.push_back(self.get_stage("LTAO Dichroic"))
        elif ao != "NOAO":
            raise Exception("Undefined AO configuration " + ao)
        
        if cal:
            response.push_back(self.get_stage("Fibers*"))
            response.push_back(self.get_stage("Offner"))
        
        response.push_back(self.get_stage("FPRS"))
        response.push_back(self.get_stage("Cryostat"))
        response.push_back(self.get_stage("Preoptics"))
        response.push_back(self.get_stage("IFU"))
        response.push_back(self.get_stage("Spectrograph"))

        gr_obj = self.get_grating(grating)
        if gr_obj is None:
            raise Exception(fr'Undefined grating: {grating}')
        
        # Push passband filter
        response.push_back(gr_obj[0])

        # Push equalizer
        response.push_back(gr_obj[1])

        response.push_back(self.get_stage("Misalignments"))
        response.push_back(self.get_stage("Detector"))

        return response

    def add_arc_lamps(self):
        # The flux of this lamps is derived from the typical spectra of
        # Oriel Instrument's calibration lamps. We see that they usually
        # peak at 10 µW / (cm² nm) = 1e8 W / (m² m). 
        #
        # We arbitratly set the line width to 1 nm until we have a better
        # approximation.

        arbitrary_line_width = 1e-9 # m
        arbitrary_peak_flux_density  = 1e8 # W / (m² m)
        pF = arbitrary_peak_flux_density * arbitrary_line_width
        fc = 1e-1 # Dimensionless

        Hg_lamp = self.add_line_lamp("Hg", pF, "Mercury arc lamp", frel_c = fc)
        Ne_lamp = self.add_line_lamp("Ne", pF, "Neon arc lamp", frel_c = fc)
        Ar_lamp = self.add_line_lamp("Ar", pF, "Argon arc lamp", frel_c = fc)
        Kr_lamp = self.add_line_lamp("Kr", pF, "Kripton arc lamp", frel_c = fc)
        Xe_lamp = self.add_line_lamp("Xe", pF, "Xenon arc lamp", frel_c = fc)

        Ar_lamp.add_line(0.472819,     23442, 40)
        Ar_lamp.add_line(0.473723,      1000, 40)
        Ar_lamp.add_line(0.476620,      2344, 40)
        Ar_lamp.add_line(0.480736,      1820, 40)
        Ar_lamp.add_line(0.488123,      2239, 40)
        Ar_lamp.add_line(0.611662,       537, 40)
        Ar_lamp.add_line(0.617399,       407, 40)
        Ar_lamp.add_line(0.664553,       269, 40)
        Ar_lamp.add_line(0.763721,     25000, 40)
        Ar_lamp.add_line(0.795036,     20000, 40)
        Ar_lamp.add_line(0.801699,     25000, 40)
        Ar_lamp.add_line(0.810592,     20000, 40)
        Ar_lamp.add_line(0.811754,     35000, 40)
        Ar_lamp.add_line(0.826679,     10000, 40)
        Ar_lamp.add_line(0.841052,     15000, 40)
        Ar_lamp.add_line(0.842696,     20000, 40)
        Ar_lamp.add_line(0.852378,     15000, 40)
        Ar_lamp.add_line(0.912547,     35000, 40)
        Ar_lamp.add_line(1.067649,       200, 40)
        Ar_lamp.add_line(1.167190,       200, 40)
        Ar_lamp.add_line(1.211564,       200, 40)
        Ar_lamp.add_line(1.214306,        50, 40)
        Ar_lamp.add_line(1.234677,        50, 40)
        Ar_lamp.add_line(1.240622,       200, 40)
        Ar_lamp.add_line(1.244272,       200, 40)
        Ar_lamp.add_line(1.245953,       100, 40)
        Ar_lamp.add_line(1.249108,       200, 40)
        Ar_lamp.add_line(1.270576,       150, 40)
        Ar_lamp.add_line(1.280624,       200, 40)
        Ar_lamp.add_line(1.293673,        50, 40)
        Ar_lamp.add_line(1.296020,       500, 40)
        Ar_lamp.add_line(1.301182,       200, 40)
        Ar_lamp.add_line(1.323452,       100, 40)
        Ar_lamp.add_line(1.327627,       500, 40)
        Ar_lamp.add_line(1.331685,      1000, 40)
        Ar_lamp.add_line(1.350788,      1000, 40)
        Ar_lamp.add_line(1.360305,        30, 40)
        Ar_lamp.add_line(1.362638,       400, 40)
        Ar_lamp.add_line(1.368229,       200, 40)
        Ar_lamp.add_line(1.382950,        10, 40)
        Ar_lamp.add_line(1.409749,       200, 40)
        Ar_lamp.add_line(1.505061,       100, 40)
        Ar_lamp.add_line(1.599386,        30, 40)
        Ar_lamp.add_line(1.694521,       500, 40)
        Hg_lamp.add_line(0.546227,      6000, 200.59)
        Hg_lamp.add_line(0.577121,      1000, 200.59)
        Hg_lamp.add_line(0.579228,       900, 200.59)
        Hg_lamp.add_line(1.014253,      1600, 200.59)
        Hg_lamp.add_line(1.129020,      1000, 200.59)
        Hg_lamp.add_line(1.213180,         5, 200.59)
        Hg_lamp.add_line(1.321356,       400, 200.59)
        Hg_lamp.add_line(1.343024,       400, 200.59)
        Hg_lamp.add_line(1.347206,       130, 200.59)
        Hg_lamp.add_line(1.350927,       200, 200.59)
        Hg_lamp.add_line(1.357392,       200, 200.59)
        Hg_lamp.add_line(1.367725,       300, 200.59)
        Hg_lamp.add_line(1.395436,       200, 200.59)
        Hg_lamp.add_line(1.530000,       600, 200.59)
        Kr_lamp.add_line(0.760364,  27320000, 83.8)
        Kr_lamp.add_line(0.785698,  20410000, 83.8)
        Kr_lamp.add_line(0.793078,   7700000, 83.8)
        Kr_lamp.add_line(0.806172,  15830000, 83.8)
        Kr_lamp.add_line(0.810625,   6520000, 83.8)
        Kr_lamp.add_line(0.810659,   8960000, 83.8)
        Kr_lamp.add_line(0.811513,  36100000, 83.8)
        Kr_lamp.add_line(0.819231,   8940000, 83.8)
        Kr_lamp.add_line(0.826551,  34160000, 83.8)
        Kr_lamp.add_line(0.828333,  14180000, 83.8)
        Kr_lamp.add_line(0.830039,  29310000, 83.8)
        Kr_lamp.add_line(0.851121,  18110000, 83.8)
        Kr_lamp.add_line(0.877916,  22170000, 83.8)
        Kr_lamp.add_line(0.893114,  22890000, 83.8)
        Kr_lamp.add_line(1.182261,   8110000, 83.8)
        Kr_lamp.add_line(1.318101,   4900000, 83.8)
        Kr_lamp.add_line(1.324431,   3180000, 83.8)
        Kr_lamp.add_line(1.362614,   4970000, 83.8)
        Kr_lamp.add_line(1.363795,  10300000, 83.8)
        Kr_lamp.add_line(1.383666,   3120000, 83.8)
        Kr_lamp.add_line(1.388665,  10600000, 83.8)
        Kr_lamp.add_line(1.394281,  11000000, 83.8)
        Kr_lamp.add_line(1.443074,   9300000, 83.8)
        Kr_lamp.add_line(1.473847,   2810000, 83.8)
        Kr_lamp.add_line(1.524379,   3960000, 83.8)
        Kr_lamp.add_line(1.537624,   1470000, 83.8)
        Kr_lamp.add_line(1.678972,   6760000, 83.8)
        Kr_lamp.add_line(1.685810,   1300000, 83.8)
        Kr_lamp.add_line(1.689507,   7680000, 83.8)
        Kr_lamp.add_line(1.694044,   5770000, 83.8)
        Ne_lamp.add_line(0.609785,      3000, 20.18)
        Ne_lamp.add_line(0.614476,     10000, 20.18)
        Ne_lamp.add_line(0.633618,     10000, 20.18)
        Ne_lamp.add_line(0.638476,     10000, 20.18)
        Ne_lamp.add_line(0.640402,     20000, 20.18)
        Ne_lamp.add_line(0.650833,     15000, 20.18)
        Ne_lamp.add_line(0.668012,      5000, 20.18)
        Ne_lamp.add_line(0.693138,    100000, 20.18)
        Ne_lamp.add_line(0.703435,     85000, 20.18)
        Ne_lamp.add_line(0.749093,     32000, 20.18)
        Ne_lamp.add_line(0.753785,     28000, 20.18)
        Ne_lamp.add_line(0.813864,     17000, 20.18)
        Ne_lamp.add_line(0.830261,     29000, 20.18)
        Ne_lamp.add_line(0.837991,     76000, 20.18)
        Ne_lamp.add_line(0.842074,     26000, 20.18)
        Ne_lamp.add_line(0.849769,     69000, 20.18)
        Ne_lamp.add_line(0.859362,     41000, 20.18)
        Ne_lamp.add_line(0.863702,     35000, 20.18)
        Ne_lamp.add_line(0.865676,     64000, 20.18)
        Ne_lamp.add_line(0.868188,     13000, 20.18)
        Ne_lamp.add_line(0.868431,     15000, 20.18)
        Ne_lamp.add_line(0.877407,     10000, 20.18)
        Ne_lamp.add_line(0.878303,     57000, 20.18)
        Ne_lamp.add_line(0.878617,     43000, 20.18)
        Ne_lamp.add_line(0.885630,     27000, 20.18)
        Ne_lamp.add_line(0.886819,     15000, 20.18)
        Ne_lamp.add_line(0.915118,     12000, 20.18)
        Ne_lamp.add_line(1.056530,      8000, 20.18)
        Ne_lamp.add_line(1.114607,     26000, 20.18)
        Ne_lamp.add_line(1.118059,     49000, 20.18)
        Ne_lamp.add_line(1.152590,     33000, 20.18)
        Ne_lamp.add_line(1.152818,     17000, 20.18)
        Ne_lamp.add_line(1.153950,      9100, 20.18)
        Ne_lamp.add_line(1.177001,     15000, 20.18)
        Ne_lamp.add_line(1.206964,     23000, 20.18)
        Ne_lamp.add_line(1.499041,       530, 20.18)
        Ne_lamp.add_line(1.507829,       140, 20.18)
        Ne_lamp.add_line(1.514424,       350, 20.18)
        Ne_lamp.add_line(1.519508,       270, 20.18)
        Ne_lamp.add_line(1.535238,       160, 20.18)
        Ne_lamp.add_line(1.541180,       250, 20.18)
        Ne_lamp.add_line(2.104701,      2700, 20.18)
        Ne_lamp.add_line(2.171404,      2900, 20.18)
        Ne_lamp.add_line(2.225343,      1300, 20.18)
        Ne_lamp.add_line(2.243426,      1300, 20.18)
        Ne_lamp.add_line(2.247292,       540, 20.18)
        Ne_lamp.add_line(2.253653,      8500, 20.18)
        Ne_lamp.add_line(2.266797,      1300, 20.18)
        Ne_lamp.add_line(2.269396,       210, 20.18)
        Ne_lamp.add_line(2.310678,      2500, 20.18)
        Ne_lamp.add_line(2.326662,      3800, 20.18)
        Ne_lamp.add_line(2.337934,      5000, 20.18)
        Ne_lamp.add_line(2.357176,      3400, 20.18)
        Ne_lamp.add_line(2.364293,     17000, 20.18)
        Ne_lamp.add_line(2.370813,      1200, 20.18)
        Ne_lamp.add_line(2.371560,      5900, 20.18)
        Ne_lamp.add_line(2.391854,       170, 20.18)
        Ne_lamp.add_line(2.395793,     11000, 20.18)
        Ne_lamp.add_line(2.396296,      4600, 20.18)
        Ne_lamp.add_line(2.397837,       220, 20.18)
        Ne_lamp.add_line(2.398470,      6000, 20.18)
        Ne_lamp.add_line(2.409353,       200, 20.18)
        Ne_lamp.add_line(2.410515,      1100, 20.18)
        Ne_lamp.add_line(2.415649,       210, 20.18)
        Ne_lamp.add_line(2.416802,      2000, 20.18)
        Ne_lamp.add_line(2.425622,      2800, 20.18)
        Ne_lamp.add_line(2.437166,      7400, 20.18)
        Ne_lamp.add_line(2.437826,      3800, 20.18)
        Ne_lamp.add_line(2.439001,       360, 20.18)
        Ne_lamp.add_line(2.445453,      1900, 20.18)
        Ne_lamp.add_line(2.445978,       240, 20.18)
        Ne_lamp.add_line(2.446607,      3300, 20.18)
        Ne_lamp.add_line(2.447161,       370, 20.18)
        Xe_lamp.add_line(0.712156,       500, 131.3)
        Xe_lamp.add_line(0.764413,       500, 131.3)
        Xe_lamp.add_line(0.820859,       700, 131.3)
        Xe_lamp.add_line(0.826879,       500, 131.3)
        Xe_lamp.add_line(0.828239,      7000, 131.3)
        Xe_lamp.add_line(0.834912,      2000, 131.3)
        Xe_lamp.add_line(0.882183,      5000, 131.3)
        Xe_lamp.add_line(0.893328,       200, 131.3)
        Xe_lamp.add_line(0.895471,      1000, 131.3)
        Xe_lamp.add_line(0.904793,       400, 131.3)
        Xe_lamp.add_line(0.916517,       500, 131.3)
        Xe_lamp.add_line(0.980238,      2000, 131.3)
        Xe_lamp.add_line(0.992592,      3000, 131.3)
        Xe_lamp.add_line(1.262685,         5, 131.3)
        Xe_lamp.add_line(1.366021,       150, 131.3)
        Xe_lamp.add_line(1.414596,        80, 131.3)
        Xe_lamp.add_line(1.473641,       200, 131.3)
        Xe_lamp.add_line(1.542222,       110, 131.3)
        Xe_lamp.add_line(1.605641,        50, 131.3)
        Xe_lamp.add_line(1.673273,      5000, 131.3)
        Xe_lamp.add_line(2.026777,      2300, 131.3)


    def load_defaults(self):
        # Load lamps
        self.load_lamp("150W",     "lamp-spectrum.csv", 2 * 150, "2x150 W continuum lamp with adjustable power")
        self.load_lamp("Arc lamp", "lamp-line-spectrum.csv", 100, "100 W arc lamp for line calibration")
        self.load_black_body_lamp("PLANK",  5700, desc = "Theoretical black body emission at 5700 K")

        self.add_arc_lamps()

        # Load passband filters for the different gratings
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
        self.register_grating("VIS", "VIS", "VIS", 3000, 0.462e-6, 0.812e-6)
        
        self.register_grating("LR1", "IZJ", "LR1", 3327, 0.811e-6, 1.369e-6)
        self.register_grating("LR2", "HK",  "LR2", 3327, 1.450e-6, 2.450e-6)
        
        self.register_grating("MR1", "IZ",  "MR1", 7050, 0.830e-6, 1.050e-6)
        self.register_grating("MR2", "J",   "MR2", 7050, 1.046e-6, 1.324e-6)
        self.register_grating("MR3", "H" ,  "MR3", 7050, 1.435e-6, 1.815e-6)
        self.register_grating("MR4", "K" ,  "MR4", 7050, 1.951e-6, 2.469e-6)
        
        self.register_grating("HR1", "Z",         "HR1", 18000, 0.827e-6, 0.903e-6)
        self.register_grating("HR2", "H (high)",  "HR2", 18000, 1.538e-6, 1.678e-6)
        self.register_grating("HR3", "K (short)", "HR3", 18000, 2.017e-6, 2.201e-6)
        self.register_grating("HR4", "K (long)",  "HR4", 18000, 2.199e-6, 2.399e-6)

        # Register scales
        self.register_scale((4, 4), HARMONI_FINEST_SPAXEL_SIZE, HARMONI_FINEST_SPAXEL_SIZE)
        self.register_scale((10, 10), 10, 10)
        self.register_scale((20, 20), 20, 20)
        self.register_scale((60, 30), 60, 30)
