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

from . import RadianceSpectrum

class OverlappedSpectrum(RadianceSpectrum):
    def __init__(self):
        super().__init__()

        self.sourceSpectrums   = []
        self.max_wl            = -1

    def push_spectrum(self, spectrum):
        self.max_wl = -1
        self.sourceSpectrums.append(spectrum)
    
    def set_fnum(self, fnum):
        super().set_fnum(fnum)

        for spectrum in self.sourceSpectrums:
            spectrum.set_fnum(fnum)
    
    # TODO: take emissivity of each intermediate filter into account
    def get_I(self, wl):
        result = 0
        for spectrum in self.sourceSpectrums:
            current = spectrum.get_I(wl)
            if result is None:
                result = current
            else:
                result += current
        return result

    def get_I_matrix(self, wl):
        result = np.zeros(wl.shape)
        for spectrum in self.sourceSpectrums:
            current = spectrum.get_I_matrix(wl)
            if result is None:
                result = current
            else:
                result += current

        return result

    def get_max_wl(self):
        return -1

    def get_max_nu(self):
        return -1

