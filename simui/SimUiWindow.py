from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMessageBox
from PyQt6 import uic
from radiosim import SimulationConfig

import pathlib
import traceback

from radiosim.Parameters import HARMONI_PIXEL_SIZE, \
    HARMONI_FINEST_SPAXEL_SIZE, HARMONI_PX_PER_SP_ALONG, \
    HARMONI_PX_PER_SP_ACROSS, HARMONI_PX_AREA

class SimUiWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/simui.ui", self)
        self.setWindowTitle("QRadioSim - The HARMONI's radiometric simulator")
        self.refresh_ui_state()
        self.connect_all()
        
    def connect_all(self):
        self.lamp1TypeCombo.activated.connect(self.on_state_widget_changed)
        self.lamp2TypeCombo.activated.connect(self.on_state_widget_changed)
        self.passBandCombo.activated.connect(self.on_state_widget_changed)
        self.tExpPassBandRadio.toggled.connect(self.on_state_widget_changed)

    def refresh_params(self):
        gratings = self.params.get_grating_names()

        # Add lamps
        self.lamp1TypeCombo.clear()
        self.lamp2TypeCombo.clear()

        self.lamp1TypeCombo.addItem('Off', userData = None)
        self.lamp2TypeCombo.addItem('Off', userData = None)

        lamps = self.params.get_lamp_names()

        for lamp in lamps:
            self.lamp1TypeCombo.addItem(lamp, userData = self.params.get_lamp(lamp))
            self.lamp2TypeCombo.addItem(lamp, userData = self.params.get_lamp(lamp))                

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

    def apply_params(self, params):
        self.params = params
        self.refresh_params()


    def refresh_lamp_control_ui_state(self):
        # Lamp control
        lamp1 = self.lamp1TypeCombo.currentData()
        lamp2 = self.lamp2TypeCombo.currentData()

        lamp1Adjustable = lamp1 is not None and lamp1.is_adjustable()
        lamp2Adjustable = lamp2 is not None and lamp2.is_adjustable()

        self.lamp1PowerSpin.setEnabled(lamp1Adjustable)
        self.lamp2PowerSpin.setEnabled(lamp2Adjustable)

        if lamp1Adjustable:
            self.lamp1PowerSpin.setValue(lamp1.get_power())

        if lamp2Adjustable:
            self.lamp2PowerSpin.setValue(lamp2.get_power())

        self.lamp1AttenLabel = fr'{self.lamp1AttenSlider.value()} %'
        self.lamp2AttenLabel = fr'{self.lamp2AttenSlider.value()} %'

        self.lamp1AttenSlider.setEnabled(lamp1 is not None)
        self.lamp2AttenSlider.setEnabled(lamp2 is not None)

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
        self.refresh_lamp_control_ui_state()
        self.refresh_exp_time_ui_state()

    def set_lamp_1(self, lamp_name):
        if lamp_name is None:
            lamp = None
        else:
            lamp = self.params.get_lamp(lamp_name)
            if lamp is None:
                raise Exception(fr'Lamp {lamp_name} does not exist. Is your configuration file up to date with the current software version?')
            
        index = self.lamp1TypeCombo.findData(lamp)
        if index == -1:
            raise RuntimeError(fr'Failed to set lamp 1: UI sync error')
        
        self.lamp1TypeCombo.setCurrentIndex(index)
    
    def set_lamp_2(self, lamp_name):
        if lamp_name is None:
            lamp = None
        else:
            lamp = self.params.get_lamp(lamp_name)
            if lamp is None:
                raise Exception(fr'Lamp {lamp_name} does not exist. Is your configuration file up to date with the current software version?')
            
        index = self.lamp2TypeCombo.findData(lamp)
        if index == -1:
            raise RuntimeError(fr'Failed to set lamp 2: UI sync error')
        
        self.lamp2TypeCombo.setCurrentIndex(index)
    
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

    def set_texp_passband(self, passband):
        index = self.passBandCombo.findData(passband)
        if index == -1:
            raise RuntimeError(fr'Cannot set passband to the exposition time calculator.')
        
        self.passBandCombo.setCurrentIndex(index)

    def set_config(self, config):
        try:
            self.set_lamp_1(config.lamp1.config)
            self.set_lamp_2(config.lamp2.config)
            self.set_grating(config.grating)
            self.set_ao_mode(config.aomode)
            self.set_scale(config.scale)

            self.expTimeSpin.setValue(config.t_exp)
            self.satLevelSpin.setValue(config.saturation)
            self.tempSpin.setValue(config.temperature - 273.15)

            self.set_texp_passband(config.texp_band)

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
        
        config.lamp1.config = None if self.lamp1TypeCombo.currentData() is None else self.lamp1TypeCombo.currentText()
        config.lamp2.config = None if self.lamp2TypeCombo.currentData() is None else self.lamp2TypeCombo.currentText()

        config.grating       = self.gratingCombo.currentText()
        config.aomode        = self.aoModeCombo.currentText()
        config.scale         = self.scaleCombo.currentData()
        config.t_exp         = self.expTimeSpin.value()
        config.saturation    = self.satLevelSpin.value()
        config.temperature   = self.tempSpin.value + 273.15

        config.spect_log     = self.logScaleCheck.isChecked()
        config.noisy         = self.photonNoiseCheck.isChecked()

        config.texp_band     = self.passBandCombo.currentData()
        config.texp_use_band = self.tExpPassBandRadio.isChecked()
        config.texp_wl       = self.tExpWlSpin.value()
        config.texp_log      = self.tExpLogScaleCheck.isChecked()
        
    
        return config

    ################################# Slots ####################################
    def on_state_widget_changed(self):
        self.refresh_ui_state()


