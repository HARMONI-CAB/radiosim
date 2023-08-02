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
from . import StageResponse
from scipy.interpolate import RegularGridInterpolator

class SkyResponse(StageResponse):
    def __init__(self, file: str, airmass_list: list):
        super().__init__()
        
        resp = np.genfromtxt(file, delimiter = ',')
        # This looks transposed
        colno = len(airmass_list) + 1
        if resp.shape[0] == colno and resp.shape[1] != colno:
            resp = resp.transpose()
        
        if resp.shape[1] != colno:
          raise RuntimeError(fr'Number of columns of {file} does not match airmass len')
        
        resp[:, 0] *= 1e-6 # Adjust units from µm to m

        self._interp = RegularGridInterpolator(
          (resp[:, 0], airmass_list),
          resp[:, 1:],
          bounds_error = False,
          fill_value = None) # Extrapolate
        
        self._airmass_list = airmass_list
        self._t_scale = 1
        self._airmass = airmass_list[0]
        self.set_temperature(0)
      
    def set_airmass(self, airmass):
        if airmass < self._airmass_list[0]:
            self._airmass = self._airmass_list[0]
        elif airmass > self._airmass_list[-1]:
            self._airmass = self._airmass_list[-1]
        else:
            self._airmass = airmass

        self._t_scale = airmass / self._airmass
        
    def get_t(self, wl):
        return self._t_scale * self._interp((wl, self._airmass)).ravel()[0]

    def get_t_matrix(self, wl):
        return self._t_scale * self._interp((wl, self._airmass))
        
    
