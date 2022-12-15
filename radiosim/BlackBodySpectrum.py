from . import RadianceSpectrum
from . import WIEN_B
from . import SPEED_OF_LIGHT

class BlackBodySpectrum(RadianceSpectrum):
    def __init__(self, T = 5000):
        super().__init__()
        self.T = T # K

    def set_temperature(self, T):
        self.T = T

    def get_max_wl(self):
        return WIEN_B / self.T
    
    def get_max_nu(self):
        return SPEED_OF_LIGHT / self.get_max_wl()
    
    def get_I(self, wl):
        return self.planck(wl, T = self.T)
