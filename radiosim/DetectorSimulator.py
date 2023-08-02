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
from .DetectorPixel import DetectorPixel

from scipy.special import erf

class TExpSimulator:
    def __init__(self, det, wl, count_limit, N = 1000):
        if isinstance(wl, float):
            wl = np.array([wl])
        
        self.det         = det
        self.Ie          = self.det.electronRatePerPixel(wl = wl)
        self.texp_approx = self.det.getMaxTexp(wl = wl, count_limit = count_limit)[0]
        self.texp_min    = np.max([0., self.texp_approx - self.texp_approx ** .5])
        self.texp_max    = self.texp_approx + self.texp_approx ** .5
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
            sigma = self.det.ron(t) / self.det.gain()
            rate = self.Ie * t
            max  = 5 * int(np.ceil(rate))
            nes  = np.linspace(0, max, max + 1)
            mus  = nes / self.det.gain()
            
            self.p[i] = np.dot(
                self.poissonDistribution(nes, rate),
                self.normalInt(self.ca, self.cb, sigma = sigma, mu = mus))
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
        pixel: DetectorPixel = None,
        spectrum = None,
        area = 980,
        pxPerDeltaL = 2.2,
        binning = 1,
        R = 18000,
        debug_etendue = False):
        self.area        = area
        self.pxPerDeltaL = pxPerDeltaL
        self.spectrum    = spectrum
        self.R           = R
        self.pixel       = pixel
        self.binning     = binning

        if debug_etendue:
            omega = spectrum.get_Omega() * (180 * 3600 / np.pi) ** 2
            print(fr"Provided area: {area:.2g} m^2")
            print(fr"Provided Omega: {omega:.2g} arcsec^2")
            etendue = area * omega
            print(fr"Detector étendue: {etendue} m²arcsec²")
        
    def assert_spectrum(self):
        if self.spectrum is None:
            raise Exception("No spectrum was defined")

    def set_R(self, R):
        self.R = R
    
    def set_spectrum(self, spectrum):
        self.spectrum = spectrum

    def get_I(self, wl = None, nu = None, atten = True):
        """Returns attenuated? radiance (W/(m^2 m sr))"""
        if atten:
            spectrum = self.spectrum
        else:
            spectrum = self.spectrum.get_source_spectrum()
        
        return spectrum.I(wl = wl, nu = nu)

    def get_E(self, wl = None, nu = None, atten = True):
        """Returns attenuated? flux (W/(m^2 m))"""
        if atten:
            spectrum = self.spectrum
        else:
            spectrum = self.spectrum.get_source_spectrum()
        
        return spectrum.E(wl = wl, nu = nu)
    
    def get_photon_radiance(self, wl = None, nu = None, atten = True):
        """Returns attenuated? photon radiance (photons/(m^2 m sr))"""
        return self.get_I(wl = wl, nu = nu, atten = atten) / self.E_p(wl, nu)

    def get_photon_flux(self, wl = None, nu = None, atten = True):
        """Returns attenuated? photon flux (photons/(m^2 m))"""
        return self.get_E(wl = wl, nu = nu, atten = atten) / self.E_p(wl, nu)
    
    def fluxPerSpaxel(self, wl = None, nu = None, atten = True):
        """
        Returns attenuated flux per spaxel (T_h * T_d * \Phi_{sp})
        This is actually a spectral density (W/m)
        """
        self.assert_spectrum()
        return self.get_E(wl = wl, nu = nu, atten = atten) * self.area

    def Dh(self, wl = None, nu = None):
        """
        Returns band dispersion (D_h). This is actually \\Delta\\lambda
        (m) or \\Delta\\nu (Hz) across the spectral dimension 
        """
        self.assert_spectrum()

        #
        # Note that, since resolution must not depend on units:
        #
        # R = lambda / dLambda = nu / dNu
        #
        # dLambda = lambda / R
        # dNu     = nu     / R
        #
        # Now, as a consequence of the dispersion and since each pixel must
        # nyquist-sample each wavelength (frequency) by pxPerDeltaL (e.g. 2.2),
        # each resolution element dLambda (dNu) gets projected on 2.2 pixels.
        #
        # This means that each pixel spans dLambda / 2.2 (dNu / 2.2)
        #

        axis = wl if wl is not None else nu
        if isinstance(axis, tuple) or isinstance(axis, list):
            axis = np.array(axis)
        elif isinstance(axis, float):
            axis = np.array([axis])
        
        res  = np.ones(axis.shape) * (axis[0] + axis[-1]) / (2 * self.R)
        return res / (self.pxPerDeltaL)

    def integratedFluxPerPixel(self, wl = None, nu = None, atten = True):
        """
        Returns incident spectral flux per pixel (\Phi_{px})
        Please note this has units of W!! This is NOT a spectral density (W/m)
        """
        self.assert_spectrum()

        # According to HRM-00509, \Phi_{px} is computed as T        pass_h * T_d * D_h * \Phi_{sp}
        Dh = self.Dh(wl = wl, nu = nu)

        return Dh * self.fluxPerSpaxel(wl = wl, nu = nu, atten = atten)

    def E_p(self, wl = None, nu = None):
        """
        Returns photon energy
        """
        if nu is None:
            if wl is None:
                raise Exception("Either frequency or wavelength must be provided")
            nu = SPEED_OF_LIGHT / wl
        
        return PLANCK_CONSTANT * nu

    def photonFluxPerPixel(self, wl = None, nu = None, atten = True):
        """
        Returns incident spectral flux per pixel, in photons
        """
        self.assert_spectrum()

        ret = self.integratedFluxPerPixel(wl = wl, nu = nu, atten = atten) / self.E_p(wl = wl, nu = nu)
        nans = np.isnan(ret)

        if len(nans.shape) > 0:
            ret[nans] = 0
        
        return ret

    def electronRatePerPixel(self, wl = None, nu = None):
        """
        Returns the generated photoelectron rate
        """
        self.assert_spectrum()
        photons = self.photonFluxPerPixel(wl = wl, nu = nu) * self.binning
        return self.pixel.electronRatePerPixel(photons, wl, nu)

    def electronsPerPixel(self, wl = None, nu = None, t = 1, disable_noise = False):
        """
        Returns the number of electrons per pixel
        """
        rate = self.electronRatePerPixel(wl, nu)
        return self.pixel.electronsPerPixel(rate, wl, nu, t, not disable_noise)

    def countsPerPixel(self, wl = None, nu = None, t = 1, disable_noise = False):
        """
        Returns the simulated number of counts per pixel
        """
        electrons = self.electronsPerPixel(wl, nu, t, disable_noise)
        return self.pixel.countsPerPixel(electrons, wl, nu, not disable_noise)
    
    def ron(self, t):
        return self.pixel.ron(t)
    
    def gain(self):
        return self.pixel.gain()
    
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
                max_lambda = wl[max_ndx]
                max_nu     = SPEED_OF_LIGHT / max_lambda
            elif nu is not None:
                max_nu     = nu[max_ndx]
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


