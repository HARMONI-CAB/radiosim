from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import pyqtSignal


from radiosim import LampConfig

import pathlib
import traceback

class LampControlWidget(QtWidgets.QWidget):
    changed = pyqtSignal()

    def __init__(self, name, lampParams, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/LampControl.ui", self)

        self.spectrum = lampParams[0]
        self.lampGroupBox.setTitle(name)
        self.powerAdjustable = self.spectrum.is_adjustable()

        if lampParams[1] is not None:
            self.lampDescLabel.setText(lampParams[1])
        else:
            self.lampDescLabel.setVisible(False)
        

        self.lampPowerSpin.setEnabled(self.powerAdjustable)
        if self.powerAdjustable:
            self.lampPowerSpin.setValue(self.spectrum.get_power())
        else:
            self.powerLabel.setVisible(False)
            self.lampPowerSpin.setVisible(False)
        
        self.connect_all()
        self.refresh_ui()

    def connect_all(self):
        self.attenSlider.valueChanged.connect(self.on_ui_changed)
        self.lampOnOffButton.toggled.connect(self.on_ui_changed)
        self.lampPowerSpin.valueChanged.connect(self.on_ui_changed)
        
    def is_on(self):
        return self.lampOnOffButton.isChecked()
    
    def refresh_ui(self):
        isOn = self.lampOnOffButton.isChecked()
        if not isOn:
            stylesheet = "font-weight: bold;\nbackground-color: #7f0000;\ncolor: white;\n"
            text       = "&OFF"
        else:
            stylesheet = "font-weight: bold;\nbackground-color: #00ff00;\ncolor: black;\n"
            text       = "&ON"
        self.attenSlider.setEnabled(isOn)
        self.attenLabel.setEnabled(isOn)

        self.attenLabel.setText(fr'{self.attenSlider.value()} %')
        self.lampOnOffButton.setStyleSheet(stylesheet)
        self.lampOnOffButton.setText(text)
        self.lampPowerSpin.setEnabled(isOn and self.powerAdjustable)

    def set_config(self, config):
        self.lampOnOffButton.setChecked(config.is_on)
        if config.power is not None and self.powerAdjustable:
            self.lampPowerSpin.setValue(config.power)
        self.attenSlider.setValue(config.attenuation)
        
    def get_config(self):
        config = LampConfig()

        config.is_on = self.lampOnOffButton.isChecked()
        config.power = self.lampPowerSpin.value() if self.powerAdjustable else None
        config.attenuation = self.attenSlider.value()

        return config

    ################################# Slots ###################################
    def on_ui_changed(self):
        self.refresh_ui()
        self.changed.emit()
    