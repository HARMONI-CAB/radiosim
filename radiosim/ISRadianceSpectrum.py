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

import numpy as np
from .RadianceSpectrum import RadianceSpectrum
from .BlackBodySpectrum import BlackBodySpectrum

#
# This turns a power spectral density of a lamp into a spectral radiance
# spectrum at the output of an integrating sphere, according to some basic
# parameters like IS radius, aperture and reflectance of the inner coating
# of the sphere.
#

class ISRadianceSpectrum(RadianceSpectrum):
    def __init__(self, radius, aperture_area, surface_response, T = 273):
        super().__init__()
        self._lamps   = []
        self._max_wl  = -1
        self._T       = T

        self._sphere_area     = 4 * np.pi * radius ** 2
        self._geom_efficiency = 1 - aperture_area / self._sphere_area
        self._response        = surface_response
        self._black_body      = BlackBodySpectrum(self._T)

    def set_temperature(self, T):
        self._T = T
        self._black_body.set_temperature(self._T)
        
    def power_to_radiance(self, wl):
        rho_m   = self._response.t(wl)
        rho     = rho_m * self._geom_efficiency
        return rho / ((1 - rho) * self._sphere_area)

    def power_to_radiance_matrix(self, wl):
        rho_m   = self._response.t(wl)
        rho     = rho_m * self._geom_efficiency
        return rho / ((1 - rho) * self._sphere_area)

    def push_spectrum(self, spectrum):
        self._max_wl = -1
        self._lamps.append(spectrum)

    def get_total_psd(self, wl, nu = None):
        result = 0
        for spectrum in self._lamps:
            result += spectrum.PSD(wl = wl, nu = nu)
        
        return result

    def get_total_psd_matrix(self, wl):
        result = np.zeros(wl.shape)
        for spectrum in self._lamps:
            result += spectrum.PSD(wl)

        return result

    def get_max_wl(self):
        return -1

    def get_max_nu(self):
        return -1

    def get_background(self, wl):
        t = self._response.t(wl)
        return (1. - t) * self._black_body.I(wl = wl)

    def get_I(self, wl):
      return self.power_to_radiance(wl) * self.get_total_psd(wl) \
        + self.get_background(wl)

    def get_I_matrix(self, wl):
      return self.power_to_radiance_matrix(wl) * self.get_total_psd_matrix(wl) \
        + self.get_background(wl)
