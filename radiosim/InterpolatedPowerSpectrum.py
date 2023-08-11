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
from . import SPEED_OF_LIGHT
import scipy.interpolate

class InterpolatedPowerSpectrum(PowerSpectrum):
    def __init__(self, file = None, response = None, SI = False):
        super().__init__()
        
        if file is not None:
            resp = np.genfromtxt(file, delimiter = ',')
        elif response is not None:
            resp = response
        else:
            raise RuntimeError('Spectrum not specified')
        
        if resp.shape[0] == 2:
            resp = resp.transpose()
        
        if not SI:
            resp[:, 0] *= 1e-6 # Adjust units from µm to m
            resp[:, 1] *= 1e+6 # Adjust units from W/µm to W/m

        max_ndx = np.argmax(resp[:, 1])

        self.max_wl = resp[max_ndx, 0]
        self.max_I  = resp[max_ndx, 1]
        self.native_wl = resp[:, 0]
        
        self.interpolator = scipy.interpolate.interp1d(
            resp[:, 0],
            resp[:, 1],
            bounds_error = False,
            fill_value = 0.)

        # Calculate max_nu
        nu = SPEED_OF_LIGHT / resp[:, 0]
        max_ndx = np.argmax(self.PSD(nu = nu))
        self.max_nu = nu[max_ndx]

    def get_PSD(self, wl):
        # Numpy horrors
        return self.interpolator(wl).ravel()[0]

    def get_PSD_matrix(self, wl):
        return self.interpolator(wl)

    def get_max_wl(self):
        return self.max_wl

    def get_max_nu(self):
        return self.max_nu
    