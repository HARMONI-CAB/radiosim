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

import matplotlib as mpl
import numpy as np
from PyQt6 import QtCore, uic, QtGui
from astropy.io import fits
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import QtWidgets

class ImageNavWidget(QtWidgets.QWidget):
    selChanged = pyqtSignal()
    mouseMoved = pyqtSignal("float", "float")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.array = None
        self.previewImage = None
        self.zoom = 1
        self.preferredZoom = 1
        self.move_last_pos = None
        self.move_ref_pos = None
        self.interactive = False
        self.x0 = 0
        self.y0 = 0
        self.autoscale = False
        self.sane_min = 0
        self.sane_max = 1
        
        self.setImageLimits(self.sane_min, self.sane_max)

        self.sel_x = 0
        self.sel_y = 0

        self.setMouseTracking(True)

    def getSelection(self):
        return self.sel_x, self.sel_y
    
    def setInteractive(self, interactive):
        self.interactive = interactive
        self.setMouseTracking(self.interactive)

    def recalcImage(self):
        if self.array is not None:
            colormap   = mpl.colormaps['inferno']
            normalized = (self.array - self.arr_min) * (1. / (self.arr_max - self.arr_min))
            clipped    = np.transpose(np.clip(normalized, 0, 1), (1, 0))
            as_bytes = (255 * colormap(clipped)).copy().astype('ubyte')

            self.previewImage = QtGui.QImage(
                as_bytes.data,
                self.img_width,
                self.img_height,
                QtGui.QImage.Format.Format_RGBX8888)
                
    def getCurrentLimits(self):
        return self.arr_min, self.arr_max

    def setImageLimits(self, min, max):
        self.arr_min = min
        self.arr_max = max
        self.recalcImage()
        self.update()

    def setAutoScale(self, autoscale):
        if self.autoscale != autoscale:
            self.autoscale = autoscale
            if self.autoscale:
                self.setImageLimits(self.sane_min, self.sane_max)

    def setImageData(self, array):
        self.array = array
        sane = array[~np.isnan(array)]

        self.sane_min = np.min(sane)
        self.sane_max = np.max(sane)

        if self.autoscale:
            self.setImageLimits(self.sane_min, self.sane_max)
        
        self.img_width  = array.shape[1]
        self.img_height = array.shape[0]

        self.ratio   = self.img_height / self.img_width
        
        self.recalcImage()
        self.update()

    def paintEvent(self, event):
        if self.previewImage is not None:
            painter = QtGui.QPainter(self)
            target_width  = self.img_width * self.zoom
            target_height = self.img_height * self.zoom
            target_x, target_y = self.imgcenter2px(-self.img_width / 2, -self.img_height / 2)
            painter.drawPixmap(
                QtCore.QRect(
                    int(target_x),
                    int(target_y),
                    int(target_width),
                    int(target_height)),
                QtGui.QPixmap(self.previewImage))

            px_sel_start_x, px_sel_start_y = self.img2px(self.sel_x + 0, self.sel_y + 0)
            px_sel_end_x,   px_sel_end_y = self.img2px(self.sel_x + 1, self.sel_y + 1)

            if px_sel_start_x < self.width() and px_sel_end_x >= 0 and \
                px_sel_start_y < self.height() and px_sel_end_y >= 0:
                painter.setPen(QtGui.QColor(0, 255, 0))
                painter.drawRect(
                    QtCore.QRectF(px_sel_start_x,
                    px_sel_start_y,
                    px_sel_end_x - px_sel_start_x,
                    px_sel_end_y - px_sel_start_y))
            painter.end()

    def setZoom(self, zoom):
        self.preferredZoom = zoom
        self.zoom = zoom
        self.update()
    
    def resetZoom(self):
        self.zoom = self.preferredZoom
        self.x0   = 0
        self.y0   = 0
        self.update()

    def zoomToPoint(self, x, y):
        self.x0 = -x * self.zoom
        self.y0 = -y * self.zoom
        self.update()
        
    def setSelection(self, x, y):
        self.sel_x = np.clip(int(x), 0, self.img_width - 1)
        self.sel_y = np.clip(int(y), 0, self.img_height - 1)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.move_ref_pos = event.pos()

        if event.button() == Qt.MouseButton.LeftButton and event.pos() in self.rect():
            x, y = self.px2img(event.pos().x(), event.pos().y())
            self.setSelection(x, y)
            self.selChanged.emit()
            self.update()

    def mouseReleaseEvent(self, event):
        # ensure that the left button was pressed *and* released within the
        # geometry of the widget; if so, emit the signal;
        if self.interactive:
            if event.button() == Qt.MouseButton.RightButton:
                self.resetZoom()
                self.update()

            self.move_ref_pos = None
            self.move_last_pos = None

    def mouseMoveEvent(self, event):
        if self.interactive:
            if self.move_ref_pos is not None:
                if self.move_last_pos is not None:
                    delta = event.position() - self.move_last_pos
                    self.x0 += delta.x()
                    self.y0 += delta.y()
                self.move_last_pos = event.position()
                self.update()
            else:
                self.mouseMoved.emit(*self.px2imgcenter(event.position().x(), event.position().y()))

    def px2img(self, px, py):
        ix, iy = self.px2imgcenter(px, py)
        return ix + self.img_width // 2, iy + self.img_height // 2

    def img2px(self, x, y):
        return self.imgcenter2px(x - self.img_width // 2, y - self.img_height //2)

    def px2imgcenter(self, px, py):
        return \
            (px - self.width() / 2 - self.x0) / self.zoom, \
            (py - self.height() / 2 - self.y0) / self.zoom

    def imgcenter2px(self, x, y):
        return \
            self.width() / 2  + x * self.zoom + self.x0, \
            self.height() / 2 + y * self.zoom + self.y0

    def wheelEvent(self, event):
        # Zooming in a point means altering the offset in a way that point
        # is not affected by the zoom. So, if the pixel at which certain
        # coordinate is, is given by:
        #
        # p_z = zoom * z + z0
        #
        # And we zoom to a different level zoom' in the coordinate z_z
        # so that p_z stays the same, the following must hold:
        #
        # zoom' * z_z + z0' = zoom * z_z + z0
        #
        # And therefore:
        #
        # z0' = zoom * z_z + z0 - zoom' * z_z
        # z0' = z0 + z_z * (zoom - zoom')

        if self.interactive:
            prev_zoom = self.zoom
            x_z, y_z = self.px2imgcenter(event.position().x(), event.position().y())
            self.zoom *= np.exp(event.angleDelta().y() / 1200)
            self.x0 += x_z * (prev_zoom - self.zoom)
            self.y0 += y_z * (prev_zoom - self.zoom)

            self.update()
