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

from PyQt6 import QtWidgets, uic
from PyQt6.QtCore import pyqtSignal

from radiosim import LampConfig, PowerSpectrum

import pathlib

class LampControlWidget(QtWidgets.QWidget):
    changed = pyqtSignal()

    def __init__(self, name, lampParams, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/LampControl.ui", self)

        self.spectrum = lampParams[0]
        self.lampGroupBox.setTitle(name)
        self.powerAdjustable = self.spectrum.is_adjustable()
        self.isPowerSource = issubclass(type(self.spectrum), PowerSpectrum)

        # Power-defined source: do not show area config
        if self.isPowerSource:
            self.effAreaLabel.setVisible(False)
            self.effAreaSpin.setVisible(False)
        
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
        self.effAreaSpin.valueChanged.connect(self.on_ui_changed)

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
        self.effAreaSpin.setVale(config.effective_area * 1e4)

    def get_config(self):
        config = LampConfig()

        config.is_on = self.lampOnOffButton.isChecked()
        config.power = self.lampPowerSpin.value() if self.powerAdjustable else None
        config.attenuation = self.attenSlider.value()
        config.effective_area = self.effAreaSpin.value() * 1e-4

        return config

    ################################# Slots ###################################
    def on_ui_changed(self):
        self.refresh_ui()
        self.changed.emit()
    