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

from radiosim import TemperatureConfig

import pathlib

class TemperatureControlWidget(QtWidgets.QWidget):
    changed = pyqtSignal()

    def __init__(self, tempId, params, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/TemperatureControl.ui", self)

        self.params    = params
        self.tempId    = tempId
        self.tempUnits = 'C'
        self.tempDesc  = params.get_temperature_desc(tempId)
        self.tempDefl  = params.get_temperature(tempId)
        self.temp      = self.tempDefl

        self.descLabel.setText(self.tempDesc)

        self.connect_all()
        self.refresh_ui()

    def connect_all(self):
        self.tempSpin.valueChanged.connect(self.on_temp_changed)
        self.unitsCombo.activated.connect(self.on_units_changed)
        self.resetButton.clicked.connect(self.on_reset)

    def is_on(self):
        return self.lampOnOffButton.isChecked()
    
    def refresh_ui(self):
        # TODO: Convert to units
        minK = 0
        maxK = 3000
        if self.tempUnits == 'K':
            tempVal = self.temp
            index   = 0
            minT    = minK
            maxT    = maxK

        elif self.tempUnits == 'C':
            tempVal = self.temp - 273.15
            minT    = minK - 273.15
            maxT    = maxK - 273.15
            index   = 1
        elif self.tempUnits == 'F':
            tempVal = (self.temp - 273.15) * 1.8 + 32
            minT    = (minK      - 273.15) * 1.8 + 32
            maxT    = (maxK      - 273.15) * 1.8 + 32
            index   = 2

        blockSig = self.tempSpin.blockSignals(True)
        self.tempSpin.setMinimum(minT)
        self.tempSpin.setMaximum(maxT)
        self.tempSpin.setValue(tempVal)
        self.tempSpin.setPrefix(
          '+' if tempVal > 0 and self.tempUnits != 'K' else None)
        self.tempSpin.blockSignals(blockSig)

        blockSig = self.unitsCombo.blockSignals(True)
        self.unitsCombo.setCurrentIndex(index)
        self.unitsCombo.blockSignals(blockSig)

    def set_config(self, config):
        self.temp      = config.temperature
        self.tempUnits = config.pref_units
        self.refresh_ui()

    def get_config(self):
        config = TemperatureConfig()
        config.temperature = self.temp
        config.pref_units  = self.tempUnits
        return config

    ################################# Slots ###################################
    def on_units_changed(self):
        units = ['K', 'C', 'F']
        self.tempUnits = units[self.unitsCombo.currentIndex()]
        self.refresh_ui()
        # Do not emit temperature changed

    def on_temp_changed(self):
        # TODO: Convert from units and emit.
        tempVal = self.tempSpin.value()

        if self.tempUnits == 'K':
            self.temp = tempVal
        elif self.tempUnits == 'C':
            self.temp = tempVal + 273.15
        elif self.tempUnits == 'F':
            self.temp = (tempVal - 32) / 1.8 + 273.15
        self.changed.emit()
    
    def on_reset(self):
        if abs(self.temp - self.tempDefl) >= 1e-3:
          self.temp = self.tempDefl
          self.refresh_ui()
          self.changed.emit()
    