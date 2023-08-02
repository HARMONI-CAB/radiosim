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

class DetectorPixel(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def electronRatePerPixel(self, photons, wl = None, nu = None):
        """
        Accepts a photon field and produces an electron rate per pixel. This
        calculation involves sensitivity of the pixel, dark currents, et caetera.
        """
        pass

    @abstractmethod
    def electronsPerPixel(self, e_rate, wl = None, nu = None, t = 1, disable_noise = False):
        """
        Accepts an electron rate per pixel, an integration time, and produces a
        total number of electrons. This also accounts for saturation of the
        pixel
        """
        pass

    @abstractmethod
    def countsPerPixel(self, electrons, wl = None, nu = None):
        """
        Accepts the number of electrons and produces an ADU count. This takes into account
        non-linear effects of the ADU electrons, amplifier noise and others.
        """
        pass

    @abstractmethod
    def ron(self, t):
        """
        Accepts the exposure time and returns the readout noise, in electron. The exposure
        time may be either a scalar or an array.
        """
        pass
    
    @abstractmethod
    def gain(self):
        """
        Returns the gain of the ADU, in electrons per count.
        """
        pass