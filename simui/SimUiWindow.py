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

import numpy as np
from PyQt6 import QtCore, uic
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox, QDialogButtonBox, QFileDialog, QSpacerItem, QSizePolicy, QLabel
from PyQt6.QtSvgWidgets import QSvgWidget
from radiosim import SimulationConfig, DetectorConfig, TelescopeConfig
from .PlotWidget import PlotWidget
from .CubeChooserDialog import CubeChooserDialog
from .LampControlWidget import LampControlWidget
import os.path
import pathlib
import traceback

from radiosim.Parameters import HARMONI_PIXEL_SIZE, \
    HARMONI_FINEST_SPAXEL_SIZE, HARMONI_PX_PER_SP_ALONG, \
    HARMONI_PX_PER_SP_ACROSS, HARMONI_PX_AREA

class SimUiWindow(QtWidgets.QMainWindow):
    plotSpectrum    = pyqtSignal()
    overlaySpectrum = pyqtSignal()
    plotTexp        = pyqtSignal()
    overlayTexp     = pyqtSignal()
    stopTexp        = pyqtSignal()
    changed         = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/simui.ui", self)
        self.setWindowTitle("QRadioSim - The HARMONI's radiometric simulator")

        self.plotWidget = PlotWidget()
        self.tExpWidget = PlotWidget()
        self.instWidget = QSvgWidget()
        
        self.cubeChooserDialog = CubeChooserDialog(self)

        self.plotStack.insertWidget(1, self.plotWidget)
        self.tExpStack.insertWidget(1, self.tExpWidget)
        self.graphStack.insertWidget(1, self.instWidget)

        self.curr_x_units = None
        self.curr_y_units = None
        self.lamp_widgets = {}
        self.filename = None
        self.changes = False
        self.params = None
        
        self.set_texp_simul_running(False)
        self.refresh_ui_state()
        self.connect_all()
        
        self.changes = False
        self.update_title()

    def update_title(self):
        filename = self.filename
        if filename is None:
            filename = 'No name'
        else:
            filename = os.path.basename(filename)

        title = 'QRadioSim - ' + filename
        
        if self.changes:
            title += '*'
        
        self.setWindowTitle(title)

    def connect_all(self):
        self.spectPlotButton.clicked.connect(self.plotSpectrum)
        self.spectOverlayButton.clicked.connect(self.overlaySpectrum)
        self.spectClearAllbuton.clicked.connect(self.on_plot_clear)
        self.overrideLabelCheck.toggled.connect(self.on_state_widget_changed)
        
        self.instModeCombo.activated.connect(self.on_inst_mode_widget_changed)
        self.focalLengthSpin.valueChanged.connect(self.on_inst_mode_widget_changed)
        self.efficiencySpin.valueChanged.connect(self.on_inst_mode_widget_changed)
        self.apertureSpin.valueChanged.connect(self.on_inst_mode_widget_changed)
        self.collectingAreaSpin.valueChanged.connect(self.on_inst_mode_widget_changed)
        self.zenithSpin.valueChanged.connect(self.on_inst_mode_widget_changed)
        self.moonSlider.valueChanged.connect(self.on_inst_mode_widget_changed)
        self.isCoatingCombo.activated.connect(self.on_inst_mode_widget_changed)
        self.isRadiusSpin.valueChanged.connect(self.on_inst_mode_widget_changed)
        self.isApertureDiamSpin.valueChanged.connect(self.on_inst_mode_widget_changed)
        self.fNSpin.valueChanged.connect(self.on_inst_mode_widget_changed)

        self.spectTypeCombo.activated.connect(self.on_spect_type_changed)


        self.tExpPlotButton.clicked.connect(self.plotTexp)
        self.tExpOverlayButton.clicked.connect(self.overlayTexp)
        self.tExpClearButton.clicked.connect(self.on_texp_clear)
        self.tExpStopButton.clicked.connect(self.stopTexp)

        self.passBandCombo.activated.connect(self.on_state_widget_changed)
        self.tExpPassBandRadio.toggled.connect(self.on_state_widget_changed)
        self.tExpWlSpin.valueChanged.connect(self.on_state_widget_changed)
        self.logScaleCheck.toggled.connect(self.on_log_scale_changed)
        self.lambdaSamplingSpin.valueChanged.connect(self.on_log_scale_changed)
        self.binningSpin.valueChanged.connect(self.on_log_scale_changed)

        self.gratingCombo.activated.connect(self.on_state_widget_changed)
        self.aoModeCombo.activated.connect(self.on_state_widget_changed)
        self.scaleCombo.activated.connect(self.on_state_widget_changed)
        
        self.action_Open.triggered.connect(self.on_open)
        self.action_Save.triggered.connect(self.on_save)
        self.action_Save_as.triggered.connect(self.on_save_as)
        self.action_Quit.triggered.connect(self.on_quit)
        self.action_LoadCube.triggered.connect(self.on_load_cube)
        self.cubeChooserDialog.accepted.connect(self.on_cube_accepted)

    def set_instrument_svg(self, svg):
        self.instWidget.load(QtCore.QByteArray(svg.encode('utf-8')))

        self.instWidget.renderer().setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)

        self.graphStack.setCurrentIndex(1)
        
    def set_texp_simul_running(self, running):
        if not running:
            self.tExpProgressBar.setValue(0)
        self.tExpProgressBar.setEnabled(running)
        self.tExpStopButton.setEnabled(running)

    def set_texp_simul_progress(self, progress):
        self.tExpProgressBar.setValue(int(progress * 1e2))
    
    def clear_plot(self):
        self.plotWidget.clear()
        self.plotStack.setCurrentIndex(0)
        self.curr_x_units = None
        self.curr_y_units = None

    def clear_texp(self):
        self.tExpWidget.clear()
        self.tExpStack.setCurrentIndex(0)
        
    def set_plot(self, *args, xlabel = None, ylabel = None, **kwargs):
        self.plotWidget.plot(*args, xlabel = xlabel, ylabel = ylabel, **kwargs)
        self.plotStack.setCurrentIndex(1)

    def set_texp_plot(self, *args, xlabel = None, ylabel = None, **kwargs):
        self.tExpWidget.plot(*args, xlabel = xlabel, ylabel = ylabel, **kwargs)
        self.tExpStack.setCurrentIndex(1)
    
    def spectrum_plot(self, *args, x_desc, x_units, y_desc, y_units, **kwargs):
        if self.curr_x_units is not None and x_units != self.curr_x_units:
            if not self.ask_yes_no(
                fr'Units of the horizontal axis differ from those of the current plot '
                fr'(current is {self.curr_x_units}, requested is {x_units}). '
                fr'This will clear the current plot. Are you sure?',
                'X axis unit mismatch'):
                return
            self.clear_plot()

        if self.curr_y_units is not None and y_units != self.curr_y_units:
            if not self.ask_yes_no(
                fr'Units of the vertical axis differ from those of the current plot '
                fr'(current is {self.curr_y_units}, requested is {y_units}). '
                fr'This will clear the current plot. Are you sure?',
                'Y axis unit mismatch'):
                return
            self.clear_plot()

        xlabel = fr'{x_desc} [{x_units}]'
        ylabel = fr'{y_desc} [{y_units}]'

        self.curr_x_units = x_units
        self.curr_y_units = y_units

        self.set_plot(*args, xlabel = xlabel, ylabel = ylabel, **kwargs)

    def ask_yes_no(self, text, title):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(title)
        dlg.setText(text)
        dlg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dlg.setIcon(QMessageBox.Icon.Question)
        button = dlg.exec()
        return button == QDialogButtonBox.StandardButton.Yes.value

    def refresh_lamps(self):
        # Remove exiting lamps
        for i in reversed(range(self.lampLayout.count())):
            item = self.lampLayout.itemAt(i)
            if item.widget() is not None:
                item.widget().deleteLater()
            self.lampLayout.removeItem(item)

        for i in reversed(range(self.skyLayout.count())): 
            item = self.skyLayout.itemAt(i)
            if item.widget() is not None:
                item.widget().deleteLater()
            self.skyLayout.removeItem(item)

        if self.params is None:
            return
        
        lamps = self.params.get_lamp_names()

        # Add lamps
        for lamp in lamps:
            params = self.params.get_lamp_params(lamp)
            widget = LampControlWidget(lamp, params)

            if params[0].test_role('cal'):
                self.lampLayout.insertWidget(-1, widget)
            else:
                self.skyLayout.insertWidget(-1, widget)
            widget.changed.connect(self.on_lamp_changed)
            self.lamp_widgets[lamp] = widget
        
        if self.skyLayout.count() == 0:
            noSources = QLabel()
            noSources.setText('No light sources defined. Open at least one datacube to run a simulation.')
            noSources.setStyleSheet('font-style: italic;')
            noSources.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            noSources.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
            noSources.setWordWrap(True)
            self.skyLayout.insertWidget(-1, noSources)
        else:
            self.skyLayout.addItem (QSpacerItem(1, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        self.lampLayout.addItem(QSpacerItem(1, 1, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def refresh_params(self):
        self.refresh_lamps()

        gratings = self.params.get_grating_names()
        
        # Add IS coatings
        self.isCoatingCombo.clear()
        self.isCoatingCombo.addItem('Fully reflective', userData = None)

        for coating in self.params.get_coatings():
            desc = self.params.get_coating_desc(coating)
            self.isCoatingCombo.addItem(desc, userData = coating)

        if self.isCoatingCombo.currentIndex() == -1:
            self.isCoatingCombo.setCurrentIndex(0)
        
        # Add gratings
        self.gratingCombo.clear()
        self.gratingCombo.addItems(gratings)
        
        # Add AO modes
        self.aoModeCombo.clear()
        self.aoModeCombo.addItems(self.params.get_ao_mode_names())

        # Add scales
        self.scaleCombo.clear()
        scales = self.params.get_scales()
        for s in scales:
            self.scaleCombo.addItem(fr'{s[0]}x{s[1]}', userData = list(s))
        self.refresh_spect_list()

        # Add spectrum types
        self.spectTypeCombo.clear()
        self.spectYAxisCombo.clear()

        for type in self.params.get_spectrum_types():
            self.spectTypeCombo.addItem(self.params.get_spectrum_type_desc(type), userData = type)
            
        # Populate passband centers:
        self.passBandCombo.clear()
        for g in gratings:
            grating = self.params.get_grating(g)
            name    = grating[5]
            self.passBandCombo.addItem(
                fr'{name} ({grating[3] * 1e6:.3f} µm - {grating[4] * 1e6:.3f} µm)', userData = g)
        

        # Add detector defaults
        self.pxSizeSpin.setValue(HARMONI_PIXEL_SIZE * 1e6)

        self.refresh_ui_state()

    def refresh_spect_list(self):
        self.spectYAxisCombo.clear()
        type = self.spectTypeCombo.currentData()
        if type is None:
            self.spectYAxisCombo.setEnabled(False)
            return
        
        spectrums = self.params.get_spectrums_for_type(type)
        if spectrums is None:
            self.spectYAxisCombo.setEnabled(False)
            return

        for spect in spectrums:
            name, units = self.params.get_spectrum_desc_for_type(type, spect)
            text = fr'{name} [{units}]'
            self.spectYAxisCombo.addItem(
                text,
                userData = spect)

        
        self.spectYAxisCombo.setEnabled(self.should_enable_yaxis())

    def apply_params(self, params):
        self.params = params
        self.refresh_params()

    def refresh_exp_time_ui_state(self):
        passBandCenterEnabled = self.tExpPassBandRadio.isChecked()
        self.passBandCombo.setEnabled(passBandCenterEnabled)
        self.tExpWlSpin.setEnabled(self.tExpCustomLambdaRadio.isChecked())

        if passBandCenterEnabled:
            grating_name = self.passBandCombo.currentData()
            if grating_name is not None:
                grating = self.params.get_grating(grating_name)
                if grating is not None:
                    center  = .5 * (grating[3] + grating[4])
                    self.tExpWlSpin.setValue(center * 1e6)
        
    def refresh_cm_ui_state(self):
        self.isApertureDiamSpin.setMinimum(
            min(1e3 * self.isRadiusSpin.value() * .25, 1e-3))
        
        self.isApertureDiamSpin.setMaximum(1e3 * self.isRadiusSpin.value())

    def refresh_max_area(self):
            maxArea = np.pi * .25 * self.apertureSpin.value() ** 2
            self.collectingAreaSpin.setMaximum(maxArea)
            self.collectingAreaSpin.setMinimum(1)
            self.maxCollAreaLabel.setText(fr'≤ {maxArea:g} m²')

    def refresh_telescope_ui_state(self):
        self.refresh_airmass()

        if self.sender() == self.apertureSpin:
            self.refresh_max_area()
        
    def refresh_instrument_mode_ui_state(self):
        self.calModeStack.setCurrentIndex(self.instModeCombo.currentIndex())
        self.sourceStack.setCurrentIndex(self.instModeCombo.currentIndex())
        
        if self.calModeStack.currentIndex() == 0:
            self.refresh_cm_ui_state()
        else:
            self.refresh_telescope_ui_state()
    
    def refresh_ui_state(self):
        self.update_title()
        self.refresh_instrument_mode_ui_state()
        self.refresh_spect_ui_state()
        self.refresh_exp_time_ui_state()

    def set_grating(self, grating_name):
        if grating_name is None:
            grating_name = "VIS"

        obj = self.params.get_grating(grating_name)
        if obj is None:
            raise Exception(fr'Grating {grating_name} does not exist. Is your configuration file up to date with the current software version?')
        
        if grating_name is not None:
            index = self.gratingCombo.findText(grating_name)
            if index == -1:
                raise RuntimeError(fr'Failed to set grating: UI sync error')
            
            self.gratingCombo.setCurrentIndex(index)

    def set_ao_mode(self, ao_mode_name):
        if ao_mode_name is not None:
            index = self.aoModeCombo.findText(ao_mode_name)
            if index == -1:
                raise RuntimeError(fr'Failed to set AO mode: UI sync error')
            
            self.aoModeCombo.setCurrentIndex(index)

    def set_scale(self, scale_tuple):
        if scale_tuple is None:
            obj = None
        else:
            obj = self.params.get_scale(scale_tuple)
            if obj is None:
                raise Exception(fr'Scale {scale_tuple[0]}x{scale_tuple[1]} does not exist. Is your configuration file up to date with the current software version?')
            
        if obj is not None:
            index = self.scaleCombo.findData(list(scale_tuple))
            if index == -1:
                raise RuntimeError(fr'Failed to set scale: UI sync error')
            
            self.scaleCombo.setCurrentIndex(index)

    def set_spectrum_config(self, type, spect):
        if type is None:
            obj = None
        else:
            obj = self.params.get_spectrum_type_desc(type)
            if obj is None:
                raise Exception(fr'Spectrum type {type} does not exist. Is your configuration up to date with the current software version?')

        if obj is not None:
            index = self.spectTypeCombo.findData(type)
            if index == -1:
                raise RuntimeError(fr'Failed to set spectrum type: UI sync error')
            self.spectTypeCombo.setCurrentIndex(index)
            self.refresh_spect_list()

            type_desc = obj
            if spect is None:
                obj = None
            else:
                obj, _ = self.params.get_spectrum_desc_for_type(type, spect)
                if obj is None:
                    raise Exception(fr'Spectrum {spect} does not exist as {type_desc}. Is your configuration up to date with the current software version?')
            
            if obj is not None:
                index = self.spectYAxisCombo.findData(spect)
                if index == -1:
                    raise RuntimeError(fr'Failed to set spectrum: UI sync error')
                self.spectYAxisCombo.setCurrentIndex(index)
        
    def get_y_axis_selection(self):
        type = self.spectTypeCombo.currentData()
        if type is None:
            return None
        spect = self.spectYAxisCombo.currentData()
        if spect is None:
            return None
        desc, units = self.params.get_spectrum_desc_for_type(type, spect)
        _, xunits = self.get_x_axis_selection()

        # Necessary for densities
        units = units.replace('ν⁻¹', fr'{xunits}⁻¹')
        return desc, units
    
    def get_x_axis_selection(self):
        if self.spectXAxisCombo.currentIndex() == 1:
            return 'Frequency', 'THz'
        else:
            return 'Wavelength', 'µm'
        
    def set_texp_passband(self, passband):
        index = self.passBandCombo.findData(passband)
        if index == -1:
            raise RuntimeError(fr'Cannot set passband to the exposition time calculator.')
        
        self.passBandCombo.setCurrentIndex(index)

    def set_detector_config(self, config):
        self.gainSpin.setValue(config.G)
        self.ronSpin.setValue(config.ron)
        self.qeSpin.setValue(config.QE * 1e2)
        self.pxSizeSpin.setValue(config.pixel_size * 1e6)

    def get_detector_config(self):
        config = DetectorConfig()

        config.G          = self.gainSpin.value()
        config.ron        = self.ronSpin.value()
        config.QE         = self.qeSpin.value() * 1e-2
        config.pixel_size = self.pxSizeSpin.value() * 1e-6
        return config

    def get_telescope_config(self):
        config = TelescopeConfig()

        config.focal_length    = self.focalLengthSpin.value()
        config.aperture        = self.apertureSpin.value()
        config.zenith_distance = self.zenithSpin.value()
        config.collecting_area = self.collectingAreaSpin.value()
        config.moon            = self.moonSlider.value() * 1e-2
        config.efficiency      = self.efficiencySpin.value() * 1e-2

        return config

    def set_cm_config(self, config):
        self.fNSpin.setValue(config.offner_f)
        self.isRadiusSpin.setValue(config.is_radius * 1e3)

        self.isApertureDiamSpin.setMinimum(1e3 * self.isRadiusSpin.value() * .25)
        self.isApertureDiamSpin.setMaximum(1e3 * self.isRadiusSpin.value())

        self.isApertureDiamSpin.setValue(config.is_aperture * 1e3)

        self.set_coating(config.is_coating)

    def get_current_role(self):
        return 'cal' if self.instModeCombo.currentIndex() == 0 else 'telescope'

    def any_lamp_is_on(self):
        role = self.get_current_role()
        for lamp in self.lamp_widgets.keys():
            if self.lamp_widgets[lamp].is_on():
                spectrum = self.params.get_lamp(lamp)
                if spectrum.test_role(role):
                    return True
        return False

    def get_custom_plot_label(self):
        if self.overrideLabelCheck.isChecked():
            text = self.overrideLabelEdit.text()
            if len(text) > 0:
                return text

        return None

    def should_enable_yaxis(self):
        type = self.spectTypeCombo.currentData()
        shouldEnable = self.any_lamp_is_on() or type == 'transmission'
        return shouldEnable

    def refresh_spect_ui_state(self):
        lampsOn = self.any_lamp_is_on()
        shouldEnable = self.should_enable_yaxis()
        
        self.overrideLabelEdit.setEnabled(self.overrideLabelCheck.isChecked())
        self.spectYAxisCombo.setEnabled(shouldEnable)
        self.plotControlBox.setEnabled(shouldEnable)

        self.tExpParamBox.setEnabled(lampsOn)
        self.tExpControlBox.setEnabled(lampsOn)
        
    def set_coating(self, coating):
        index = -1

        if coating is not None:
            for i in range(1, self.isCoatingCombo.count()):
                key = self.isCoatingCombo.itemData(i)
                if key == coating:
                    index = i
                    break

            if index == -1:
                QMessageBox.warning(
                    self, 
                    fr'Integrating sphere coating `{coating}` is not supported. ' +
                    fr'Assuming fully reflective material for now.')
                coating = None
            
        if index == -1:
            self.isCoatingCombo.setCurrentIndex(0)
        else:
            self.isCoatingCombo.setCurrentIndex(index)

    def set_cal_mode(self, enabled):
        ndx = 0 if enabled else 1
        self.calModeStack.setCurrentIndex(ndx)
        self.instModeCombo.setCurrentIndex(ndx)
        self.sourceStack.setCurrentIndex(ndx)

    def refresh_airmass(self):
        angle = self.zenithSpin.value()
        toRad = angle / 180. * np.pi
        sec   = 1. / np.cos(toRad)
        
        self.airmassLabel.setText(fr'{sec:.2f}')

    def set_telescope_config(self, config):
        self.focalLengthSpin.setValue(config.focal_length)
        self.apertureSpin.setValue(config.aperture)
        self.zenithSpin.setValue(config.zenith_distance)
        self.collectingAreaSpin.setValue(config.collecting_area)
        self.moonSlider.setValue(config.moon * 100)
        self.efficiencySpin.setValue(config.efficiency * 100)

        self.refresh_airmass()
        self.refresh_max_area()

    def set_config(self, config):
        try:
            for lamp in config.lamps.keys():
                self.lamp_widgets[lamp].set_config(config.lamps[lamp])
            
            self.lambdaSamplingSpin.setValue(config.lambda_sampling)
            self.binningSpin.setValue(config.binning)

            self.set_cm_config(config)
            self.set_telescope_config(config.telescope)
            self.set_cal_mode(config.cal_select)

            self.set_grating(config.grating)
            self.set_ao_mode(config.aomode)
            self.set_scale(config.scale)

            self.set_detector_config(config.detector)

            self.expTimeSpin.setValue(config.t_exp)
            self.satLevelSpin.setValue(config.saturation)
            self.tempSpin.setValue(config.temperature - 273.15)

            if config.x_axis == 'frequency':
                self.spectXAxisCombo.setCurrentIndex(1)
            else:
                self.spectXAxisCombo.setCurrentIndex(0)
            
            self.set_spectrum_config(config.type, config.y_axis)
            self.set_texp_passband(config.texp_band)
            self.intStepsSpin.setValue(config.texp_iters)

            if config.texp_use_band:
                self.tExpPassBandRadio.setChecked(True)
            else:
                self.tExpCustomLambdaRadio.setChecked(True)
                self.tExpWlSpin.setValue(config.texp_wl * 1e6)
            
            self.logScaleCheck.setChecked(config.spect_log)
            self.photonNoiseCheck.setChecked(config.noisy)
            self.tExpLogScaleCheck.setChecked(config.texp_log)

            self.changes = False
            self.update_title()
            self.changed.emit()
            
        except RuntimeError as e:
            dialog = QMessageBox(
                parent = self, 
                icon = QMessageBox.Icon.Critical,
                text=fr"Critical error while setting configuration: {str(e)}<p />Call trace:<pre>{traceback.format_exc()}</pre>")
            dialog.setWindowTitle("Message Dialog")
            dialog.exec()   # Stores the return value for the button pressed
        except Exception as e:
            dialog = QMessageBox(
                parent = self, 
                icon = QMessageBox.Icon.Warning,
                text=fr"Failed to set configuration: {str(e)}<p />Call trace:<pre>{traceback.format_exc()}</pre>")
            dialog.setWindowTitle("Message Dialog")
            dialog.exec()   # Stores the return value for the button pressed

    def get_config(self):
        config = SimulationConfig()
        
        # Read lamp config
        for lamp in self.lamp_widgets.keys():
            config.set_lamp_config(lamp, self.lamp_widgets[lamp].get_config())
        
        config.cal_select      = self.instModeCombo.currentIndex() == 0

        config.is_coating      = self.isCoatingCombo.currentData()
        config.is_aperture     = self.isApertureDiamSpin.value() * 1e-3
        config.is_radius       = self.isRadiusSpin.value() * 1e-3
        config.lambda_sampling = self.lambdaSamplingSpin.value()
        config.binning         = self.binningSpin.value()
        config.grating         = self.gratingCombo.currentText()
        config.aomode          = self.aoModeCombo.currentText()
        config.scale           = self.scaleCombo.currentData()
        config.t_exp           = self.expTimeSpin.value()
        config.saturation      = self.satLevelSpin.value()
        config.temperature     = self.tempSpin.value() + 273.15

        config.type            = self.spectTypeCombo.currentData()
        config.x_axis          = 'frequency' if self.spectXAxisCombo.currentIndex() == 1 else 'wavelength'
        config.y_axis          = self.spectYAxisCombo.currentData()

        config.spect_log       = self.logScaleCheck.isChecked()
        config.noisy           = self.photonNoiseCheck.isChecked()

        config.texp_band       = self.passBandCombo.currentData()
        config.texp_use_band   = self.tExpPassBandRadio.isChecked()
        config.texp_wl         = self.tExpWlSpin.value()
        config.texp_log        = self.tExpLogScaleCheck.isChecked()
        config.texp_iters      = self.intStepsSpin.value()

        config.detector        = self.get_detector_config()
        config.telescope       = self.get_telescope_config()

        return config

    def do_save_as(self):
        name, filter = QFileDialog.getSaveFileName(
            self, 
            'Save current configuration',
            directory = 'my_config.yaml' if self.filename is None else self.filename,
            filter = 'QRadioSim config files (*.yml, *.yaml);;All files (*)')
        if len(name) == 0:
            return False

        try:
            config = self.get_config()
            config.save_to_file(name)
            self.filename = os.path.basename(name)
            self.changes = False
        except Exception as e:
            QMessageBox.critical(self, 'Cannot save file', 'Failed to save file: ' + str(e))
            return False
    
        return True

    def do_save(self):
        if self.filename is None:
            return self.do_save_as()
        
        try:
            config = self.get_config()
            config.save_to_file(self.filename)
            self.changes = False
            self.update_title()
        except Exception as e:
            QMessageBox.critical(self, 'Cannot save file', 'Failed to save file: ' + str(e))
            return False
    
        return True

    def about_to_close(self):
        if self.changes:
            dlg = QMessageBox(self)
            dlg.setWindowTitle('Save changes')
            dlg.setText('There are unsaved changes in the current configuration. Do you want to save them to a file?')
            dlg.setStandardButtons(
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel)
            dlg.setIcon(QMessageBox.Icon.Question)
            button = dlg.exec()

            if button == QDialogButtonBox.StandardButton.No.value:
                return True
            if button == QDialogButtonBox.StandardButton.Cancel.value:
                return False

            return self.do_save_as()

        return True

    def do_open(self):
        name, filter = QFileDialog.getOpenFileName(
            self,
            'Load configuration',
            filter = 'QRadioSim config files (*.yml, *.yaml);;All files (*)')
        
        if len(name) == 0:
            return False

        try:
            config = SimulationConfig()
            config.load_from_file(name)
            self.set_config(config)
            self.filename = os.path.basename(name)
            self.changes = False
            self.update_title()
        except Exception as e:
            QMessageBox.critical(self, 'Cannot load config file', 'Failed to load config file: ' + str(e) + fr'<p /><pre>{traceback.format_exc()}</pre>')
            return False
            
    def closeEvent(self, event):
        # do stuff
        if self.about_to_close():
            event.accept() # let the window close
        else:
            event.ignore()

    def notify_changes(self):
        self.changes = True
        self.update_title()
        self.changed.emit()

    ################################# Slots ####################################
    def on_open(self):
        if not self.about_to_close():
            return

        self.do_open()

    def on_save(self):
        self.do_save()

    def on_save_as(self):
        self.do_save_as()

    def on_quit(self):
        if not self.about_to_close():
            return
        QtWidgets.QApplication.quit()

    def on_inst_mode_widget_changed(self):
        self.notify_changes()
        self.refresh_instrument_mode_ui_state()
        self.refresh_spect_ui_state()
        
    def on_state_widget_changed(self):
        self.notify_changes()
        self.refresh_ui_state()

    def on_spect_type_changed(self):
        self.notify_changes()
        self.refresh_spect_list()
        self.refresh_spect_ui_state()

    def on_lamp_changed(self):
        self.notify_changes()
        self.refresh_spect_ui_state()

    def on_plot_clear(self):
        self.clear_plot()

    def on_log_scale_changed(self):
        self.notify_changes()
        self.plotWidget.set_log_scale(self.logScaleCheck.isChecked())
    
    def on_texp_clear(self):
        self.clear_texp()

    def on_texp_log_scale_changed(self):
        self.notify_changes()
        self.tExpWidget.set_log_scale(self.tExpLogScaleCheck.isChecked())

    def on_load_cube(self):
        if self.cubeChooserDialog.do_open():
            self.cubeChooserDialog.set_lamp_name(self.suggest_lamp_name())
            self.cubeChooserDialog.show()
        
    def suggest_lamp_name(self):
        filename = self.cubeChooserDialog.get_filename()
        name = os.path.basename(filename)

        if self.params.get_lamp(name) is not None:
            i = 1
            while self.params.get_lamp(name + fr' ({i})') is not None:
                i += 1
            name = name + fr' ({i})'

        return name

    def on_cube_accepted(self):
        freq_units, ff, data = self.cubeChooserDialog.get_selected_spectrum()
        base_units = self.cubeChooserDialog.get_base_unit()

        # Convert units to J/s/m^2/m/rad^2
        if base_units == 'erg/s/cm2/AA/arcsec2':
            data *= 4.254517e+17
        else:
            QMessageBox.warning(
                self,
                'Cannot load this spectrum',
                fr'The spectrum uses an unknown intensity unit ' + \
                fr'({base_units}) and therefore it cannot be used as a source.'
            )
            return
        
        if freq_units is not None:
            mult = 1
            if freq_units.lower() == 'angstrom':
                mult = 1e-4
            elif freq_units.lower() == 'nm':
                mult = 1e-3
            elif freq_units.lower() != 'µm':
                QMessageBox.warning(
                    self,
                    'Cannot load this spectrum',
                    fr'The spectrum uses an unknown frequency / wavelength axis ' + \
                    fr'unit ({freq_units}) and therefore it cannot be used as a source.'
                )
                return
            
            ff   *= mult
            data *= 1e-6 
            name = self.cubeChooserDialog.get_lamp_name()
            if len(name) == 0:
                name = self.suggest_lamp_name()
            
            resp = np.array([ff, data])
            resp[np.isnan(resp)] = 0

            self.params.load_lamp(
                name,
                response = resp,
                desc = 'Datacube source',
                role = 'telescope')
            
            self.instModeCombo.setCurrentIndex(1)
            self.refresh_instrument_mode_ui_state()
            self.refresh_lamps()
