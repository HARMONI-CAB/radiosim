from PyQt6 import QtCore
from PyQt6.QtCore import pyqtSignal
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox, QDialogButtonBox, QFileDialog
from PyQt6 import uic
from radiosim import SimulationConfig, DetectorConfig
from .PlotWidget import PlotWidget
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/simui.ui", self)
        self.setWindowTitle("QRadioSim - The HARMONI's radiometric simulator")
        
        self.plotWidget = PlotWidget()
        self.plotStack.insertWidget(1, self.plotWidget)
        self.curr_x_units = None
        self.curr_y_units = None
        self.lamp_widgets = {}
        self.changes = False
        self.filename = None
        self.refresh_ui_state()
        self.connect_all()
        
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

        self.spectTypeCombo.activated.connect(self.on_spect_type_changed)

        self.passBandCombo.activated.connect(self.on_state_widget_changed)
        self.tExpPassBandRadio.toggled.connect(self.on_state_widget_changed)
        
        self.logScaleCheck.toggled.connect(self.on_log_scale_changed)

        self.action_Open.triggered.connect(self.on_open)
        self.action_Save.triggered.connect(self.on_save)
        self.action_Save_as.triggered.connect(self.on_save_as)
        self.action_Quit.triggered.connect(self.on_quit)

    def clear_plot(self):
        self.plotWidget.clear()
        self.plotStack.setCurrentIndex(0)
        self.curr_x_units = None
        self.curr_y_units = None

    def set_plot(self, *args, xlabel = None, ylabel = None, **kwargs):
        self.plotWidget.plot(*args, xlabel = xlabel, ylabel = ylabel, **kwargs)
        self.plotStack.setCurrentIndex(1)

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

    def refresh_params(self):
        gratings = self.params.get_grating_names()

        # Remove exiting lamps
        lamps = self.params.get_lamp_names()

        for l in self.lamp_widgets.keys():
            widget = self.lamp_widgets[l]
            self.lampLayout.removeWidget(widget)
            widget.deleteLater()

        # Add lamps
        for lamp in lamps:
            params = self.params.get_lamp_params(lamp)
            widget = LampControlWidget(lamp, params)
            self.lampLayout.insertWidget(-1, widget)
            widget.changed.connect(self.on_lamp_changed)
            self.lamp_widgets[lamp] = widget
        
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
            center  = .5 * (grating[3] + grating[4])
            self.passBandCombo.addItem(
                fr'{name} ({center * 1e6:.3f} µm)', userData = g)
        

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
        self.spectYAxisCombo.setEnabled(True)

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
        
    def refresh_ui_state(self):
        self.update_title()
        self.refresh_spectrum_ui()
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
        self.fNSpin.setValue(config.f)

    def get_detector_config(self):
        config = DetectorConfig()

        config.G          = self.gainSpin.value()
        config.ron        = self.ronSpin.value()
        config.QE         = self.qeSpin.value() * 1e-2
        config.pixel_size = self.pxSizeSpin.value() * 1e-6
        config.f          = self.fNSpin.value()

        return config

    def any_lamp_is_on(self):
        for lamp in self.lamp_widgets.keys():
            if self.lamp_widgets[lamp].is_on():
                return True
        return False

    def refresh_spectrum_ui(self):
        self.spectrumControlBox.setEnabled(self.any_lamp_is_on())
    
    def set_config(self, config):
        try:
            for lamp in config.lamps.keys():
                self.lamp_widgets[lamp].set_config(config.lamps[lamp])
            
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
        
        config.grating       = self.gratingCombo.currentText()
        config.aomode        = self.aoModeCombo.currentText()
        config.scale         = self.scaleCombo.currentData()
        config.t_exp         = self.expTimeSpin.value()
        config.saturation    = self.satLevelSpin.value()
        config.temperature   = self.tempSpin.value() + 273.15

        config.type          = self.spectTypeCombo.currentData()
        config.x_axis        = 'frequency' if self.spectXAxisCombo.currentIndex() == 1 else 'wavelength'
        config.y_axis        = self.spectYAxisCombo.currentData()

        config.spect_log     = self.logScaleCheck.isChecked()
        config.noisy         = self.photonNoiseCheck.isChecked()

        config.texp_band     = self.passBandCombo.currentData()
        config.texp_use_band = self.tExpPassBandRadio.isChecked()
        config.texp_wl       = self.tExpWlSpin.value()
        config.texp_log      = self.tExpLogScaleCheck.isChecked()
        config.texp_iters    = self.intStepsSpin.value()

        config.detector      = self.get_detector_config()

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

    def on_state_widget_changed(self):
        self.changes = True
        self.update_title()
        self.refresh_ui_state()

    def on_spect_type_changed(self):
        self.changes = True
        self.update_title()
        self.refresh_spect_list()
    
    def on_lamp_changed(self):
        self.changes = True
        self.update_title()
        self.refresh_spectrum_ui()

    def on_plot_clear(self):
        self.clear_plot()
    
    def on_log_scale_changed(self):
        self.changes = True
        self.update_title()
        self.plotWidget.set_log_scale(self.logScaleCheck.isChecked())
    