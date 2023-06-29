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

from faulthandler import disable
import numpy as np
import time

from numpy.random import default_rng

from . import SPEED_OF_LIGHT
from . import PLANCK_CONSTANT
from . import StageResponse
from scipy.special import erf

class TExpSimulator:
    def __init__(self, det, wl, count_limit, N = 1000):
        self.det         = det
        self.Ie          = self.det.electronRatePerPixel(wl = wl)
        self.texp_approx = self.det.getMaxTexp(wl = wl, count_limit = count_limit)[0]
        self.texp_min    = np.max([0., self.texp_approx - self.texp_approx ** .5])
        self.texp_max    = self.texp_approx + self.texp_approx ** .5
        self.sigma       = self.det.ron / self.det.G
        self.t_exp       = np.linspace(self.texp_min, self.texp_max, N)
        self.p           = np.zeros(N)
        self.i           = 0
        self.N           = N
        self.ca          = count_limit - .5
        self.cb          = count_limit + .5
        self.dt          = (self.texp_max - self.texp_min) / (N - 1)

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

    def get_texp_approx(self):
        return self.texp_approx

    def progress(self):
        return self.i / self.N

    def done(self):
        return self.i == self.N

    def work(self, timeout_ms = 100):
        start = time.perf_counter()
        i = self.i
        while i < self.N and (time.perf_counter() - start) * 1e3 < timeout_ms:
            t = self.t_exp[i]
            rate = self.Ie * t
            max  = int(np.ceil(rate))
            nes  = np.linspace(0, max, max + 1)
            mus  = nes / self.det.G
            
            self.p[i] = np.dot(
                self.poissonDistribution(nes, rate),
                self.normalInt(self.ca, self.cb, sigma = self.sigma, mu = mus))
            i += 1

        self.i = i

    def get_result(self):
        nans = np.isnan(self.p)

        if len(nans.shape) > 0:
            self.p[nans] = 0
        
        k =  np.sum(self.p * self.dt)
        if k == 0.:
            k = 1
        
        return np.array([self.t_exp, self.p / k])


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

    # Returns attenuated? flux (W/(m^2 m))
    def get_E(self, wl = None, nu = None, atten = True):
        if atten:
            spectrum = self.spectrum
        else:
            spectrum = self.spectrum.get_source_spectrum()
        
        return spectrum.E(wl = wl, nu = nu)
    
    # Returns attenuated? photon flux (photons/(m^2 m))
    def get_photon_flux(self, wl = None, nu = None, atten = True):
        return self.get_E(wl = wl, nu = nu, atten = atten) / self.E_p(wl, nu)
    
    # Returns attenuated flux per spaxel (T_h * T_d * \Phi_{sp})
    # This is actually a spectral density (W/m)
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

        e[np.where(e < 0)] = 0

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
    
    def getTexpDistribution(self, wl, count_limit, N = 1000):
        sim = TExpSimulator(self, wl, count_limit, N)

        print("Integration time estimate: {0:g} s".format(sim.get_texp_approx()))
        while not sim.done():
            print(fr'Calculating [{sim.progress() * 1e2:.0f} % completed]', end = '\r')
            sim.work(500)
        print(fr'Calculating [{sim.progress() * 1e2:.0f} % completed]', end = '\n')

        return sim.get_result()


