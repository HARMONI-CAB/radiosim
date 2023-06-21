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
import numpy as np

from . import SPEED_OF_LIGHT
from . import BOLTZMANN
from . import PLANCK_CONSTANT
from . import WIEN_B

class RadianceSpectrum(ABC):
    def __init__(self):
        self.fnum          = 0
        self.to_irradiance = -1
        self.power         = None
        self.power_factor  = 1
        self.native_wl     = None
        self.role          = None

    def set_role(self, role):
        self.role = role

    def get_role(self):
        return self.role

    def test_role(self, role):
        if self.role is None:
            return False

        return self.role == role
        
    def units(self):
        return self.unit_type
    
    def set_fnum(self, fnum):
        self.fnum          = 0
        self.to_irradiance = np.pi / (4 * fnum ** 2)
        
    def set_nominal_power_rating(self, power):
        self.power        = power
        self.power_factor = 1

    def is_adjustable(self):
        return self.power is not None

    def get_power(self):
        return self.power
    
    def adjust_power(self, power):
        if self.power is None:
            raise Exception("Cannot adjust spectrum source power: no nominal power rating set")
        
        self.power_factor = power / self.power

    @abstractmethod
    def get_max_wl(self):
        pass

    @abstractmethod
    def get_max_nu(self):
        pass

    @abstractmethod
    def get_I(self, wl):
        pass

    def get_max_I(self, frequency = False):
        if frequency:
            nu = self.get_max_nu()
            return self.I(nu = nu)
        else:
            wl = self.get_max_wl()
            return self.I(wl = wl)

    def get_max_photons(self, frequency = False):
        wl = self.get_max_wl()

        if frequency:
            return self.photons(nu = SPEED_OF_LIGHT / wl)
        else:
            return self.photons(wl = wl)

    def get_I_matrix(self, wl_matrix):
        if len(wl_matrix.shape) != 1:
            raise Exception("High-order tensors not yet supported")
        
        return np.apply_along_axis(self.get_I, 0, wl_matrix)

    def get_I_nu(self, nu):
        return self.get_I(SPEED_OF_LIGHT / nu) * (SPEED_OF_LIGHT / (nu * nu))
    
    def get_I_nu_matrix(self, nu):
        wlength = SPEED_OF_LIGHT / nu
        correct = (SPEED_OF_LIGHT / (nu * nu))

        return self.get_I_matrix(wlength) * correct

    def I(self, wl = None, nu = None):
        f = self.power_factor
        if wl is None and nu is not None:
            if isinstance(nu, np.ndarray):
                return f * self.get_I_nu_matrix(nu)
            else:
                return f * self.get_I_nu(nu)
        elif wl is not None and nu is None:
            if isinstance(wl, np.ndarray):
                return f * self.get_I_matrix(wl)
            else:
                return f * self.get_I(wl)
        else:
            raise Exception("Either wavelength or frequency must be provided")
    
    def E(self, wl = None, nu = None):
        if self.to_irradiance < 0:
            raise Exception("Cannot calculate radiance: f/# not set")
        return self.to_irradiance * self.I(wl, nu)
        
    def photons(self, wl = None, nu = None):
        corr = 1

        if nu is None and wl is None:
            raise Exception("Either wavelength or frequency must be provided")
        
        if nu is None:
            nu   = SPEED_OF_LIGHT / wl
            corr = SPEED_OF_LIGHT / (wl * wl)
        
        # Compute the spectral radiance (frequency)
        I_nu = self.I(nu = nu)

        # This has units of power per surface, solid angle and frequency
        # Since the energy of a photon is given by h * nu, dividing I_nu
        # by (h * nu) provides the photon flux spectrum per surface and solid angle
        return I_nu / (PLANCK_CONSTANT * nu) * corr

    def argmax_I(self, wl = None, nu = None):
        if nu is None and wl is None:
            raise Exception("Either wavelength or frequency must be provided")
        
        axis = wl if wl is not None else nu
        I    = self.I(wl, nu)

        return axis[np.argmax(I)]
        
    def argmax_photons(self, wl = None, nu = None):
        if nu is None and wl is None:
            raise Exception("Either wavelength or frequency must be provided")
        
        axis    = wl if wl is not None else nu
        photons = self.photons(wl, nu)

        return axis[np.argmax(photons)]

    def wien_T(self):
        return WIEN_B / self.get_max_wl()

    def planck(self, wl = None, nu = None, T = None):
        h = PLANCK_CONSTANT
        c = SPEED_OF_LIGHT
        k = BOLTZMANN
        c2 = c * c
        if T is None:
            T = self.wien_T()

        if wl is not None:    
            return 2 * h * c2 / (wl ** 5) / (np.exp(h * c / (wl * k * T)) - 1)
        
        if nu is not None:
            return 2 * h * nu ** 3 / (c2  * (np.exp(h * nu / (k * T)) - 1))
    
