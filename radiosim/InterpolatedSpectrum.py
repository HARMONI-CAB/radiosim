import numpy as np
from . import RadianceSpectrum
import scipy.interpolate

class InterpolatedSpectrum(RadianceSpectrum.RadianceSpectrum):
    def __init__(self, file):
        super().__init__()
        
        resp = np.genfromtxt(file, delimiter = ',')

        if resp.shape[0] == 2:
            resp = resp.transpose()
        
        resp[:, 0] *= 1e-6 # Adjust units from µm to m
        resp[:, 1] *= 1e+6 # Adjust units from J / (m^2 * µm * sr * s) to J / (m^2 * m * sr * s)

        max_ndx = np.argmax(resp[:, 1])

        self.max_wl = resp[max_ndx, 0]
        self.max_I  = resp[max_ndx, 1]

        self.interpolator = scipy.interpolate.interp1d(
            resp[:, 0],
            resp[:, 1],
            bounds_error = False,
            fill_value = 0.)

        # Calculate max_nu
        nu = RadianceSpectrum.SPEED_OF_LIGHT / resp[:, 0]
        max_ndx = np.argmax(self.I(nu = nu))
        self.max_nu = nu[max_ndx]

    def get_I(self, wl):
        # Numpy horrors
        return self.interpolator(wl).ravel()[0]

    def get_I_matrix(self, wl):
        return self.interpolator(wl)

    def get_max_wl(self):
        return self.max_wl

    def get_max_nu(self):
        return self.max_nu
    