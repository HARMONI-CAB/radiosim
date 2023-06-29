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

class StageResponse(ABC):
    _name  = None
    _label = None
    _color = '#d0d0d0'
    _text  = '#000000'

    def set_label(self, label):
        name = re.sub('[^0-9a-zA-Z_]', '', label)
        name = re.sub('^[^a-zA-Z_]+', '', name)

        self._label = label
        self._name  = name
        self._exp   = 1

        self.calc_color_lazy()

    def set_multiplicity(self, exp):
        self._exp = exp

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
        return fr'{self._name} [shape=rectangle, width=2, fillcolor="{self._color}", fontcolor="{self._text}", label="{self._label}", labelangle=90 ];'

    @abstractmethod
    def get_t(self, wl):
        pass

    def get_t_matrix(self, wl_matrix):
        if len(wl_matrix.shape) != 1:
            raise Exception("High-order tensors not yet supported")
        
        if self._exp == 1:
            return np.apply_along_axis(self.get_t, 1, wl_matrix)
        else:
            return np.apply_along_axis(self.get_t, 1, wl_matrix) ** self._exp
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
        
    def apply(self, wl, spectrum = None):
        if isinstance(wl, np.ndarray):
            if spectrum is None:
                # Compound call
                if len(wl.shape) != 2 or wl.shape[0] != 2:
                    raise Exception("Invalid shape for the compound wavelength / spectrum array")
                
                return self.apply(wl[0, :], wl[1, :])
            elif isinstance(spectrum, np.ndarray):
                # Separate call
                if len(wl.shape) != 1:
                    raise Exception("Invalid shape for the wavelength axis " + str(wl.shape))
                
                if len(wl) != len(spectrum):
                    raise Exception("Wavelength and spectrum arrays size mismatch")

                # Just a product
                if self._exp == 1:
                    return self.get_t_matrix(wl) * spectrum
                else:
                    return (self.get_t_matrix(wl) ** self._exp) * spectrum
            
        elif isinstance(wl, float) and isinstance(spectrum, float):
            if self._exp == 1:
                return self.get_t(wl) * spectrum
            else:
                return (self.get_t(wl) ** self._exp) * spectrum
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
