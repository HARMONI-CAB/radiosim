import matplotlib as matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams.update({'font.size': 8})

SPEED_OF_LIGHT  = 299792458 # m / s

class SpectrumPainter:
    def __init__(self, title = "Untitled source"):
        self.title    = title

    def plot(
        self,
        spectrum,
        desc = 'Untitled source',
        start = 400e-9,
        end = 2.5e-6,
        step = 1e-9,
        ax = None,
        log = False,
        photons = False,
        frequency = False):
        if ax is None:
            plt.figure()
            ax = plt.gca()

        N = int((end - start) / step)

        if frequency:
            wl = None
            nu = np.linspace(SPEED_OF_LIGHT / end, SPEED_OF_LIGHT / start, N)
            units = 'THz'
            Cx = 1e12  # Hz per THz
            x  = nu / Cx
            xlabel = 'Frequency ($' + units + '$)'
        else:
            wl = np.linspace(start, end, N)
            nu = None
            units  = '{\mu}m'
            Cx = 1e-6 # m per µm
            x  = wl / Cx
            xlabel = 'Wavelength ($' + units + '$)'

        if photons:
            y = spectrum.photons(wl = wl, nu = nu) * Cx
            ylabel = 'Photon field ($\gamma m^{-2} sr^{-1} {' + units + '}^{-1} s^{-1}$)'
        else:
            y = spectrum.I(wl = wl, nu = nu) * Cx
            ylabel = 'Spectral radiance ($W m^{-2} sr^{-1} {' + units + '}^{-1}$)'

        ax.plot(x, y, label = desc)

        ax.set_ylabel(ylabel)
        ax.set_xlabel(xlabel)
        ax.set_xlim([x[0], x[-1]])
        

        ax.grid(True)
        ax.legend()
        ax.set_title(self.title)
        if log:
            ax.set_yscale('log')
    
    def compare_to_planck(
        self,
        spectrum,
        desc = 'Untitled source',
        start = 400e-9,
        end = 2.5e-6,
        step = 1e-9,
        ax = None,
        log = False,
        frequency = False):

        N = int((end - start) / step)

        if frequency:
            wl = None
            nu = np.linspace(SPEED_OF_LIGHT / end, SPEED_OF_LIGHT / start, N)
            units = 'THz'
            Cx = 1e12  # Hz per THz
            x  = nu / Cx
            xlabel = 'Frequency ($' + units + '$)'
            ylabel = '$I_\nu / B_\nu$'
        else:
            wl = np.linspace(start, end, N)
            nu = None
            units  = '{\mu}m'
            Cx = 1e-6 # m per µm
            x  = wl / Cx
            xlabel = 'Wavelength ($' + units + '$)'
            ylabel = '$I_\lambda / B_\lambda$'
        
        T = spectrum.wien_T()
        B = spectrum.planck(wl = wl, nu = nu) * Cx
        I = spectrum.I(wl = wl, nu = nu) * Cx

        y = I / B

        ax.plot(x, y, label = 'T = ${0:g}$ K'.format(T))

        ax.set_ylabel(ylabel)
        ax.set_xlabel(xlabel)
        ax.set_xlim([x[0], x[-1]])
        
        ax.grid(True)
        ax.legend()
        ax.set_title(self.title)
        if log:
            ax.set_yscale('log')
        