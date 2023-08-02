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

from .DetectorPixel        import DetectorPixel
from .SimulationConfig     import SimulationConfig
from .Parameters           import Parameters
from .BlackBodySpectrum    import BlackBodySpectrum
from scipy.integrate       import simps

from . import SPEED_OF_LIGHT

import numpy as np
from numpy.random import default_rng

class CCDPixel(DetectorPixel):
    def __init__(self, params: Parameters, config: SimulationConfig):
        self.G          = config.detector.G
        
        if config.grating == 'VIS':
            self.ron_le    = config.detector.ron_vis
            self.ron_he    = config.detector.ron_vis
            self.dark      = config.detector.dark_vis
        else:
            self.ron_le    = config.detector.ron_nir_le
            self.ron_he    = config.detector.ron_nir
            self.dark      = config.detector.dark_nir
            
        self.QE         = params.get_QE(config.grating)
        self.pixel_area = config.detector.pixel_size ** 2
        self.trad_cone  = config.detector.trad_cone
        self.tmech_cone = config.detector.tmech_cone

        if 'TCryo' not in config.temps:
            raise RuntimeError('Cryogenic temperature not defined')
        
        self.trad       = params.get_temperature('TCryo')
        self.tcryo_mech = self.trad - 5.
        
        self.Brad       = BlackBodySpectrum(self.trad)
        self.Bcryo_mech = BlackBodySpectrum(self.tcryo_mech)
        self.rng        = default_rng()
        
    def electronRatePerPixel(self, photons, wl = None, nu = None):
        """
        Accepts a photon field and produces an electron rate per pixel. This
        calculation involves sensitivity of the pixel, dark currents, et caetera.
        """

        # Note that photons here has units of photons/s
        if wl is None:
            wl = SPEED_OF_LIGHT / nu
            sign = -1
        else:
            sign = 1

        prad     = self.trad_cone  * self.Brad.photons(wl)         # photons/s/m/m2
        pmech    = self.tmech_cone * self.Bcryo_mech.photons(wl)   # photons/s/m/m2
        ppixel   = (prad + pmech) * self.pixel_area                # photons/s/m

        if isinstance(self.QE, float):
            e_rate = self.QE * photons       # e/s
            epixel = self.QE * ppixel        # e/s/m
        else:
            e_rate = self.QE.t(wl) * photons # e/s
            epixel = self.QE.t(wl) * ppixel  # e/s/m

        #
        # We need to be careful here: background emission comes from ALL
        # wavelengths. We have a stream of thermal photons that is going to
        # excite electrons in the detector according to the QE. This means that
        # we need to integrate this stream of background photons accordingly.
        #

        e_rate += sign * simps(epixel, wl) #e/s
        return e_rate

    def electronsPerPixel(self, e_rate, wl = None, nu = None, t = 1, noisy = True):
        """
        Accepts an electron rate per pixel, an integration time, and produces a
        total number of electrons. This also accounts for saturation of the
        pixel
        """
        
        e = e_rate * t
        e[np.where(e < 0)] = 0

        if noisy:
            # Add Poisson noise
            e = self.rng.poisson(lam = e)
            
            # Add readout noise
            ron = self.ron(t)
            e = self.rng.normal(loc = e, scale = ron)
        return e

    def ron(self, t):
        return self.ron_le * (t < 120) + self.ron_he * (t >= 120)
    
    def gain(self):
        return self.G
    
    def countsPerPixel(self, electrons, wl = None, nu = None, noisy = True):
        """
        Accepts the number of electrons and produces an ADU count. This takes into account
        non-linear effects of the ADU electrons, amplifier noise and others.
        """
        
        return electrons / self.G