import sys
from PyQt6 import QtWidgets
from .SimUiWindow import SimUiWindow
from radiosim import SimulationConfig

class SimUI:
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = SimUiWindow()

    def apply_params(self, params):
        self.window.apply_params(params)

    def set_config(self, config):
        self.config = config
        self.window.set_config(self.config)

    def run(self):
        self.window.show()
        return self.app.exec()

def startSimUi(params):
    ui = SimUI()

    # Initialization done, set some default config
    ui.apply_params(params)
    ui.set_config(SimulationConfig())

    return ui.run()



