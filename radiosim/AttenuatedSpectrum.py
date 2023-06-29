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

from radiosim.SpectrumPainter import SPEED_OF_LIGHT
from . import RadianceSpectrum
from . import CompoundResponse

class AttenuatedSpectrum(RadianceSpectrum.RadianceSpectrum):
    def __init__(self, sourceSpectrum):
        super().__init__()

        self.sourceSpectrum = sourceSpectrum
        self.filters        = CompoundResponse()
        self.max_wl         = -1
        self.attenuation    = 0. # From 0 to 1

    def set_attenuation(self, attenuation):
        if attenuation < 0 or attenuation > 1:
            raise Exception('Invalid attenuation (must be between 0 and 1)')
        self.attenuation = attenuation

    def get_source_spectrum(self):
        return self.sourceSpectrum
    
    def push_filter(self, filter):
        self.max_wl = -1
        self.filters.push_back(filter)
    
    def set_fnum(self, fnum):
        super().set_fnum(fnum)
        self.sourceSpectrum.set_fnum(fnum)
    
    def set_spaxel(self, x, y):
        super().set_spaxel(x, y)
        self.sourceSpectrum.set_spaxel(x, y)
    
    # TODO: take emissivity of each intermediate filter into account
    def get_I(self, wl):
        alpha = (1. - self.attenuation) * self.sourceSpectrum.power_factor
        return self.filters.apply(wl, alpha * self.sourceSpectrum.get_I(wl))

    def get_I_matrix(self, wl):
        alpha = (1. - self.attenuation) * self.sourceSpectrum.power_factor
        return self.filters.apply(wl, alpha * self.sourceSpectrum.get_I_matrix(wl))

    def get_max_wl(self):
        if self.max_wl < 0:
            if self.sourceSpectrum.native_wl is not None:
                wl = self.sourceSpectrum.native_wl
                max_ndx = np.argmax(self.I(wl = wl))
                self.max_wl = wl[max_ndx]
            else:
                # Do not trust this
                self.max_wl = self.sourceSpectrum.get_max_wl()
        return self.max_wl

    def get_max_nu(self):
        return SPEED_OF_LIGHT / self.get_max_wl()

