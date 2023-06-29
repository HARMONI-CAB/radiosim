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

import sys
import numpy as np
from graphviz import Digraph, Source
import io
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

import radiosim.AllPassResponse
import radiosim.PowerSpectrum
import radiosim.AttenuatedSpectrum
import radiosim.ISRadianceSpectrum
import radiosim.IsotropicRadiatorSpectrum
import radiosim.OverlappedSpectrum

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
        self.window.changed.connect(self.on_changed)

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
                    title  = 'CCD saturation time probability distribution',
                    xlabel = 'Time to saturation [s]',
                    ylabel = fr'Probability density $p(t|{{c = {self.max_c}}})$',
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

    def get_graphviz(self):
        graph = '''
        digraph {
            rotate=90;
	        node [style=filled, color="#505050", fillcolor=white, fontname="Helvetica", fontsize = 12];
            edge [fontname="Helvetica", color="#505050", constaint=false];
        '''

        role       = 'cal' if self.config.cal_select else 'telescope'
        response   = self.make_current_response()
        lamp_nodes = []
        count = 0

        for lamp in self.config.lamps.keys():
            config   = self.config.lamps[lamp]
            spectrum = self.params.get_lamp(lamp)
            if config.is_on and spectrum.test_role(role):
                lamp_node = fr'lamp_{count}'
                count += 1
                lamp_nodes.append(lamp_node)
                intensity = int(255 - config.attenuation * 2.55)
                color     = '#ffffff' if intensity < 127 else '#000000'
                fillcolor = fr'#{intensity:02x}{intensity:02x}00'
                graph += f'{lamp_node} [shape=ellipse, fillcolor="{fillcolor}", label=<<font color="{color}">{lamp}</font>>];\n'

        coating = self.get_selected_coating()
        color = coating._color

        if self.config.cal_select:
            html   = f'Integrating Sphere\n{coating._name}'
            graph += f'input [shape=circle, fillcolor="white:{color}", gradientangle=0, style=radial, label = "{html}"];\n'
        else:
            html   = f'<b>ELT</b><br />{self.config.telescope.focal_length} / {self.config.telescope.aperture}'
            graph += f'input [shape=cylinder, fillcolor="white", rotate=90, height=2, width=2, label = <{html}>];\n'
        
        graph += response.get_graphviz()

        for lamp in lamp_nodes:
            graph += f'  {lamp} -> input;\n'
        
        graph += f'  input -> {response.get_entrance_node_name()};\n'

        graph += '}'

        return graph

    def refresh_instrument_graph(self):
        dot = Source(self.get_graphviz(), format = 'svg')
        data = io.StringIO()

        data.write( dot.pipe().decode('utf-8') )

        self.window.set_instrument_svg(data.getvalue())
        
    def make_current_response(self):
        return self.params.make_response(
            grating = self.config.grating, 
            ao = self.config.aomode,
            cal = self.config.cal_select)

    def get_selected_coating(self):
        # Initialize integrating sphere
        if self.config.is_coating is not None:
            coating = self.params.get_stage(self.config.is_coating)
        else:
            coating = radiosim.AllPassResponse()
            coating.set_label("Ideal reflector")
        
        return coating

    def make_cal_mode_spectrum(self):
        #
        # The generation of a CAL mode spectrum works assuming that there is
        # certain unstructured power input that is transformed into a Lambertian
        # surface that feeds the Calibration Module's Offner. The sources can
        # be either pure power spectrums or isotropic radiators.
        #
        coating  = self.get_selected_coating()

        sphere  = radiosim.ISRadianceSpectrum(
            self.config.is_radius, 
            .25 * np.pi * self.config.is_aperture ** 2,
            coating)
        
        # Spectrum coming from all lamps
        self.lamp_text = ''
        for lamp in self.config.lamps.keys():
            config = self.config.lamps[lamp]
            if config.is_on:
                lamp_spectrum = self.params.get_lamp(lamp)

                if lamp_spectrum.test_role('cal'):
                    if len(self.lamp_text) > 0:
                        self.lamp_text += ' + '
                    self.lamp_text += lamp
                    

                    # Power defined source: defined "as-is"
                    if issubclass(type(lamp_spectrum), radiosim.PowerSpectrum):
                        lamp_radiator = lamp_spectrum
                    else:
                        # Radiance-defined source: defined as an isotropic radiator
                        lamp_radiator = radiosim.IsotropicRadiatorSpectrum(
                            config.effective_area,
                            lamp_spectrum)

                    if config.power is not None:
                        lamp_spectrum.adjust_power(config.power)
                    lamp_radiator.set_attenuation(config.attenuation * 1e-2)
                    sphere.push_spectrum(lamp_radiator)

        # The "attenuated spectrum" is what is going to determine how much flux
        # is extracted from the sphere's output. The "set_fnum" will determine 
        # the size of the light cone, from which we can determine the surface
        # density of power. I.e. the irradiance.
        spectrum = radiosim.AttenuatedSpectrum(sphere)
        spectrum.set_fnum(self.config.offner_f)
        return spectrum

    def make_obs_mode_spectrum(self):
        #
        # The generation of an observation mode spectrum assumes that there is
        # certain radiance distribution in the sky with no spatial structure
        # (i.e. we are at the optical infinity - the wavefronts are flat). It
        # also assumes that the radiance of the selected pixel is representative
        # of its surroundings, so that the effect of the PSF is low.
        #

        mas2rad = 4.8481368e-09 # 1 mas = 4.8481368e-09 rad

        sky = radiosim.OverlappedSpectrum()

        # Spectrum coming from all lamps
        self.lamp_text = ''
        for lamp in self.config.lamps.keys():
            config = self.config.lamps[lamp]
            if config.is_on:
                lamp_spectrum = self.params.get_lamp(lamp)

                if lamp_spectrum.test_role('telescope'):
                    if len(self.lamp_text) > 0:
                        self.lamp_text += ' + '
                    self.lamp_text += lamp
                    
                    if issubclass(type(lamp_spectrum), radiosim.PowerSpectrum):
                        raise RuntimeError("Power spectrums are not allowed as sky sources")
                    
                    sky.push_spectrum(lamp_spectrum)

        # In observation mode, we already have the size of our pixel in the sky.
        # This means that we can convert directly from radiance to irradiance
        # by multiplying the surface intensity by the spaxel scale.
        spectrum = radiosim.AttenuatedSpectrum(sky)
        spectrum.set_spaxel(self.config.scale[0] * mas2rad, self.config.scale[1] * mas2rad)
        spectrum.set_attenuation(1 - self.config.telescope.efficiency)
        return spectrum

    def simulate_spectrum(self):
        self.config = self.window.get_config()
        self.refresh_instrument_graph()

        self.x_axis_name, self.x_axis_units = self.window.get_x_axis_selection()
        self.y_axis_name, self.y_axis_units = self.window.get_y_axis_selection()

        # Initialize optical train
        response = self.make_current_response()

        if self.config.cal_select:
            spectrum = self.make_cal_mode_spectrum()
            dimRelX  = self.config.scale[0] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ALONG)
            dimRelY  = self.config.scale[1] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ACROSS)
            A_sp     = self.config.detector.pixel_size ** 2 * dimRelX * dimRelY
        else:
            spectrum = self.make_obs_mode_spectrum()
            A_sp     = self.config.telescope.collecting_area
            
        spectrum.push_filter(response)
        self.spectrum = spectrum

        # Initialize detector

        grating = self.params.get_grating(self.config.grating)
        self.det = radiosim.DetectorSimulator(
                spectrum,
                A_sp    = A_sp,
                R       = grating[2],
                binning = self.config.binning,
                pxPerDeltaL = self.config.lambda_sampling,
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
            K = 1e-12 # Hz per THz
            x  = nu * 1e12 # In THz
        else:
            wl = np.linspace(lambda_min, lambda_max, 1000)
            nu = None
            K  = 1e-6 # m per µm
            x  = wl * 1e6 # In µm

        # Decide what to paint
        type   = self.config.type
        y_axis = self.config.y_axis
        tdesc  = self.params.get_spectrum_type_desc(type)

        label = self.window.get_custom_plot_label()
        if type == 'is_out':
            if label is None:
                label = fr'{self.lamp_text} ({tdesc}, {self.config.grating}, {self.config.aomode})'
            if y_axis == 'spect_E':
                y = K * self.det.get_E(wl = wl, nu = nu, atten = False)
            elif y_axis == 'photon_F':
                y = K * self.det.get_photon_flux(wl, nu, atten = False)
            else:
                raise Exception(fr'Invalid quantity {type}:{y_axis}')
        elif type == 'detector':
            if label is None:
                label = fr'{self.lamp_text} ({tdesc}, {self.config.grating}, {self.config.aomode})'
            if y_axis == 'spect_E':
                y = K * self.det.get_E(wl = wl, nu = nu, atten = True)
            elif y_axis == 'photon_F':
                y = K * self.det.get_photon_flux(wl, nu, atten = True)
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
            if label is None:
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
    
    def on_changed(self):
        self.config = self.window.get_config()
        self.refresh_instrument_graph()

def startSimUi(params):
    ui = SimUI()

    # Initialization done, set some default config
    ui.apply_params(params)
    ui.set_config(SimulationConfig())

    return ui.run()



