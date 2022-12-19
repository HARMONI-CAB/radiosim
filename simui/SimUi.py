import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QObject
from .SimUiWindow import SimUiWindow
from radiosim import SimulationConfig

class SimUI(QObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = QtWidgets.QApplication(sys.argv)
        self.window = SimUiWindow()
        self.window.plotSpectrum.connect(self.on_plot_spectrum)
        self.window.overlaySpectrum.connect(self.on_overlay_spectrum)

    def apply_params(self, params):
        self.window.apply_params(params)

    def set_config(self, config):
        self.config = config
        self.window.set_config(self.config)

    def run(self):
        self.window.show()
        return self.app.exec()

    ################################# Slots ####################################
    def on_plot_spectrum(self):
        print('Plot spectrum!')
        pass

    def on_overlay_spectrum(self):
        print('Overlay spectrum!')
        pass

def startSimUi(params):
    ui = SimUI()

    # Initialization done, set some default config
    ui.apply_params(params)
    ui.set_config(SimulationConfig())

    return ui.run()



