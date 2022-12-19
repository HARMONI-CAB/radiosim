import sys
import numpy as np
from PyQt6 import QtWidgets
from PyQt6.QtCore import QObject
from .SimUiWindow import SimUiWindow
from radiosim import SimulationConfig, Parameters
import radiosim.DetectorSimulator
from radiosim.Parameters import \
    HARMONI_FINEST_SPAXEL_SIZE, HARMONI_PX_PER_SP_ALONG, \
    HARMONI_PX_PER_SP_ACROSS, HARMONI_PX_AREA
import radiosim.AttenuatedSpectrum

class SimUI(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = QtWidgets.QApplication(sys.argv)
        self.config = SimulationConfig()
        self.params = Parameters()
        self.window = SimUiWindow()
        self.window.plotSpectrum.connect(self.on_plot_spectrum)
        self.window.overlaySpectrum.connect(self.on_overlay_spectrum)

    def apply_params(self, params):
        self.params = params
        self.window.apply_params(params)

    def set_config(self, config):
        self.config = config
        self.window.set_config(self.config)

    def simulate_spectrum(self):
        self.config = self.window.get_config()

        # Initialize optical train
        response = self.params.make_response(
            grating = self.config.grating, 
            ao = self.config.aomode)

        # Initialize spectrum
        spectrum = radiosim.AttenuatedSpectrum(self.params.get_lamp(self.config.lamp1.config))
        spectrum.push_filter(response)
        spectrum.set_fnum(self.config.f)

        if self.config.lamp1.power is not None:
            spectrum.adjust_power(self.config.lamp1.power)
        
        # Initialize detector
        dimRelX = self.config.scale[0] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ALONG)
        dimRelY = self.config.scale[1] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ACROSS)
        A_sp    = HARMONI_PX_AREA * dimRelX * dimRelY

        grating = self.params.get_grating(self.config.grating)
        self.det = radiosim.DetectorSimulator(
                spectrum,
                A_sp    = A_sp,
                R       = grating[2],
                poisson = self.config.noisy,
                G       = self.config.G,
                ron     = self.config.ron)
        
    def plot_spectrum_result(self):
        t_exp = self.config.t_exp
        grating = self.params.get_grating(self.config.grating)
        lambda_min = grating[3]
        lambda_max = grating[4]
        counts     = self.config.y_axis == 'counts'

        if t_exp < 0:
            exps = [5, 10, 30, 60, 120]
        else:
            exps = [t_exp]

        wl = np.linspace(lambda_min, lambda_max, 1000)

        for t in exps:
            if counts:
                y = self.det.countsPerPixel(wl = wl, t = t)
            else:
                y = self.det.electronsPerPixel(wl = wl, t = t)
            print('Plot!')
            self.window.set_plot(
                wl * 1e6, 
                y, 
                xlabel = 'Wavelength ($\mu m$)',
                ylabel = 'ADC output' if self.config == 'counts' else 'Total electrons',
                xlim = [lambda_min * 1e6, lambda_max * 1e6])

    def run(self):
        self.window.show()
        return self.app.exec()

    ################################# Slots ####################################
    def on_plot_spectrum(self):
        print('Plot spectrum!')
        self.simulate_spectrum()
        self.plot_spectrum_result()
        pass

    def on_overlay_spectrum(self):
        print('Overlay spectrum!')
        pass

def startSimUi(params):
    ui = SimUI()

    # Initialization done, set some default config
    ui.apply_params(params)
    ui.set_config(SimulationConfig())

    return ui.run()



