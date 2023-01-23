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

class PlotWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)

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
        
    def plot(self, *args, xlabel = None, ylabel = None, xlim = None, ylim = None, label = None, title = None, **kwargs):
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
        self._static_ax.cla()
