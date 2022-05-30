from abc import ABC, abstractmethod
import numpy as np
from . import RadianceSpectrum
from . import CompoundResponse

class AttenuatedSpectrum(RadianceSpectrum.RadianceSpectrum):
    def __init__(self, sourceSpectrum):
        super().__init__()

        self.sourceSpectrum = sourceSpectrum
        self.filters        = CompoundResponse()
        self.power          = sourceSpectrum.power
        self.power_factor   = sourceSpectrum.power_factor
        
    def push_filter(self, filter):
        self.filters.push_back(filter)
    
    # TODO: take emissivity of each intermediate filter into account
    def get_I(self, wl):
        return self.filters.apply(wl, self.sourceSpectrum.get_I(wl))

    def get_I_matrix(self, wl):
        return self.filters.apply(wl, self.sourceSpectrum.get_I_matrix(wl))

    def get_max_wl(self):
        return self.sourceSpectrum.get_max_wl()

    def get_max_nu(self):
        return self.sourceSpectrum.get_max_nu()
