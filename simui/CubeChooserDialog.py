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
from matplotlib.ticker import FormatStrFormatter
from PyQt6 import QtCore, uic, QtGui
from astropy.io import fits
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from .ImageNavWidget import ImageNavWidget
from .QDegSpinBox import QDegSpinBox

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

        self.xSpinBox = QDegSpinBox(self)
        self.xSpinBox.setFormat('hms')
        self.xStackedWidget.insertWidget(1, self.xSpinBox)
        self.xStackedWidget.setCurrentIndex(1)

        self.ySpinBox = QDegSpinBox(self)
        self.ySpinBox.setFormat('dms')
        self.yStackedWidget.insertWidget(1, self.ySpinBox)
        self.yStackedWidget.setCurrentIndex(1)

        self.hdu_depth = -1
        self.have_x_units = False
        self.have_y_units = False

        self.last_mov_x = None
        self.last_mov_y = None

        self.previewStackedWidget.insertWidget(0, self.imageNav)
        self.detailStackedWidget.insertWidget(0, self.zoomNav)

        self.autoscale = self.autoScaleButton.isChecked()
        self.add_spectrum_plot()
        self.refresh_ui_state()
        self.connect_all()

    def refresh_ui_state(self):
        self.blendRadiusSpin.setEnabled(self.blend_enabled())
        self.baseLevelSlider.setEnabled(not self.img_auto_scale_enabled())
        self.rangeSlider.setEnabled(not self.img_auto_scale_enabled())
        self.baseLevelLabel.setEnabled(not self.img_auto_scale_enabled())
        self.rangeLabel.setEnabled(not self.img_auto_scale_enabled())

    def blend_enabled(self):
        return self.blendCheck.isChecked()

    def img_auto_scale_enabled(self):
        return self.imgAutoScaleButton.isChecked()

    def add_spectrum_plot(self):
        layout = QtWidgets.QVBoxLayout(self.spectrumWidget)

        self.fig = Figure()
        static_canvas = FigureCanvas(self.fig)
        
        # Ideally one would use self.addToolBar here, but it is slightly
        # incompatible between PyQt6 and other bindings, so we just add the
        # toolbar as a plain widget instead.

        layout.addWidget(NavigationToolbar(static_canvas, self))
        layout.addWidget(static_canvas)

        self._static_ax = static_canvas.figure.subplots()
        self._static_ax.yaxis.set_major_formatter(FormatStrFormatter('%.3e'))
        self._line      = None
        self._sel       = None
        self.fig.tight_layout()

    def connect_all(self):
        self.openButton.clicked.connect(self.on_load_cube)
        self.blendCheck.toggled.connect(self.on_blend_setting_changed)
        self.blendRadiusSpin.valueChanged.connect(self.on_blend_setting_changed)
        self.autoScaleButton.toggled.connect(self.on_toggle_autoscale)
        self.imgAutoScaleButton.toggled.connect(self.on_img_scale_changed)
        self.baseLevelSlider.valueChanged.connect(self.on_img_scale_changed)
        self.rangeSlider.valueChanged.connect(self.on_img_scale_changed)

        self.imageNav.mouseMoved.connect(self.on_image_nav_move)
        self.imageNav.selChanged.connect(self.on_selection_changed)
        self.xSpaxSpinBox.valueChanged.connect(self.on_spax_spin_box_changed)
        self.xSpinBox.valueChanged.connect(self.on_angle_spin_box_changed)

        self.ySpaxSpinBox.valueChanged.connect(self.on_spax_spin_box_changed)
        self.ySpinBox.valueChanged.connect(self.on_angle_spin_box_changed)
        
        self.centralWavelengthSpin.valueChanged.connect(self.on_slice_changed)
        self.passBandWidthSpin.valueChanged.connect(self.on_slice_changed)

    def selected_spectral_slice(self):
        wl = self.centralWavelengthSpin.value()
        ndx = (wl - self.f_0) / self.f_delta + self.f_rndx
        return int(np.clip(ndx, 0, self.hdu_depth - 1))

    def selected_spectral_slice_thickness(self):
        bw = self.passBandWidthSpin.value()
        slices = bw / self.f_delta
        return int(np.ceil(np.abs(slices)))

    def reduce_hdu(self):
        centerndx      = self.selected_spectral_slice()
        thickness      = self.selected_spectral_slice_thickness()
        ndx_start      = centerndx - thickness // 2
        ndx_stop       = centerndx + thickness // 2

        if ndx_start < 0:
            ndx_start  = 0
        if ndx_stop > self.hdu_depth:
            ndx_stop = self.hdu_depth
        
        if ndx_stop - ndx_start <= 1:
            self.hdu_slice = self.hdu_data[centerndx]
        else:
            self.hdu_slice = np.mean(self.hdu_data[ndx_start:ndx_stop], axis = 0)
        
        sane = self.hdu_slice[~np.isnan(self.hdu_slice) & ~np.isinf(self.hdu_slice)]

        if len(sane) > 0:
            self.hdu_min   = np.min(sane)
            self.hdu_max   = np.max(sane)
        else:
            self.hdu_min   = 0
            self.hdu_max   = 1

    def refresh_hdu(self):
        self.reduce_hdu()
        self.imageNav.setImageData(self.hdu_slice)
        self.zoomNav.setImageData(self.hdu_slice)
        self.refresh_img_scale_info()

    def get_blend_spectrum_at(self, x, y, blend):
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x >= self.hdu_width:
            x = self.hdu_width - 1
        if y >= self.hdu_height:
            y = self.hdu_height - 1
        if blend is None or blend < 1:
            return self.hdu_data[:, y, x]
        else:
            radius = int(np.floor(blend))
            indexes = np.linspace(-radius + 1, radius - 1, 2 * radius - 1).astype(int)
            xx, yy = np.meshgrid(indexes, indexes)

            # Select the pixels that fall in a circle
            valid = xx ** 2 + yy ** 2 <= blend ** 2
            xx = xx[valid].ravel() + x
            yy = yy[valid].ravel() + y
            
            # And also the ones inside the picture
            valid = (0 <= xx) & (xx < self.hdu_width) & (0 <= y) & (yy < self.hdu_height)
            xx = xx[valid]
            yy = yy[valid]

            selection = self.hdu_data[:, yy, xx]
            return selection.mean(axis = 1)

    def update_selection_spaxel(self, x, y, redraw = True):
        if x >= 0 and y >= 0 and x < self.hdu_width and y < self.hdu_height:
            blend = self.imageNav.getSelectionMaxRadius()
            data = self.get_blend_spectrum_at(x, y, blend)
            if self._sel is None:
                self._sel, = self._static_ax.plot(self.ff, data, linewidth = 1, color = [1, 0, 0])
                self._static_ax.set_xlabel(f'{self.f_mag} ({self.f_unit})')
                self._static_ax.set_ylabel(f'{self.b_mag} ({self.b_unit})')
                self.fig.tight_layout()
            else:
                self._sel.set_data(self.ff, data)
                if redraw:
                    self.refresh_spectrum_scale()
                    self._sel.figure.canvas.draw()

    def update_spectrum_at(self, x, y):
        x += self.hdu_width // 2
        y += self.hdu_height // 2
        
        if x >= 0 and y >= 0 and x < self.hdu_width and y < self.hdu_height:
            blend = self.imageNav.getSelectionMaxRadius()
            data = self.get_blend_spectrum_at(x, y, blend)
            if self._line is None:
                self._static_ax.clear()
                self._line, = self._static_ax.plot(self.ff, data, linewidth = 1)
                self._static_ax.set_xlabel(f'{self.f_mag} ({self.f_unit})')
                self._static_ax.set_ylabel(f'{self.b_mag} ({self.b_unit})')
                self.fig.tight_layout()
            else:
                self._line.set_data(self.ff, data)
                self.refresh_spectrum_scale()
                self._line.figure.canvas.draw()

    def hdrdfl(self, name, val):
        if name not in self.hdu.header:
            return val    
        return self.hdu.header[name]
    
    def update_spaxel_from_spinboxes(self):
        if self.have_x_units:
            if self.xStackedWidget.currentIndex() == 1:
                val = self.xSpinBox.value()
                px  = int(np.round((val - self.x_min) / (self.x_max - self.x_min) * (self.hdu_width - 1)))
                blocked = self.xSpaxSpinBox.blockSignals(True)
                self.xSpaxSpinBox.setValue(px)
                self.xSpaxSpinBox.blockSignals(blocked)

        if self.have_y_units:
            if self.yStackedWidget.currentIndex() == 1:
                val = self.ySpinBox.value()
                py  = int(np.round((val - self.y_min) / (self.y_max - self.y_min) * (self.hdu_height - 1)))
                blocked = self.ySpaxSpinBox.blockSignals(True)
                self.ySpaxSpinBox.setValue(py)
                self.ySpaxSpinBox.blockSignals(blocked)

        px, py = self.get_selection_center()
        self.set_selection_spaxel(px, py)

    def get_selection_center(self):
        return self.xSpaxSpinBox.value(), self.ySpaxSpinBox.value()

    def set_selection_spaxel(self, px, py, redraw = True):
        do_block_x = self.xSpaxSpinBox.blockSignals(True)
        do_block_y = self.ySpaxSpinBox.blockSignals(True)

        self.xSpaxSpinBox.setValue(px)
        self.ySpaxSpinBox.setValue(py)
        self.imageNav.setSelection(px, py)
        self.zoomNav.setSelection(px, py)
        self.update_selection_spaxel(px, py, redraw)
        
        if self.have_x_units:
            if self.xStackedWidget.currentIndex() == 1:
                val = (px * (self.x_max - self.x_min) / (self.hdu_width - 1) + self.x_min)
                blocked = self.xSpinBox.blockSignals(True)
                self.xSpinBox.setValue(val)
                self.xSpinBox.blockSignals(blocked)

        if self.have_y_units:
            if self.yStackedWidget.currentIndex() == 1:
                val = (py * (self.y_max - self.y_min) / (self.hdu_height - 1) + self.y_min)
                blocked = self.ySpinBox.blockSignals(True)
                self.ySpinBox.setValue(val)
                self.ySpinBox.blockSignals(blocked)

        self.xSpaxSpinBox.blockSignals(do_block_x)
        self.ySpaxSpinBox.blockSignals(do_block_y)

    def configureCoordAxis(
        self,
        labelWidget, stackWidget, spinWidget,
        mag, units,
        min, max, delta):

        blocked = spinWidget.blockSignals(True)

        if units is not None:
            units = units.lower()

        if mag is not None:
            mag = mag.lower()

        if units == 'deg':
            # This quantity can be expressed as an angle. Let's go ahead
            if mag == 'ra' or mag == 'ra---sin' or mag == 'ra---tan':
                mag = 'Right ascension'
                spinWidget.setFormat('hms')
            elif mag == 'dec' or mag == 'dec--sin' or mag == 'dec--tan':
                mag = 'Declination'
                spinWidget.setFormat('dms')
            else:
                spinWidget.setFormat('dms')

            # Reversed axes are definitely a reality
            if min > max:
                spinWidget.setMinimum(max)
                spinWidget.setMaximum(min)
            else:
                spinWidget.setMinimum(min)
                spinWidget.setMaximum(max)

            spinWidget.setSingleStep(np.abs(delta))
            stackWidget.setCurrentIndex(1)
        else:
            stackWidget.setCurrentIndex(0)
        
        if mag is not None:
            labelWidget.setText(mag)
        
        spinWidget.blockSignals(blocked)

    def conv_freq_units(self, unit, f_max, *args):
        if unit == 'Hz':                
            order = np.log10(f_max)
            mult = 1
            if order >= 12:
                unit = 'THz'
                mult = 1e-12
            elif order >= 9:
                unit = 'GHz'
                mult = 1e-9
            elif order >= 6:
                unit = 'MHz'
                mult = 1e-6
            elif order >= 3:
                unit = 'kHz'
                mult = 1e-3
            
            conv = []
            for i in args:
                conv.append(i * mult)
        else:
            if unit == 'mum':
                unit = 'µm'
            conv = list(args)

        return tuple([unit] + conv)

    def conv_sky_units(self, unit, *args):
        if unit.lower() == 'mas':
            unit = 'deg'
            mult = 1e-3 / 3600
            conv = []
            for i in args:
                conv.append(i * mult)
        else:
            conv = list(args)
        return tuple([unit] + conv)

    def mag_to_sci(self, val):
        sign = val < 0
        if sign:
            val = -val

        if val == 0:
            return '0'
        
        exp = int(np.floor(np.log10(val)))
        mult   = 10**(-exp)
        
        result = f'{val * mult:.3f}'

        if sign:
            result = '-' + result

        if exp != 0:
            result += f" × 10<sup>{exp}</sup>"

        return result

    def extract_hdu_unit_info(self):
        self.b_mag   = self.hdrdfl('BTYPE', 'Arbitrary intensity')
        self.b_unit  = self.hdrdfl('BUNIT', 'a.u.')
        
        self.x_mag   = self.hdu.header['CTYPE1']
        self.x_unit  = self.hdu.header['CUNIT1']

        if self.x_unit is not None:
            self.have_x_units = True
            self.x_rndx  = self.hdrdfl('CRPIX1', 1) - 1
            self.x_0     = self.hdrdfl('CRVAL1', 0)
            self.x_delta = self.hdu.header['CDELT1']
            self.x_unit, self.x_0, self.x_delta = \
                self.conv_sky_units(self.x_unit, self.x_0, self.x_delta)
            
        self.y_mag   = self.hdu.header['CTYPE2']
        self.y_unit  = self.hdu.header['CUNIT2']

        if self.y_unit is not None:
            self.have_y_units = True
            self.y_rndx  = self.hdrdfl('CRPIX2', 1) - 1
            self.y_0     = self.hdrdfl('CRVAL2', 0)
            self.y_delta = self.hdu.header['CDELT2']
            self.y_unit, self.y_0, self.y_delta = \
                self.conv_sky_units(self.y_unit, self.y_0, self.y_delta)
        
        self.f_mag   = self.hdu.header['CTYPE3']
        self.f_unit  = self.hdu.header['CUNIT3']
        self.f_rndx  = self.hdrdfl('CRPIX3', 1) - 1
        self.f_0     = self.hdrdfl('CRVAL3', 0)
        self.f_delta = self.hdu.header['CDELT3']

        # Adjust third axis first.
        self.f_min   = (0 - self.f_rndx) * self.f_delta + self.f_0
        self.f_max   = (self.hdu_depth - 1 - self.f_rndx) * self.f_delta + self.f_0

        do_rev = False
        if self.f_min > self.f_max:
            do_rev = True
            tmp = self.f_min
            self.f_min = self.f_max
            self.f_max = tmp

        self.f_unit, self.f_min, self.f_max, self.f_0, self.f_delta = \
            self.conv_freq_units(
                self.f_unit,
                self.f_max,
                self.f_min, self.f_max, self.f_0, self.f_delta)
        if do_rev:
            self.ff      = np.linspace(self.f_max, self.f_min, self.hdu_depth)
        else:
            self.ff      = np.linspace(self.f_min, self.f_max, self.hdu_depth)
    
        # Adjust horizontal axis
        self.xSpaxSpinBox.setMinimum(0)
        self.xSpaxSpinBox.setMaximum(self.hdu_width - 1)
        
        if self.have_x_units:
            self.x_min   = (0 - self.x_rndx) * self.x_delta + self.x_0
            self.x_max   = (self.hdu_width - 1 - self.x_rndx) * self.x_delta + self.x_0
        else:
            self.x_min   = 0
            self.x_max   = 1
            self.x_delta = 1

        self.configureCoordAxis(
            self.xLabel,
            self.xStackedWidget,
            self.xSpinBox,
            self.x_mag,
            self.x_unit,
            self.x_min,
            self.x_max,
            self.x_delta)
        
        # Adjust vertical axis
        self.ySpaxSpinBox.setMinimum(0)
        self.ySpaxSpinBox.setMaximum(self.hdu_height - 1)
        
        if self.have_y_units:
            self.y_min   = (0 - self.y_rndx) * self.y_delta + self.y_0
            self.y_max   = (self.hdu_height - 1 - self.y_rndx) * self.y_delta + self.y_0
        else:
            self.y_min   = 0
            self.y_max   = 1
            self.y_delta = 1

        self.configureCoordAxis(
            self.yLabel,
            self.yStackedWidget,
            self.ySpinBox,
            self.y_mag,
            self.y_unit,
            self.y_min,
            self.y_max,
            self.y_delta)

    def set_hdu(self, hdu):
        self.hdu = hdu
        
        self.hdu_data       = self.hdu.data
        sane = self.hdu_data[~np.isnan(self.hdu_data) & ~np.isinf(self.hdu_data)]

        if len(sane) > 0:
            self.hdu_abs_min   = np.min(sane)
            self.hdu_abs_max   = np.max(sane)
        else:
            self.hdu_abs_min   = 0
            self.hdu_abs_max   = 1

        if len(self.hdu_data.shape) == 4 and self.hdu_data.shape[0] == 1:
            self.hdu_data = self.hdu_data.reshape( \
                self.hdu_data.shape[1],
                self.hdu_data.shape[2],
                self.hdu_data.shape[3])
            

        if self.hdu_depth != self.hdu_data.shape[0]:
            self._line = None
            self._sel  = None

        self.hdu_depth  = self.hdu_data.shape[0]
        self.hdu_height = self.hdu_data.shape[1]
        self.hdu_width  = self.hdu_data.shape[2]

        self.extract_hdu_unit_info()

        self.centralWavelengthSpin.setMinimum(self.f_min)
        self.centralWavelengthSpin.setMaximum(self.f_max)
        self.centralWavelengthSpin.setMinimum(self.f_min)
        self.centralWavelengthSpin.setMaximum(self.f_max)

        # The ideal step is given by the number of elements in the freq axis
        min_step = np.abs(self.f_delta)

        # The number of required decimals of this step can be approximated by:
        decimals = int(np.ceil(-np.log10(min_step)))
        self.centralWavelengthSpin.setDecimals(decimals)
        self.centralWavelengthSpin.setSingleStep(min_step)
        self.centralWavelengthSpin.setSuffix(fr' {self.f_unit}')
        self.centralWavelengthSpin.setValue(.5 * (self.f_max + self.f_min))

        self.passBandWidthSpin.setDecimals(decimals)
        self.passBandWidthSpin.setSingleStep(min_step)
        self.passBandWidthSpin.setMinimum(min_step)
        self.passBandWidthSpin.setMaximum(min_step * (self.hdu_depth))
        self.passBandWidthSpin.setValue(min_step)
        self.passBandWidthSpin.setSuffix(fr' {self.f_unit}')
        
        self.refresh_hdu()

        z1 = 256 / self.hdu_height
        z2 = 512 / self.hdu_width
        self.imageNav.setZoom(np.min([z1, z2]))
        self.zoomNav.setZoom(self.zoomNav.width() / 10)

        self.previewStackedWidget.setCurrentIndex(0)
        self.detailStackedWidget.setCurrentIndex(0)

        self._static_ax.set_xlim([self.f_min, self.f_max])
        self._static_ax.set_xlabel(f'{self.f_mag} ({self.f_unit})')
        self._static_ax.set_ylabel(f'{self.b_mag} ({self.b_unit})')

        self.fig.tight_layout()
        self.refresh_spectrum_scale(True)

        if not self.img_auto_scale_enabled():
            self.apply_current_img_scale()

        self.refresh_img_scale_info()

    def refresh_img_scale_info(self):
        min, max = self.imageNav.getCurrentLimits()
        self.imgScaleLabel.setText(
            f'<b>{self.mag_to_sci(min)} {self.b_unit}</b>' +\
                f' to <b>{self.mag_to_sci(max)} {self.b_unit}</b>'
        )
        
    def refresh_spectrum_scale(self, force_draw = False):
        if not self.autoscale:
            self._static_ax.relim()
            self._static_ax.set_ylim([self.hdu_abs_min, self.hdu_abs_max])
        else:
            self._static_ax.relim()
            self._static_ax.autoscale_view(True, True, True)

        if force_draw:
            self.fig.canvas.draw()

    def set_autoscale_spectrum(self, autoscale):
        self.autoscale = autoscale
        self._static_ax.set_autoscale_on(autoscale)
        self.refresh_spectrum_scale(True)

    def load_cube(self, filename):
        hdul = fits.open(filename)
        self.set_hdu(hdul[0])
        
    def set_img_mag_scale(self, baseNorm, zoom):
        # baseNorm is the relative base level of the image, with the following
        # interpretation:
        #
        # -1 means that the magnitude axis is always below 0 (min)
        # +1 means that the magnitude axis is always above 1 (max)
        #  0 means that min maps to 0 and max maps to 1:
        #

        full_range = self.hdu_abs_max - self.hdu_abs_min
        value_off  = baseNorm * full_range

        min = (self.hdu_abs_min + value_off) / zoom
        max = (self.hdu_abs_max + value_off) / zoom

        self.imageNav.setImageLimits(min, max)
        self.zoomNav.setImageLimits(min, max)

    def apply_current_img_scale(self):
        base_level_norm = self.baseLevelSlider.value() / self.baseLevelSlider.maximum()
        range_zoom      = 10. ** (4 * self.rangeSlider.value() / self.rangeSlider.maximum())
        self.set_img_mag_scale(base_level_norm, range_zoom)

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
        self.last_mov_x = x
        self.last_mov_y = y
        self.zoomNav.zoomToPoint(x, y)
        self.update_spectrum_at(int(np.floor(x)), int(np.floor(y)))

    def on_slice_changed(self):
        self.refresh_hdu()

    def on_selection_changed(self, last):
        px, py = self.imageNav.getSelection()
        self.set_selection_spaxel(px, py, last)

    def on_spax_spin_box_changed(self):
        px, py = self.get_selection_center()
        self.set_selection_spaxel(px, py)

    def on_angle_spin_box_changed(self):
        self.update_spaxel_from_spinboxes()

    def on_toggle_autoscale(self):
        self.set_autoscale_spectrum(self.autoScaleButton.isChecked())

    def on_blend_setting_changed(self):
        self.refresh_ui_state()
        if self.blend_enabled():
            self.imageNav.setBlendRadius(self.blendRadiusSpin.value())
            self.zoomNav.setBlendRadius(self.blendRadiusSpin.value())
        else:
            self.imageNav.setBlendRadius(None)
            self.zoomNav.setBlendRadius(None)
        
        # Force update of the selection
        px, py = self.get_selection_center()
        self.set_selection_spaxel(px, py)

        # And the spectrum
        if self.last_mov_x is not None and self.last_mov_y is not None:
            x = self.last_mov_x
            y = self.last_mov_y
            self.zoomNav.zoomToPoint(x, y)
            self.update_spectrum_at(int(np.floor(x)), int(np.floor(y)))

    def on_img_scale_changed(self):
        self.refresh_ui_state()

        if self.img_auto_scale_enabled():
            self.imageNav.setAutoScale(True)
            self.zoomNav.setAutoScale(True)
        else:
            self.imageNav.setAutoScale(False)
            self.zoomNav.setAutoScale(False)
            self.apply_current_img_scale()
        
        self.refresh_img_scale_info()

