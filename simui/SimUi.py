import sys
from PyQt6 import QtWidgets
from .SimUiWindow import SimUiWindow

class SimUI:
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = SimUiWindow()

    def apply_params(self, params):
        self.window.apply_params(params)

    def run(self):
        self.window.show()
        return self.app.exec()

def startSimUi(params):
    ui = SimUI()
    ui.apply_params(params)

    return ui.run()



