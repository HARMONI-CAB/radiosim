
from PyQt6 import QtCore, uic, QtGui
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import QtWidgets
from parse import parse
import math

class QDegSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        self.setFormat('dms')
        super().__init__(*args, **kwargs)
        self.setMinimum(0)
        self.setMaximum(360 - 1e-3 / 3600)
        self.setSingleStep(1e-3 / 3600)
        self.setDecimals(13)

    def setFormat(self, formatStr):
        if formatStr == 'hms':
            self.parseString = self.hms2deg
            self.toString    = self.deg2hms
        elif formatStr == 'dms':
            self.parseString = self.dms2deg
            self.toString    = self.deg2dms
        else:
            raise RuntimeError(f'Invalid format "{formatStr}"')
    
    def parseString(self):
        raise NotImplementedError('Abstract method')
    
    def toString(self):
        raise NotImplementedError('Abstract method')
    
    def textFromValue(self, value):
        return self.toString(value)

    def valueFromText(self, text):
        return self.parseString(text)

    def deg2dms(self, deg):
        i_deg = math.floor(deg)
        min   = (deg - i_deg) * 60
        i_min = math.floor(min)
        sec   = (min - i_min) * 60
        return f'{i_deg:3d}º {i_min:2d}\' {sec:2.3f}\"'

    def deg2hms(self, deg):
        hours  = deg * (12 / 180)
        i_hour = math.floor(hours)
        min    = (hours - i_hour) * 60
        i_min  = math.floor(min)
        sec    = (min - i_min) * 60
        return f'{i_hour:2d}h {i_min:2d}m {sec:2.3f}s'

    def dms2deg(self, string):
        result = parse("{3i}º {2i}' {2.3f}\"", string)
        if result is None:
            return None

        deg = float(result[0])
        min = float(result[1])
        sec = float(result[2])

        return deg + (min + sec / 60) / 60

    def hms2deg(self, string):
        result = parse("{2i}h {2i}m {2.3f}s", string)
        if result is None:
            return None

        hour = float(result[0])
        min = float(result[1])
        sec = float(result[2])

        return (hour + (min + sec / 60) / 60) * (180 / 12)
    