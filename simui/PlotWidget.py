from PyQt6 import QtWidgets
from PyQt6.QtCore import QObject
import numpy as np
import time
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
