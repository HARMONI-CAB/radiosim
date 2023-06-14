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
from . import BOLTZMANN
from . import SPEED_OF_LIGHT
from . import PROTONMASS

DELTA_LAMBDA_LIMIT = 6

class LineSpectrum(RadianceSpectrum):
    def __init__(self, peak_F, T = 1000, frel_c = 0):
        super().__init__()
        self.T          = T
        self.lines      = []
        self.peak_F     = peak_F 
        self.frel_c     = frel_c
        self.frel_max   = 0
        self.lambda_max = 0

    # Wavelength goes in µm, f_rel is adimensional
    def add_line(self, wavelength, f_rel, mass = 1):
        self.lines.append([wavelength * 1e-6, f_rel, mass])

        if f_rel > self.frel_max:
            self.frel_max = f_rel
            self.lambda_max = wavelength * 1e-6

    def get_max_wl(self):
        return self.lambda_max
    
    def get_max_nu(self):
        return SPEED_OF_LIGHT / self.get_max_wl()

    def get_I(self, wl):
        # This is a standard deviation
        delta_r_lambda = 1 / (SPEED_OF_LIGHT) * np.sqrt( \
            2 * BOLTZMANN * self.T / PROTONMASS)

        min_delta = np.max(np.abs(wl[1:] - wl[0:-1]))

        # Use hydrogen as reference
        wl_min = np.min(wl) * (1 - delta_r_lambda * DELTA_LAMBDA_LIMIT)
        wl_max = np.max(wl) * (1 + delta_r_lambda * DELTA_LAMBDA_LIMIT)
        subset = []
        # Select the lines we need to evaluate
        for line in self.lines:
            lambd = line[0]
            if wl_min < lambd and lambd < wl_max:
                subset.append(line)

        #
        # We have to be careful with the continuum here:
        # it is a density, and therefore its flux depends on
        # the width of the band along which it is integrated.
        #
        # The flux is therefore provided as a frction of the
        # total spectral flux
        #

        continuum = np.ones(wl.shape) * self.frel_c * self.peak_F
        if len(subset) > 0:
            sqrt2pi = np.sqrt(2 * np.pi)
            K = self.peak_F / (self.frel_max * 4 * np.pi * sqrt2pi)

            for line in subset:
                lambd  = line[0]
                mass   = line[2]
                sigma  = delta_r_lambda * lambd / np.sqrt(mass)
                sigma  = np.sqrt(sigma ** 2 + min_delta ** 2)
                delta  = wl - lambd
                flux   = line[1]
                A      = flux * K / sigma
                eval   = A * np.exp(-.5 * (delta / sigma) ** 2)

                continuum += eval
        
        return continuum
    