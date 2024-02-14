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
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import QtCore, uic, QtGui
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QMessageBox, QCheckBox, QApplication
import os.path
import pathlib

class StageSelectDialog(QtWidgets.QDialog):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    dir = pathlib.Path(__file__).parent.resolve()
    uic.loadUi(fr"{dir}/StageSelect.ui", self)
    self._response   = None
    self._checkboxes = {}
    self._pruned     = []
    self.refresh_ui()
    self.setWindowTitle('Enable/Disable stages')

  def refresh_ui(self):
    # Remove placeholders
    for i in reversed(range(self.scrollAreaLayout.count())):
        item = self.scrollAreaLayout.itemAt(i)
        if item.widget() is not None:
          widget = item.widget()
          widget.hide()
          widget.deleteLater()  

        self.scrollAreaLayout.removeItem(item)

    # Add widgets
    self._checkboxes = {}

    if self._response is not None:
      stages = self._response.stages()
      for stage in stages:
          widget = QCheckBox(self)
          self.scrollAreaLayout.insertWidget(-1, widget)

          label = stage.get_label()
          name  = stage.get_entrance_node_name()

          widget.setText(label)
          widget.setChecked(label not in self._pruned)
          
          self._checkboxes[name] = widget

  def set_prune_list(self, pruned: list):
    self._pruned = pruned.copy()
    self.refresh_ui()
  
  def set_response(self, response):
    self._response = response
    self.refresh_ui()

  def get_prune_list(self):
    self._pruned = []

    for cb in self._checkboxes:
      if not self._checkboxes[cb].isChecked():
        self._pruned.append(self._checkboxes[cb].text())

    return self._pruned
  