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
import matplotlib as mpl
from PyQt6 import QtCore, uic, QtGui
from astropy.io import fits
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog
from .ImageNavWidget import ImageNavWidget
import os.path
import pathlib
import traceback

class CubeChooserDialog(QtWidgets.QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/CubeSelector.ui", self)
        self.imageNav = ImageNavWidget(self)
        self.imageNav.setInteractive(True)

        self.zoomNav = ImageNavWidget(self)

        self.previewStackedWidget.insertWidget(0, self.imageNav)
        self.detailStackedWidget.insertWidget(0, self.zoomNav)

        self.connect_all()

    def connect_all(self):
        self.openButton.clicked.connect(self.on_load_cube)
        self.imageNav.mouseMoved.connect(self.on_image_nav_move)

    def reduce_hdu(self):
        self.hdu_slice = self.hdu.data[self.hdu_depth // 2]
        self.hdu_min   = np.min(self.hdu_slice)
        self.hdu_max   = np.max(self.hdu_slice)

    def refresh_hdu(self):
        self.hdu_depth  = self.hdu.shape[0]
        self.hdu_height = self.hdu.shape[2]
        self.hdu_width  = self.hdu.shape[1]
        self.reduce_hdu()

        self.imageNav.setImageData(self.hdu_slice)

        z1 = 256 / self.hdu_height
        z2 = 512 / self.hdu_width

        self.imageNav.setZoom(np.min([z1, z2]))
        self.zoomNav.setImageData(self.hdu_slice)
        self.zoomNav.setZoom(self.zoomNav.width() / 10)

        self.previewStackedWidget.setCurrentIndex(0)
        self.detailStackedWidget.setCurrentIndex(0)

    def set_hdu(self, hdu):
        self.hdu = hdu
        self.refresh_hdu()

    def load_cube(self, filename):
        hdul = fits.open(filename)
        self.set_hdu(hdul[0])
        
    def do_open(self):
        name, filter = QFileDialog.getOpenFileName(
            self,
            'Load configuration',
            filter = 'FITS data cubes (*.fits);;All files (*)')
        
        if len(name) == 0:
            return False

        try:
            self.load_cube(name)
            self.filename = os.path.basename(name)
        except Exception as e:
            QMessageBox.critical(self, 'Cannot load data cube file', 'Failed to load data cube file: ' + str(e) + fr'<p /><pre>{traceback.format_exc()}</pre>')
            return False
            
        return True

################################ Slots ########################################
    def on_load_cube(self):
        self.do_open()
    
    def on_image_nav_move(self, x, y):
        self.zoomNav.zoomToPoint(x, y)
