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

from abc import ABC, abstractmethod
import yaml
from yaml.loader import SafeLoader
from radiosim.Parameters import HARMONI_PIXEL_SIZE

class SerializableConfig(ABC):
    def __init__(self):
        super().__init__()
        self._cache = {}

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def load(self, dict):
        pass

    def getordfl(self, dict, key, dfl):
        if key not in dict:
            return dfl

        return dict[dfl]

    def save_param(self, attr):
        self._cache[attr] = getattr(self, attr)
    
    def load_from_dict(self, attr, dict):
        if dict is None:
            dict = self._cache

        if attr in dict:
            setattr(self, attr, dict[attr])
        
    def load_all(self, dict):
        for key in dict.keys():
            if key[0] != '_':
                self.load_from_dict(key, dict)
            
    def as_dict(self):
        return self._cache.copy()
    
    def save_to_file(self, file):
        self.save()

        with open(file, 'w') as fp:
            yaml.dump(self._cache, fp, default_flow_style = False)
    
    def load_from_file(self, file):
        with open(file, 'r') as fp:
            data = yaml.load(fp, Loader = SafeLoader)
            self._cache = data
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

        self.load(self._cache)
    
class LampConfig(SerializableConfig):
    def __init__(self):
        super().__init__()
        
        self.is_on             = False
        self.power             = None
        self.attenuation       = 0
        self.effective_area    = 8e-5
        self.fiber             = None
        self.fiber_length      = 1

    def save(self):
        self.save_param('is_on')
        self.save_param('power')
        self.save_param('attenuation')
        self.save_param('effective_area')
        self.save_param('fiber')
        self.save_param('fiber_length')

    def load(self, dict):
        self.load_all(dict)
    
class DetectorConfig(SerializableConfig):
    def __init__(self):
        super().__init__()

        self.G          = 1
        self.ron        = 5
        self.QE         = .95
        self.pixel_size = HARMONI_PIXEL_SIZE

    def save(self):
        self.save_param('G')
        self.save_param('ron')
        self.save_param('QE')
        self.save_param('pixel_size')

    def load(self, dict):
        self.load_all(dict)
    
class TelescopeConfig(SerializableConfig):
    def __init__(self):
        super().__init__()

        self.focal_length    = 743.40
        self.aperture        = 39
        self.collecting_area = 980
        self.zenith_distance = 0
        self.moon            = 0
        self.efficiency      = 1

    def save(self):
        self.save_param('focal_length')
        self.save_param('aperture')
        self.save_param('zenith_distance')
        self.save_param('moon')
        self.save_param('efficiency')
        self.save_param('collecting_area')

    def load(self, dict):
        self.load_all(dict)

class SimulationConfig(SerializableConfig):
    def __init__(self):
        super().__init__()
        
        self.lamps         = {}
        self.lamp_configs  = {}

        self.telescope       = TelescopeConfig()
        self.detector        = DetectorConfig()
        self.cal_select      = False
        self.is_radius       = 1e-1
        self.is_aperture     = .5e-1
        self.is_coating      = 'SPECTRALON'
        self.offner_f        = 17.37 # See CALIBRATION UNIT RELAY OPTICAL DESIGN

        self.binning         = 1
        self.lambda_sampling = 2.2
        self.grating         = 'VIS'
        self.aomode          = 'NOAO'
        self.scale           = (4, 4)
        self.t_exp           = 10
        self.saturation      = 20000
        self.temperature     = 273.15

        self.type            = 'is_out'
        self.x_axis          = 'wavelength'
        self.y_axis          = 'spect_E' # Spectral irradiance

        self.spect_log       = False
        self.noisy           = True

        self.texp_band       = self.grating
        self.texp_use_band   = True
        self.texp_wl         = 0.8e-6
        self.texp_log        = False

        self.texp_iters      = 1000

        self.detector_config = {}
        
    def set_lamp_config(self, name, lamp):
        self.lamps[name] = lamp
    
    def save(self):
        self.save_param("cal_select")
        self.save_param("lambda_sampling")
        
        self.save_param("is_coating")
        self.save_param("is_radius")
        self.save_param("is_aperture")
        self.save_param("offner_f")
        
        self.save_param("binning")
        self.save_param('grating')
        self.save_param('aomode')
        self.save_param('scale')
        self.save_param('t_exp')
        self.save_param('saturation')
        self.save_param('temperature')
        self.save_param('type')
        self.save_param('x_axis')
        self.save_param('y_axis')
        self.save_param('spect_log')
        self.save_param('noisy')

        self.save_param('texp_band')
        self.save_param('texp_use_band')
        self.save_param('texp_wl')
        self.save_param('texp_log')

        self.save_param('texp_iters')

        for lamp in self.lamps.keys():
            self.lamps[lamp].save()
            self.lamp_configs[lamp] = self.lamps[lamp].as_dict()

        self.save_param('lamp_configs')

        self.detector.save()
        self.detector_config = self.detector.as_dict()
        
        self.save_param('detector_config')

        self.telescope.save()
        self.telescope_config = self.telescope.as_dict()
        self.save_param('telescope_config')

    def load(self, dict):
        self.load_all(dict)

        # Fix certain datatypes
        self.scale = tuple(self.scale)
        
        for lamp in self.lamp_configs.keys():
            self.lamps[lamp] = SimulationConfig()
            self.lamps[lamp].load(self.lamp_configs[lamp])

        self.detector.load(self.detector_config)
        self.telescope.load(self.telescope_config)
