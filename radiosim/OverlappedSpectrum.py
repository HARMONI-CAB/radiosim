from abc import ABC, abstractmethod
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

