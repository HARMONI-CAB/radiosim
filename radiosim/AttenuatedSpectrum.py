from abc import ABC, abstractmethod
import numpy as np

from radiosim.SpectrumPainter import SPEED_OF_LIGHT
from . import RadianceSpectrum
from . import CompoundResponse

class AttenuatedSpectrum(RadianceSpectrum.RadianceSpectrum):
    def __init__(self, sourceSpectrum):
        super().__init__()

        self.sourceSpectrum = sourceSpectrum
        self.filters        = CompoundResponse()
        self.power          = sourceSpectrum.power
        self.power_factor   = sourceSpectrum.power_factor
        self.max_wl         = -1
        self.attenuation    = 0. # From 0 to 1

    def set_attenuation(self, attenuation):
        if attenuation < 0 or attenuation > 1:
            raise Exception('Invalid attenuation (must be between 0 and 1)')
        self.attenuation = attenuation

    def get_source_spectrum(self):
            return self.sourceSpectrum
    
    def push_filter(self, filter):
        self.max_wl = -1
        self.filters.push_back(filter)
    
    def set_fnum(self, fnum):
        super().set_fnum(fnum)
        self.sourceSpectrum.set_fnum(fnum)
    
    # TODO: take emissivity of each intermediate filter into account
    def get_I(self, wl):
        alpha = 1. - self.attenuation
        return self.filters.apply(wl, alpha * self.sourceSpectrum.get_I(wl))

    def get_I_matrix(self, wl):
        alpha = 1. - self.attenuation
        return self.filters.apply(wl, alpha * self.sourceSpectrum.get_I_matrix(wl))

    def get_max_wl(self):
        if self.max_wl < 0:
            if self.sourceSpectrum.native_wl is not None:
                wl = self.sourceSpectrum.native_wl
                max_ndx = np.argmax(self.I(wl = wl))
                self.max_wl = wl[max_ndx]
            else:
                # Do not trust this
                self.max_wl = self.sourceSpectrum.get_max_wl()
        return self.max_wl

    def get_max_nu(self):
        return SPEED_OF_LIGHT / self.get_max_wl()

