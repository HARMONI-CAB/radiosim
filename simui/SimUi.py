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
    HARMONI_FINEST_SPAXEL_SIZE, HARMONI_INST_FNUM

import radiosim.AllPassResponse
import radiosim.PowerSpectrum
import radiosim.AttenuatedSpectrum
import radiosim.ISRadianceSpectrum
import radiosim.IsotropicRadiatorSpectrum
import radiosim.OverlappedSpectrum
import radiosim.AttenuatedPowerSpectrum
import radiosim.CompoundResponse
import radiosim.CCDPixel

ARCSEC2_PER_SR = (180 * 3600 / np.pi) ** 2

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
        self.create_simulator()
        
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

        simulator = TExpSimulator(self.detsim, self.target_wl, self.max_c, self.config.texp_iters)

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
        try:
            prob = self.run_texp_simulation()
            if prob is not None:
                
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
                parent = self.window, 
                icon = QMessageBox.Icon.Warning,
                text=fr"Failed to calculate saturation time distribution: {str(e)}")
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

                if self.config.cal_select:
                    respPerM      = self.params.get_fiber(config.fiber)

                    if type(respPerM) is radiosim.AllPassResponse:
                        graph += f'{lamp_node} [shape=ellipse, fillcolor="{fillcolor}", label=<<font color="{color}">{lamp}</font>>];\n'
                    else:
                        fiberResponse = radiosim.CompoundResponse()
                        fiberResponse.push_front(respPerM)
                        fiberResponse.set_multiplicity(config.fiber_length)
                        ffill, ftext   = fiberResponse.calc_color_lazy()

                        graph += f'{lamp_node}_lamp [shape=ellipse, fillcolor="{fillcolor}", label=<<font color="{color}">{lamp}</font>>];\n'
                        graph += f'{lamp_node} [shape=rectangle, fillcolor="{ffill}", color="{ftext}", label="     {config.fiber}     \n{config.fiber_length:.2g} m"];\n'
                        graph += f'{lamp_node}_lamp -> {lamp_node};\n'
                else:
                    graph += f'{lamp_node} [shape=rectangle, fillcolor="{fillcolor}", label=<<font color="{color}">{lamp}</font>>];\n'

        coating = self.get_selected_coating()
        fillcolor = coating._color
        color     = coating._text

        if self.config.cal_select:
            html   = f'Integrating Sphere\n{coating._name}'
            graph += f'input [shape=circle, fillcolor="white:{fillcolor}", fontcolor="{color}", gradientangle=0, style=radial, label = "{html}"];\n'
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
        
    def get_sky_fnum(self):
        fnum_tel = self.config.telescope.focal_length / self.config.telescope.aperture
        xscale = self.config.scale[0]
        yscale = self.config.scale[1]
        k      = HARMONI_FINEST_SPAXEL_SIZE / np.sqrt(xscale * yscale)
        return fnum_tel * k
    
    def get_cal_fnum(self):
        xscale = self.config.scale[0]
        yscale = self.config.scale[1]
        k      = HARMONI_FINEST_SPAXEL_SIZE / np.sqrt(xscale * yscale)
        return self.config.offner_f * k
    
    def make_current_response(self):
        resp_config = {}
        airmass = 1.1

        if self.config.cal_select:
            angle   = self.config.telescope.zenith_distance
            toRad   = angle / 180. * np.pi
            airmass = 1. / np.cos(toRad)
        
        resp_config['grating'] = self.config.grating
        resp_config['ao']      = self.config.aomode
        resp_config['cal']     = self.config.cal_select
        resp_config['airmass'] = airmass

        # Incrementing the scale means that the same pixel covers more sky.
        # This reduces the effective focal length in the involved parts.
        resp_config['fD_tel']  = self.get_sky_fnum()
        resp_config['fD_cal']  = HARMONI_INST_FNUM
        resp_config['fD_ins']  = HARMONI_INST_FNUM
        resp_config['fD_fix']  = HARMONI_INST_FNUM

        return self.params.make_response(resp_config)

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
        aperture = .25 * np.pi * self.config.is_aperture ** 2
        sphere   = radiosim.ISRadianceSpectrum(
            self.config.is_radius, 
            aperture,
            coating)
        
        sphere.set_temperature(self.params.get_temperature('TCal'))

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
                        lamp_radiator.adjust_power(config.power)
                    lamp_radiator.set_attenuation(config.attenuation * 1e-2)

                    # Add fiber effect
                    response = self.params.get_fiber(config.fiber)
                    fiber_spectrum = radiosim.AttenuatedPowerSpectrum(lamp_radiator)
                    fiber_spectrum.push_filter(response)
                    fiber_spectrum.set_multiplicity(config.fiber_length)
                    sphere.push_spectrum(fiber_spectrum)


        spectrum = radiosim.AttenuatedSpectrum(sphere)
        spectrum.set_fnum(self.get_cal_fnum())
        return spectrum

    def make_obs_mode_spectrum(self):
        #
        # The generation of an observation mode spectrum assumes that there is
        # certain radiance distribution in the sky with no spatial structure
        # (i.e. we are at the optical infinity - the wavefronts are flat). It
        # also assumes that the radiance of the selected pixel is representative
        # of its surroundings, so that the effect of the PSF is low.
        #

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
        # This means that we can obtain the etendue directly from the telescope
        # aperture and the projected spaxel
        spectrum = radiosim.AttenuatedSpectrum(sky)
        spectrum.set_fnum(self.get_sky_fnum())

        return spectrum

    def refresh_parameters(self, config):
        # Adjust telescope parameters
        self.params.set_telescope_parameters(
            config.telescope.aperture,
            config.telescope.collecting_area)
        
        # Adjust temperatures
        for temp in self.config.temps.keys():
            self.params.set_temperature(temp, self.config.temps[temp].temperature)

    def create_simulator(self):
        self.config = self.window.get_config()
        self.refresh_parameters(self.config)
        self.refresh_instrument_graph()

        self.x_axis_name, self.x_axis_units = self.window.get_x_axis_selection()
        self.y_axis_name, self.y_axis_units = self.window.get_y_axis_selection()

        # Initialize optical train
        response = self.make_current_response()

        if self.config.bypass_stage is not None:
            response.prune_forward(self.config.bypass_stage)

        if self.config.cal_select:
            spectrum = self.make_cal_mode_spectrum()
        else:
            spectrum = self.make_obs_mode_spectrum()

        spectrum.push_filter(response)
        
        #
        # In order to calculate the power collected by a pixel, two equivalent
        # reasonings are possible:
        #
        # A. Project the spaxel on the sky. Multiply I by Omega(spaxel) to get
        #    the irradiance, and by Area(telescope) to get the total power.
        # B. Calculate the light cone span angles (in X and Y directions)
        #    multiply that to the output irradiance of the focus optics, and
        #    then multiply that by the size of the pixel.
        #
        # We are going to follow A as seems easier to calculate. On the other
        # hand, the dark current is obtained from two sources:
        #
        #    1. Portion of the mechanisms seeing by the detector (this was
        #       measured in 0.2 sr, which corresponds to a cone of 28º deg diameter
        #       approximately.
        #    2. Radiation temperature (hemispherical emission, all 180º)
        #
        # We are going to model background in a separate object, called
        # DetectorPixel. This is going to be an abstract class that will accept
        # a photon flux per pixel and will provide counts, taking into account
        # the size of the pixel and other environmental properties.
        #

        self.spectrum = spectrum
        
        # Initialize detector
        grating = self.params.get_grating(self.config.grating)
        self.detsim = radiosim.DetectorSimulator(
                radiosim.CCDPixel(self.params, self.config),
                spectrum,
                area    = self.config.detector.pixel_size ** 2,
                R       = grating[2],
                pxPerDeltaL = self.config.lambda_sampling,
                binning = self.config.binning)
        
    def plot_spectrum_result(self):
        t_exp = self.config.t_exp
        grating = self.params.get_grating(self.config.grating)
        R          = grating[2]
        lambda_min = grating[3]
        lambda_max = grating[4]
        # Decide what to paint
        type       = self.config.type
        y_axis     = self.config.y_axis
        tdesc      = self.params.get_spectrum_type_desc(type)
        label      = self.window.get_custom_plot_label()
        show_sat   = False
        noiseless  = not self.config.noisy

        do_stem = type == 'detector'
        if do_stem:
            pxPerDeltaL = self.config.lambda_sampling
            dLambda     = .5 * (lambda_max + lambda_min) / (R * pxPerDeltaL)
            steps       = int((lambda_max - lambda_min) / dLambda)
            detWl       = lambda_min+ np.linspace(0, steps - 1, steps) * dLambda

        if self.config.x_axis == 'frequency':
            if do_stem:
                nu = SPEED_OF_LIGHT / detWl[::-1]
            else:
                nu = np.linspace(SPEED_OF_LIGHT / lambda_max, SPEED_OF_LIGHT / lambda_min, 1000)
            wl = None
            K = 1e12        # Hz per THz
            x  = nu * 1e-12 # In THz
        else:
            if do_stem:
                wl = detWl
            else:
                wl = np.linspace(lambda_min, lambda_max, 1000)
            nu = None
            K  = 1e-6     # m per µm
            x  = wl * 1e6 # In µm

        if y_axis == 'photon_I':
            K /= ARCSEC2_PER_SR # Radiances must be /arcsec2

        if type == 'is_out':
            if label is None:
                label = fr'{self.lamp_text} ({tdesc}, {self.config.grating}, {self.config.aomode})'
            if y_axis == 'spect_E':
                y = K * self.detsim.get_E(wl = wl, nu = nu, atten = False)
            elif y_axis == 'photon_I':
                y = K * self.detsim.get_photon_radiance(wl, nu, atten = False)
            elif y_axis == 'photon_F':
                y = K * self.detsim.get_photon_flux(wl, nu, atten = False)
            elif y_axis == 'dphotondt':
                y = self.detsim.photonFluxPerPixel(wl = wl, nu = nu, atten = False)
            else:
                raise Exception(fr'Invalid quantity {type}:{y_axis}')
        elif type == 'detector':
            if label is None:
                label = fr'{self.lamp_text} ({tdesc}, {self.config.grating}, {self.config.aomode})'
            if y_axis == 'spect_E':
                y = K * self.detsim.get_E(wl = wl, nu = nu, atten = True)
            elif y_axis == 'photon_I':
                y = K * self.detsim.get_photon_radiance(wl, nu, atten = True)
            elif y_axis == 'photon_F':
                y = K * self.detsim.get_photon_flux(wl, nu, atten = True)
            elif y_axis == 'dphotondt':
                y = self.detsim.photonFluxPerPixel(wl = wl, nu = nu, atten = True)
            elif y_axis == 'dedt_Px':
                y = self.detsim.electronRatePerPixel(wl = wl, nu = nu)
            elif y_axis == 'electrons':
                y = self.detsim.electronsPerPixel(
                    wl = wl,
                    nu = nu,
                    t = t_exp,
                    disable_noise = noiseless)
            elif y_axis == 'counts':
                show_sat = True
                y = self.detsim.countsPerPixel(
                    wl = wl,
                    nu = nu,
                    t = t_exp,
                    disable_noise = noiseless)
            else:
                raise Exception(fr'Invalid quantity {type}:{y_axis}')
        elif type == 'transmission':
            if y_axis == 'total_response':
                part = self.make_current_response()
                y_desc = 'Instrument response'
            elif y_axis == 'sky':
                part = self.params.get_sky_transmission()
                y_desc = 'Sky transmission'
            else:
                part = self.params.get_transmission(y_axis)
                y_desc = part.get_label()
            if wl is None:
                wl = SPEED_OF_LIGHT / nu
            y = part.get_t_matrix(wl)
            if label is None:
                label = fr'{y_desc} at {self.config.grating}'
        else:
            raise Exception(fr'Invalid spectrum type {type}')
        
        self.window.spectrum_plot(
            x,
            y,
            x_desc  = self.x_axis_name,
            x_units = self.x_axis_units,
            y_desc  = self.y_axis_name,
            y_units = self.y_axis_units,
            label   = label,
            stem    = do_stem)
        
        if show_sat:
            self.window.set_saturation_level(
                self.config.grating,
                x[0],
                x[-1],
                self.config.saturation)
        self.window.set_show_saturation(show_sat)

    def run(self):
        self.window.show()
        return self.app.exec()

    ################################# Slots ####################################
    def on_plot_spectrum(self):
        self.window.clear_plot()
        self.on_overlay_spectrum()

    def on_overlay_spectrum(self):
        self.create_simulator()
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



