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
import numpy as np
import re
from . import SPEED_OF_LIGHT
from . import BlackBodySpectrum, PowerSpectrum

class StageResponse(ABC):
    _name  = None
    _label = None
    _color = '#d0d0d0'
    _text  = '#000000'

    def __init__(self):
        self._name       = "NO_NAME"
        self._label      = "NO LABEL"
        self._exp        = 1
        self._em_mul     = 1
        self._T          = 273
        self._black_body = BlackBodySpectrum(self._T)
        self._background = True
        self._fnum_set   = False

    def set_background(self, enabled):
        self._background = enabled
    
    def set_label(self, label):
        name = re.sub('[^0-9a-zA-Z_]', '', label)
        name = re.sub('^[^a-zA-Z_]+', '', name)
        self._name       = name
        self._label      = label
        if self._fnum_set:
            self.calc_color_lazy()

    def set_fnum(self, fnum):
        self._black_body.set_fnum(fnum)
        self._fnum_set = True
        self.calc_color_lazy()

    def get_label(self):
        return self._label
    
    def set_temperature(self, T):
        self._T     = T
        self._black_body.set_temperature(self._T)

    def get_temperature(self):
        return self._T
    
    def set_emission_multiplier(self, k):
        self._em_mul = k

    def set_multiplicity(self, exp):
        self._exp = exp

    def get_multiplicity(self):
        return self._exp

    def get_entrance_node_name(self):
        return self._name
    
    def get_exit_node_name(self):
        return self._name

    def gamma_correction(self, range, gamma = .25):
        ret = range ** gamma

        if ret < 0:
            ret = 0
        elif ret > 1:
            ret = 1

        return ret

    def calc_color_lazy(self):
        HUMAN_UV  = 320e-9
        HUMAN_UR  = 780e-9

        GIANT_UV  = 450e-9
        GIANT_IR  = 3500e-9

        H2G_M     = (GIANT_IR - GIANT_UV) / (HUMAN_UR - HUMAN_UV)
        
        blue_mu   = (420e-9 - HUMAN_UV) * H2G_M + GIANT_UV
        green_mu  = (530e-9 - HUMAN_UV) * H2G_M + GIANT_UV
        red_mu    = (560e-9 - HUMAN_UV) * H2G_M + GIANT_UV

        # blue_f    = 46e-9 * H2G_M
        # green_f   = 76e-9 * H2G_M
        # red_f     = 98e-9 * H2G_M

        blue_f    = 30e-9 * H2G_M
        green_f   = 30e-9 * H2G_M
        red_f     = 30e-9 * H2G_M

        blue      = int(self.gamma_correction(self.estimate_response(blue_mu, blue_f)) * 255)
        green     = int(self.gamma_correction(self.estimate_response(green_mu, green_f)) * 255)
        red       = int(self.gamma_correction(self.estimate_response(red_mu, red_f)) * 255)

        intens    = (.25 * blue + .5 * green + .25 * red) / (255.)

        self._color = fr'#{red:02x}{green:02x}{blue:02x}'
        self._text  = '#000000' if intens > 0.4 else '#ffffff'

        return self._color, self._text

    def get_graphviz(self):
        return fr'{self._name} [shape=rectangle, width=2, fillcolor="{self._color}", fontcolor="{self._text}", label=<     {self._label}<br/><font point-size="7">T = {self._T - 273.15:.3g}º C</font>>, labelangle=90 ];'

    @abstractmethod
    def get_t(self, wl):
        pass

    def get_t_matrix(self, wl_matrix):
        if len(wl_matrix.shape) != 1:
            raise Exception("High-order tensors not yet supported")
        return np.apply_along_axis(self.get_t, 1, wl_matrix)

    def t(self, wl):
        if self._exp == 1:
            if isinstance(wl, np.ndarray):
                return self.get_t_matrix(wl)
            else:
                return self.get_t(wl)
        else:
            if isinstance(wl, np.ndarray):
                return self.get_t_matrix(wl) ** self._exp
            else:
                return self.get_t(wl) ** self._exp
        
    def apply_array(self, wl, spectrum = None, thermal = True):
        t = self.t(wl)
        result = t * spectrum

        # For non-zero temperature: add background
        if self._T > 0 and self._background:
            if issubclass(type(spectrum), PowerSpectrum) or not thermal:
                return result
            result += (1. - t) * self._black_body.E(wl = wl)    
        return result

    def apply_scalar(self, wl, spectrum = None, thermal = True):
        t = self.t(wl)
        result = t * spectrum

        # For non-zero temperature: add background
        if self._T > 0 and self._background:
            if issubclass(type(spectrum), PowerSpectrum) or not thermal:
                return result
            result += (1. - t) * self._black_body.E(wl = wl)
        return result

    def apply(self, wl, spectrum = None, thermal = True):
        if isinstance(wl, np.ndarray):
            if spectrum is None:
                # Compound call
                if len(wl.shape) != 2 or wl.shape[0] != 2:
                    raise Exception("Invalid shape for the compound wavelength / spectrum array")
                return self.apply(wl[0, :], wl[1, :], thermal)
            elif isinstance(spectrum, np.ndarray):
                # Separate call
                if len(wl.shape) != 1:
                    raise Exception("Invalid shape for the wavelength axis " + str(wl.shape))
                
                if len(wl) != len(spectrum):
                    raise Exception("Wavelength and spectrum arrays size mismatch")
                return self.apply_array(wl, spectrum, thermal)
        elif isinstance(wl, float) and isinstance(spectrum, float):
            return self.apply_scalar(wl, spectrum, thermal)
        else:
            raise Exception("Invalid combination of wavelength and spectrum parameter types ({0} and {1})".format(str(type(wl)), str(type(spectrum))))

    def estimate_response(self, wl0, fwhm, num = 1000):
        std = fwhm / 2.355
        ww = np.linspace(wl0 - 5 * std, wl0 + 5 * std, num)
        dw = ww[1] - ww[0]
        spectrum = np.exp(-.5 * (ww - wl0) ** 2 / std ** 2) / (std * np.sqrt(2 * np.pi))
        resp  = self.apply(ww, spectrum)

        result = np.sum(resp) * dw

        return result