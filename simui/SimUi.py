import sys
import numpy as np
from PyQt6 import QtWidgets
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import QMessageBox, QApplication
from .SimUiWindow import SimUiWindow
from radiosim import SimulationConfig, Parameters
import radiosim.DetectorSimulator
from radiosim.DetectorSimulator import TExpSimulator
from radiosim import SPEED_OF_LIGHT
from radiosim.Parameters import \
    HARMONI_FINEST_SPAXEL_SIZE, HARMONI_PX_PER_SP_ALONG, \
    HARMONI_PX_PER_SP_ACROSS, HARMONI_PX_AREA
import radiosim.AttenuatedSpectrum, radiosim.OverlappedSpectrum

class SimUI(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = QtWidgets.QApplication(sys.argv)
        self.config = SimulationConfig()
        self.params = Parameters()
        self.window = SimUiWindow()
        self.connect_all()

    def connect_all(self):
        self.window.plotSpectrum.connect(self.on_plot_spectrum)
        self.window.overlaySpectrum.connect(self.on_overlay_spectrum)
        self.window.plotTexp.connect(self.on_plot_texp)
        self.window.overlayTexp.connect(self.on_overlay_texp)
        self.window.stopTexp.connect(self.on_texp_cancelled)
        
    def apply_params(self, params):
        self.params = params
        self.window.apply_params(params)

    def set_config(self, config):
        self.config = config
        self.window.set_config(self.config)

    def run_texp_simulation(self):
        self.simulate_spectrum()
        
        if self.config.texp_use_band:
            grating = self.params.get_grating(self.config.texp_band)
            lambda_min = grating[3]
            lambda_max = grating[4]
            steps = self.config.texp_iters

            wl = np.linspace(lambda_min, lambda_max, steps)
            self.target_wl = self.spectrum.argmax_photons(wl = wl)
        else:
            self.target_wl = self.config.texp_wl
        
        self.max_c = self.config.saturation

        simulator = TExpSimulator(self.det, self.target_wl, self.max_c, self.config.texp_iters)

        self.tExpCancelled = False
        
        ####################### Simulation loop start ##########################
        self.window.set_texp_simul_running(True)
        while not simulator.done() and not self.tExpCancelled:
            simulator.work()
            self.window.set_texp_simul_progress(simulator.progress())
            QApplication.processEvents()
        self.window.set_texp_simul_running(False)
        ######################## Simulation loop end ###########################

        if simulator.done():
            return simulator.get_result()
        else:
            return None

    def simulate_texp_and_plot(self):
        prob = self.run_texp_simulation()

        if prob is not None:
            try:
                self.window.set_texp_plot(
                    prob[0, :],
                    prob[1, :],
                    label = '$\lambda = {0:1.3f}{{\mu}}m$, $c_{{max}}$ = {1} ADU, scale ${2}x{3}$'.format(
                        self.target_wl * 1e6,
                        self.max_c,
                        self.config.scale[0],
                        self.config.scale[1]
                    ))
            except Exception as e:
                dialog = QMessageBox(
                    parent = self, 
                    icon = QMessageBox.Icon.Warning,
                    text=fr"Failed to calculate saturation time distribution")
                dialog.setWindowTitle("Simulation error")
                dialog.exec()   # Stores the return value for the button pressed

    def simulate_spectrum(self):
        self.config = self.window.get_config()

        print('------------------------------------------')
        self.config.save_to_file('/dev/stdout')
        print('------------------------------------------')

        self.x_axis_name, self.x_axis_units = self.window.get_x_axis_selection()
        self.y_axis_name, self.y_axis_units = self.window.get_y_axis_selection()

        # Initialize optical train
        response = self.params.make_response(
            grating = self.config.grating, 
            ao = self.config.aomode)

        # Initialize spectrum
        overlapped = radiosim.OverlappedSpectrum()
        
        # Spectrum coming from all lamps
        self.lamp_text = ''
        for lamp in self.config.lamps.keys():
            config = self.config.lamps[lamp]
            if config.is_on:
                if len(self.lamp_text) > 0:
                    self.lamp_text += ' + '
                self.lamp_text += lamp
                
                lamp_spectrum = self.params.get_lamp(lamp)
                atten_spectrum = radiosim.AttenuatedSpectrum(lamp_spectrum)
                if config.power is not None:
                    lamp_spectrum.adjust_power(config.power)
                atten_spectrum.set_attenuation(config.attenuation * 1e-2)
                overlapped.push_spectrum(atten_spectrum)

        spectrum = radiosim.AttenuatedSpectrum(overlapped)
        spectrum.push_filter(response)
        spectrum.set_fnum(self.config.detector.f)
        
        self.spectrum = spectrum

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
        tdesc  = self.params.get_spectrum_type_desc(type)

        if type == 'is_out':
            label = fr'{self.lamp_text} ({tdesc}, {self.config.grating}, {self.config.aomode})'
            if y_axis == 'spect_E':
                y = self.det.get_E(wl = wl, nu = nu, atten = False)
            elif y_axis == 'photon_F':
                y = self.det.get_photon_flux(wl, nu, atten = False)
            else:
                raise Exception(fr'Invalid quantity {type}:{y_axis}')
        elif type == 'detector':
            label = fr'{self.lamp_text} ({tdesc}, {self.config.grating}, {self.config.aomode})'
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
            y = stage.get_t_matrix(wl)
            label = fr'{y_axis} at {self.config.grating}'
        else:
            raise Exception(fr'Invalid spectrum type {type}')
        
        

        self.window.spectrum_plot(
            x,
            y,
            x_desc  = self.x_axis_name,
            x_units = self.x_axis_units,
            y_desc  = self.y_axis_name,
            y_units = self.y_axis_units,
            label   = label)

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

    def on_plot_texp(self):
        self.window.clear_texp()
        self.on_overlay_texp()

    def on_overlay_texp(self):
        self.simulate_texp_and_plot()

    def on_texp_cancelled(self):
        self.tExpCancelled = True
    
def startSimUi(params):
    ui = SimUI()

    # Initialization done, set some default config
    ui.apply_params(params)
    ui.set_config(SimulationConfig())

    return ui.run()



