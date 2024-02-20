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

from . import PowerSpectrum
from . import WIEN_B
from . import SPEED_OF_LIGHT

#
# In order to convert from radiance to power we have to take into account
# the following facts:
#
# - The isotropic radiator refers to a Lambertian sphere of certain area
# - The surface does not radiante in all directions. In particular:
#   1. The sphere is opaque. This divides the angular sphere from 4pi to 2pi
#   2. The emission is weighted by the angle with a factor cos theta. This
#      scales down the energy again by 1/2, resulting in pi.

class IsotropicRadiatorSpectrum(PowerSpectrum):
    def __init__(self, area, radiance):
        super().__init__()
        self.radiance = radiance
        self.radiance_to_power = np.pi * area
        
    def get_max_wl(self):
        return self.radiance.get_max_wl(self)
    
    def get_max_nu(self):
        return self.radiance.get_max_nu()
    
    def get_PSD(self, wl):
        return self.radiance.I(wl) * self.radiance_to_power

    def get_PSD_matrix(self, wl):
        return self.radiance.I(wl) * self.radiance_to_power
    
    def adjust_power(self, power):
        self.radiance.adjust_power(power)
    
    def integrate_power(self, wl_min = .45e-6, wl_max = 2.4e-6, N = 1000):
        wl   = np.linspace(wl_min, wl_max, N + 1)
        dWl  = wl[1] - wl[0]
        psds = self.get_PSD_matrix(wl)
        trap = .5 * (psds[:-1] + psds[1:]) * dWl
        return np.sum(trap)
