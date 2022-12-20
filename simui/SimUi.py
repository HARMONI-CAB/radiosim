import sys
import numpy as np
from PyQt6 import QtWidgets
from PyQt6.QtCore import QObject
from .SimUiWindow import SimUiWindow
from radiosim import SimulationConfig, Parameters
import radiosim.DetectorSimulator
from radiosim import SPEED_OF_LIGHT
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

        self.config.save_to_file('/dev/stdout')
        self.x_axis_name, self.x_axis_units = self.window.get_x_axis_selection()
        self.y_axis_name, self.y_axis_units = self.window.get_y_axis_selection()

        # Initialize optical train
        response = self.params.make_response(
            grating = self.config.grating, 
            ao = self.config.aomode)

        # Initialize spectrum
        spectrum = radiosim.AttenuatedSpectrum(self.params.get_lamp(self.config.lamp1.config))
        spectrum.push_filter(response)
        spectrum.set_fnum(self.config.detector.f)

        if self.config.lamp1.power is not None:
            spectrum.adjust_power(self.config.lamp1.power)
        
        # Initialize detector
        dimRelX = self.config.scale[0] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ALONG)
        dimRelY = self.config.scale[1] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ACROSS)
        A_sp    = self.config.detector.pixel_size ** 2 * dimRelX * dimRelY

        grating = self.params.get_grating(self.config.grating)
        self.det = radiosim.DetectorSimulator(
                spectrum,
                A_sp    = A_sp,
                R       = grating[2],
                poisson = self.config.noisy,
                QE      = self.config.detector.QE,
                G       = self.config.detector.G,
                ron     = self.config.detector.ron)
        
    def plot_spectrum_result(self):
        t_exp = self.config.t_exp
        grating = self.params.get_grating(self.config.grating)
        lambda_min = grating[3]
        lambda_max = grating[4]


        if self.config.x_axis == 'frequency':
            nu = np.linspace(SPEED_OF_LIGHT / lambda_max, SPEED_OF_LIGHT / lambda_min, 1000)
            wl = None
            x  = nu * 1e12 # In THz
        else:
            wl = np.linspace(lambda_min, lambda_max, 1000)
            nu = None
            x  = wl * 1e6 # In µm

        # Decide what to paint
        type   = self.config.type
        y_axis = self.config.y_axis

        if type == 'is_out':
            if y_axis == 'spect_E':
                y = self.det.get_E(wl = wl, nu = nu, atten = False)
            elif y_axis == 'photon_F':
                y = self.det.get_photon_flux(wl, nu, atten = False)
            else:
                raise Exception(fr'Invalid quantity {type}:{y_axis}')
        elif type == 'detector':
            if y_axis == 'spect_E':
                y = self.det.get_E(wl = wl, nu = nu, atten = True)
            elif y_axis == 'photon_F':
                y = self.det.get_photon_flux(wl, nu, atten = True)
            elif y_axis == 'dedt_Px':
                y = self.det.electronRatePerPixel(wl = wl, nu = nu)
            elif y_axis == 'electrons':
                y = self.det.electronsPerPixel(wl = wl, nu = nu, t = t_exp)
            elif y_axis == 'counts':
                y = self.det.countsPerPixel(
                    wl = wl,
                    nu = nu,
                    t = t_exp,
                    disable_noise = not self.config.noisy)
            else:
                raise Exception(fr'Invalid quantity {type}:{y_axis}')
        elif type == 'transmission':
            stage = self.params.get_stage(y_axis)
            if wl is None:
                wl = SPEED_OF_LIGHT / nu
            y = stage.get_t(wl)
        else:
            raise Exception(fr'Invalid spectrum type {type}')
        
        tdesc   = self.params.get_spectrum_type_desc(type)
        desc, _ = self.params.get_spectrum_desc_for_type(type, y_axis)

        self.window.spectrum_plot(
            x,
            y,
            x_desc  = self.x_axis_name,
            x_units = self.x_axis_units,
            y_desc  = self.y_axis_name,
            y_units = self.y_axis_units,
            label   = fr'{desc} ({tdesc}, {self.config.grating}, {self.config.aomode})')

    def run(self):
        self.window.show()
        return self.app.exec()

    ################################# Slots ####################################
    def on_plot_spectrum(self):
        self.window.clear_plot()
        self.on_overlay_spectrum()

    def on_overlay_spectrum(self):
        self.simulate_spectrum()
        self.plot_spectrum_result()

def startSimUi(params):
    ui = SimUI()

    # Initialization done, set some default config
    ui.apply_params(params)
    ui.set_config(SimulationConfig())

    return ui.run()



