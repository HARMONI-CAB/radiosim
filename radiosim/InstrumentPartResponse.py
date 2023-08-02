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

import scipy.interpolate

DEFAULT_DUST_EMI = 0.5    # Grey Dust covering on some optics (50% emissivity)
DEFAULT_MIN_DUST = 0.005  # 0.5% dust on optical surfaces - won't be perfectly clean

class InstrumentPartResponse(StageResponse):
    def __init__(
      self,
      temp: float,
      area_scaling: float   = 1,
      n_mirrors: int        = 0,
      n_lenses: int         = 0,
      dust_lens: float      = 0.,
      dust_mirror: float    = DEFAULT_MIN_DUST,
      global_scaling: float = 1.,
      emis_scaling: float   = 1.,
      emis_mirror           = None,
      emis_lens             = None,
      t_mirror              = None,
      t_lens                = None,
      emis_dust: float      = DEFAULT_DUST_EMI
    ):
        super().__init__()
        
        if emis_mirror is None and t_mirror is None:
          n_mirrors = 0
        
        if emis_lens is None and t_lens is None:
          n_lenses = 0

        self._area_scaling    = area_scaling
        self._n_mirrors       = n_mirrors
        self._n_lenses        = n_lenses
        self._fdust_lens      = dust_lens
        self._fdust_mirror    = dust_mirror
        self._g_scaling       = global_scaling
        self._emis_scaling    = emis_scaling
        self._emis_dust       = emis_dust

        # Setup mirror response interpolator
        if n_mirrors > 0:
            if type(t_mirror) is str:
              self._mirror_interp = self.load_throughput(t_mirror)
            elif type(t_mirror) is float:
              self._mirror_interp = self.flat_throughput(t_mirror)
            elif type(emis_mirror) is str:
              self._mirror_interp = self.load_emissivity(emis_mirror)
            elif type(emis_mirror) is float:
              self._mirror_interp = self.flat_emissivity(emis_mirror)

        if n_lenses > 0:
            if type(t_lens) is str:
              self._lens_interp   = self.load_throughput(t_lens)
            elif type(t_lens) is float:
              self._lens_interp   = self.flat_throughput(t_lens)
            elif type(emis_lens) is str:
              self._lens_interp   = self.load_emissivity(emis_lens)
            elif type(emis_lens) is float:
              self._lens_interp   = self.flat_emissivity(emis_lens)
          
        self._t_dust = self.calc_dust_throughtput()

        self.set_temperature(temp)

    def flat_emissivity(self, level):
        return scipy.interpolate.interp1d(
            [400e-9, 2.6e-6],
            [1 - level, 1 - level],
            bounds_error=False,
            fill_value=0)

    def load_emissivity(self, filename):
        resp = np.genfromtxt(filename, delimiter = ',')

        # This looks transposed
        if resp.shape[0] == 2 and resp.shape[1] != 2:
            resp = resp.transpose()
      
        resp[:, 0] *= 1e-6 # Adjust units from µm to m

        # Be careful! This is a emissivity spectrum. We need a throughput
        # spectrum here.

        return scipy.interpolate.interp1d(
            resp[:, 0],
            1 - resp[:, 1],
            bounds_error = False,
            fill_value = 0.)
          
    def flat_throughput(self, level):
        return scipy.interpolate.interp1d(
            [400e-9, 2.6e-6],
            [level, level],
            bounds_error=False,
            fill_value=0)

    def load_throughput(self, filename):
        resp = np.genfromtxt(filename, delimiter = ',')

        # This looks transposed
        if resp.shape[0] == 2 and resp.shape[1] != 2:
            resp = resp.transpose()
      
        resp[:, 0] *= 1e-6 # Adjust units from µm to m

        return scipy.interpolate.interp1d(
            resp[:, 0],
            resp[:, 1],
            bounds_error = False,
            fill_value = 0.)

    def set_area_scaling(self, scaling):
        self._area_scaling = scaling
      
    def calc_dust_throughtput(self):
        t_mirror = 1. - self._emis_dust * self._fdust_mirror
        t_lens   = 1. - self._emis_dust * self._fdust_lens
        t        = t_mirror ** self._n_mirrors * t_lens ** self._n_lenses

        #
        # TODO: This is hard-copied from HSIM and it is not well understood.
        # I am waiting for an explanation by Miguel in order to use this.
        #

        if self._area_scaling != 1:
          e        = 1 - t
          e       *= self._area_scaling
          t        = 1 - e

        return   t
    
    def get_t(self, wl):
        t = self._t_dust

        if self._n_mirrors > 0:
            t *= self._mirror_interp(wl).ravel()[0] ** self._n_mirrors

        if self._n_lenses > 0:
            t *= self._lens_interp(wl).ravel()[0] ** self._n_lenses
        
        return t

    def get_t_matrix(self, wl):
        t = self._t_dust * np.ones(wl.shape)

        if self._n_mirrors > 0:
            t *= self._mirror_interp(wl) ** self._n_mirrors

        if self._n_lenses > 0:
            t *= self._lens_interp(wl) ** self._n_lenses

        return t
        
    