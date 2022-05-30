import numpy as np

from numpy.random import default_rng

from . import SPEED_OF_LIGHT
from . import BOLTZMANN
from . import PLANCK_CONSTANT
from . import WIEN_B
from . import StageResponse

class DetectorSimulator:
    def __init__(
        self,
        spectrum = None,
        A_sp = 15e-6,
        pxPerDeltaL = 2.2,
        R = 18000,
        QE = .95,
        binning = 1,
        G = 1,
        poisson = False,
        ron = 5):
        self.A_sp        = A_sp
        self.pxPerDeltaL = pxPerDeltaL
        self.spectrum    = spectrum
        self.R           = R
        self.QE          = QE
        self.binning     = binning
        self.G           = G
        self.poisson     = poisson
        self.rng         = default_rng()
        self.ron         = ron

    def assert_spectrum(self):
        if self.spectrum is None:
            raise Exception("No spectrum was defined")

    def set_R(self, R):
        self.R = R
    
    def set_spectrum(self, spectrum):
        self.spectrum = spectrum

    # Returns attenuated flux per spaxel (T_h * T_d * \Phi_{sp})
    # This is actually a spectral density (W/µm)
    def attenFluxPerSpaxel(self, wl = None, nu = None):
        self.assert_spectrum()

        return self.spectrum.E(wl = wl, nu = nu) * self.A_sp

    # Returns band dispersion (D_h). This is actually \Delta\lambda
    # across the spectral dimension
    def Dh(self, wl = None, nu = None):
        self.assert_spectrum()

        if wl is None:
            if nu is None:
                raise Exception("Either frequency or wavelength must be provided")
            wl = SPEED_OF_LIGHT / nu
        
        return wl / (self.pxPerDeltaL * self.R)

    # Returns incident spectral flux per pixel (\Phi_{px})
    # Please note this has units of W!! This is NOT a spectral density (W)
    def integratedFluxPerPixel(self, wl = None, nu = None):
        self.assert_spectrum()

        # According to HRM-00509, \Phi_{px} is computed as T_h * T_d * D_h * \Phi_{sp}
        return self.Dh(wl = wl, nu = nu) * self.attenFluxPerSpaxel(wl = wl, nu = nu)

    # Returns photon energy
    def E_p(self, wl = None, nu = None):
        if nu is None:
            if wl is None:
                raise Exception("Either frequency or wavelength must be provided")
            nu = SPEED_OF_LIGHT / wl
        
        return PLANCK_CONSTANT * nu

    # Returns incident spectral flux per pixel, in photons
    def photonFluxPerPixel(self, wl = None, nu = None):
        self.assert_spectrum()

        ret = self.integratedFluxPerPixel(wl = wl, nu = nu) / self.E_p(wl = wl, nu = nu)
        nans = np.isnan(ret)
        ret[nans] = 0
        return ret

    # Returns the generated photoelectron rate
    def electronRatePerPixel(self, wl = None, nu = None):
        self.assert_spectrum()
        
        if isinstance(self.QE, float):
            rate = self.QE * self.photonFluxPerPixel(wl = wl) * self.binning
        elif isinstance(self.QE, StageResponse):
            rate = self.QE.apply(self.spectrum) * self.binning
        else:
            raise Exception("Unknown data type for QE (" + str(type(self.QE)) + ")")

        return rate

    # Returns the actual number of generated photoelectrons after some time
    def electronsPerPixel(self, wl = None, nu = None, t = 1):
        e = t * self.electronRatePerPixel(wl, nu)

        if self.poisson:
            e = self.rng.poisson(lam = e)
        
        return e

    # Returns simulated counts
    def countsPerPixel(self, wl = None, nu = None, t = 1):
        e = self.electronsPerPixel(wl = wl, nu = nu, t = t)
        e = self.rng.normal(loc = e, scale = self.ron)

        return np.round(e / self.G)
    