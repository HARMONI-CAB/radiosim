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

from PyQt6 import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.pyplot import setp

class PlotWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        self.cycle = 0
        self.limits = {}
        self.limits_visible = False
        self.fig = Figure()
        self.fig.tight_layout()
        static_canvas = FigureCanvas(self.fig)
        
        
        # Ideally one would use self.addToolBar here, but it is slightly
        # incompatible between PyQt6 and other bindings, so we just add the
        # toolbar as a plain widget instead.

        layout.addWidget(NavigationToolbar(static_canvas, self))
        layout.addWidget(static_canvas)

        self._static_ax = static_canvas.figure.subplots()
        self.log_scale  = False

    def resizeEvent(self, event):
        self.fig.tight_layout()
    
    def set_log_scale(self, enabled):
        self.log_scale = enabled
        self._static_ax.set_yscale("log" if self.log_scale else "linear")
        self.fig.canvas.draw()
        
    def draw_limit(self, name: str):
        plot = self.limits[name][0]
        if plot is not None:
            plot.remove()

        xmin   = self.limits[name][1]
        xmax   = self.limits[name][2]
        height = self.limits[name][3]
        self.limits[name][0], = self._static_ax.plot(
            [xmin, xmax],
            [height, height],
            linestyle = 'dashed',
            color = 'red',
            zorder = 10)
        self.fig.tight_layout()
        self.fig.canvas.draw()

    def set_limits_visible(self, visible: bool):
        if visible != self.limits_visible:
            self.limits_visible = visible

            if visible:
                for name in self.limits:
                    self.draw_limit(name)
            else:
                for name in self.limits:
                    plot = self.limits[name][0]
                    if plot is not None:
                        plot.remove()
                    plot = self.limits[name][0] = None
        
    def set_limit(self, name: str, xmin: float, xmax: float, height: float):
        if name in self.limits:
            self.limits[name][1] = xmin
            self.limits[name][2] = xmax
            self.limits[name][3] = height
        else:
            self.limits[name] = [None, xmin, xmax, height]
        
        if self.limits_visible:
            self.draw_limit(name)
    
    def plot(self, *args, xlabel = None, ylabel = None, xlim = None, ylim = None, label = None, title = None, stem = False, **kwargs):
        if stem:
            linefmt = fr'C{self.cycle}-'
            basefmt = fr'C{self.cycle}-'
            markerfmt = fr'C{self.cycle}o'
            self.cycle += 1
            markerline, stemline, baseline, = self._static_ax.stem(*args, linefmt = linefmt, markerfmt = markerfmt, basefmt = basefmt, label = label, *kwargs)
            setp(stemline, linewidth = .5)
            setp(baseline, linewidth = 1.25)
            setp(markerline, markersize = 2.5)
        else:
            self._static_ax.plot(*args, label = label, *kwargs)
        if xlabel is not None:
            self._static_ax.set_xlabel(xlabel)
        if ylabel is not None:
            self._static_ax.set_ylabel(ylabel)
        if xlim is not None:
            self._static_ax.set_xlim(xlim)
        if ylim is not None:
            self._static_ax.set_ylim(ylim)
        if label is not None:
            self._static_ax.legend()
        if title is not None:
            self._static_ax.set_title(title)

        self._static_ax.grid(True)
        self.fig.tight_layout()
        self.fig.canvas.draw()

    def clear(self):
        self.cycle = 0
        self.limits = {}
        self._static_ax.cla()
