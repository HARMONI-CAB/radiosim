from faulthandler import disable
import numpy as np

from numpy.random import default_rng

from . import SPEED_OF_LIGHT
from . import BOLTZMANN
from . import PLANCK_CONSTANT
from . import WIEN_B
from . import StageResponse
from scipy.special import erf

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

    # Returns attenuated? flux (W/(m^2µm))
    def get_E(self, wl = None, nu = None, atten = True):
        if atten:
            spectrum = self.spectrum
        else:
            spectrum = self.spectrum.get_source_spectrum()
        
        return spectrum.E(wl = wl, nu = nu)
    
    # Returns attenuated? photon flux (photons/(m^2µm))
    def get_photon_flux(self, wl = None, nu = None, atten = True):
        return self.get_E(wl = wl, nu = nu, atten = atten) / self.E_p(wl, nu)
    
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

        if len(nans.shape) > 0:
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
    def electronsPerPixel(self, wl = None, nu = None, t = 1, disable_noise = False):
        e = t * self.electronRatePerPixel(wl, nu)

        if self.poisson and not disable_noise:
            e = self.rng.poisson(lam = e)
        
        return e

    # Returns simulated counts
    def countsPerPixel(self, wl = None, nu = None, t = 1, disable_noise = False):
        e = self.electronsPerPixel(wl = wl, nu = nu, t = t, disable_noise = disable_noise)

        if not disable_noise:
            e = self.rng.normal(loc = e, scale = self.ron)
            return np.round(e / self.G)

        return e / self.G
    
    # Compute max texp:
    def getMaxTexp(self, wl = None, nu = None, count_limit = 20000):
        # Compute counts during 1 second. Assume proportionality and deduce exposition
        counts = self.countsPerPixel(
            wl = wl,
            nu = nu,
            t = 1,
            disable_noise = True)

        # Scalar case
        if isinstance(counts, float):
            max_count = counts
            if wl is not None:
                max_lambda = wl
                max_nu     = SPEED_OF_LIGHT / max_lambda
            elif nu is not None:
                max_nu     = nu
                max_lambda = SPEED_OF_LIGHT / max_nu
        else: # Vector case
            max_ndx = np.argmax(counts)
            max_count = counts[max_ndx]
            if wl is not None:
                max_lambda = wl[max_count]
                max_nu     = SPEED_OF_LIGHT / max_lambda
            elif nu is not None:
                max_nu     = nu[max_count]
                max_lambda = SPEED_OF_LIGHT / max_nu
        
        if max_count == 0.:
            raise Exception("Source produced no counts, cannot guess max t_exp")
        
        # TODO: CONSIDER NON-LINEAR SCENARIOS
        k = float(count_limit) / float(max_count)

        return (1 * k,  max_lambda, max_nu)

    def poissonDistribution(self, x, rate):
        if rate > 20:
            sqrtt = np.sqrt(rate)
            quot  = np.sqrt(2 * np.pi) * sqrtt
            mu    = rate
            p = np.exp(-.5 * ((x - mu) / sqrtt) ** 2) / quot
        else:
            p = np.exp(-rate) * rate ** x / np.math.gamma(x + 1)

        return p

    def normalInt(self, a, b, sigma, mu):
        sqrt2 = 1.4142135623730951
        q = 1 / (sqrt2 * sigma)
        p = .5 * (erf((b - mu) * q) - erf((a - mu) * q))
        
        return p
    
    def getTexpDistribution(self, wl, count_limit, N = 1000):
        Ie          = self.electronRatePerPixel(wl = wl)
        texp_approx = self.getMaxTexp(wl = wl, count_limit = count_limit)[0]
        texp_min    = np.max([0., texp_approx - texp_approx ** .5])
        texp_max    = texp_approx + texp_approx ** .5
        sigma       = self.ron / self.G            
        t_exp       = np.linspace(texp_min, texp_max, N)
        p           = np.zeros(N)
        i           = 0
        ca          = count_limit - .5
        cb          = count_limit + .5
        dt          = (texp_max - texp_min) / (N - 1)

        print("Integration time estimate: {0:g} s".format(texp_approx))

        for t in t_exp:
            rate = Ie * t
            max  = int(np.ceil(rate))
            nes  = np.linspace(0, max, max + 1)
            mus  = nes / self.G
            p[i] = np.dot(
                self.poissonDistribution(nes, rate),
                self.normalInt(ca, cb, sigma = sigma, mu = mus))
            i += 1

        nans = np.isnan(p)

        if len(nans.shape) > 0:
            p[nans] = 0
        
        k =  np.sum(p * dt)
        if k == 0.:
            k = 1
        
        return np.array([t_exp, p / k])


