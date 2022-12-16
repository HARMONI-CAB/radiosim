from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6 import QtWidgets
from PyQt6 import uic

import pathlib

from radiosim.Parameters import HARMONI_PIXEL_SIZE, \
    HARMONI_FINEST_SPAXEL_SIZE, HARMONI_PX_PER_SP_ALONG, \
    HARMONI_PX_PER_SP_ACROSS, HARMONI_PX_AREA

class SimUiWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        dir = pathlib.Path(__file__).parent.resolve()
        uic.loadUi(fr"{dir}/simui.ui", self)
        self.setWindowTitle("QRadioSim - The HARMONI's radiometric simulator")
        self.refresh_ui_state()
        self.connect_all()
        
    def connect_all(self):
        self.lamp1TypeCombo.activated.connect(self.on_state_widget_changed)
        self.lamp2TypeCombo.activated.connect(self.on_state_widget_changed)
        self.passBandCombo.activated.connect(self.on_state_widget_changed)
        self.tExpPassBandRadio.toggled.connect(self.on_state_widget_changed)

    def refresh_params(self):
        gratings = self.params.get_grating_names()

        # Add lamps
        self.lamp1TypeCombo.clear()
        self.lamp2TypeCombo.clear()

        self.lamp1TypeCombo.addItem('Off', userData = None)
        self.lamp2TypeCombo.addItem('Off', userData = None)

        lamps = self.params.get_lamp_names()

        for lamp in lamps:
            self.lamp1TypeCombo.addItem(lamp, userData = self.params.get_lamp(lamp))
            self.lamp2TypeCombo.addItem(lamp, userData = self.params.get_lamp(lamp))                

        # Add gratings
        self.gratingCombo.clear()
        self.gratingCombo.addItems(gratings)
        
        # Add AO modes
        self.aoModeCombo.clear()
        self.aoModeCombo.addItems(self.params.get_ao_mode_names())

        # Add scales
        self.scaleCombo.clear()
        scales = self.params.get_scales()
        for s in scales:
            self.scaleCombo.addItem(fr'{s[0]}x{s[1]}', userData = s)

        # Populate passband centers:
        self.passBandCombo.clear()
        for g in gratings:
            grating = self.params.get_grating(g)
            name    = grating[5]
            center  = .5 * (grating[3] + grating[4])
            self.passBandCombo.addItem(
                fr'{name} ({center * 1e6:.3f} µm)', userData = center)
        

        # Add detector defaults
        self.pxSizeSpin.setValue(HARMONI_PIXEL_SIZE * 1e6)

        self.refresh_ui_state()
        
    def apply_params(self, params):
        self.params = params
        self.refresh_params()


    def refresh_lamp_control_ui_state(self):
        # Lamp control
        lamp1 = self.lamp1TypeCombo.currentData()
        lamp2 = self.lamp2TypeCombo.currentData()

        lamp1Adjustable = lamp1 is not None and lamp1.is_adjustable()
        lamp2Adjustable = lamp2 is not None and lamp2.is_adjustable()

        self.lamp1PowerSpin.setEnabled(lamp1Adjustable)
        self.lamp2PowerSpin.setEnabled(lamp2Adjustable)

        if lamp1Adjustable:
            self.lamp1PowerSpin.setValue(lamp1.get_power())

        if lamp2Adjustable:
            self.lamp2PowerSpin.setValue(lamp2.get_power())

        self.lamp1AttenLabel = fr'{self.lamp1AttenSlider.value()} %'
        self.lamp2AttenLabel = fr'{self.lamp2AttenSlider.value()} %'

        self.lamp1AttenSlider.setEnabled(lamp1 is not None)
        self.lamp2AttenSlider.setEnabled(lamp2 is not None)

    def refresh_exp_time_ui_state(self):
        passBandCenterEnabled = self.tExpPassBandRadio.isChecked()
        self.passBandCombo.setEnabled(passBandCenterEnabled)
        self.tExpWlSpin.setEnabled(self.tExpCustomLambdaRadio.isChecked())

        if passBandCenterEnabled:
            wl = self.passBandCombo.currentData()
            if wl is not None:
                self.tExpWlSpin.setValue(wl * 1e6)
        
    def refresh_ui_state(self):
        self.refresh_lamp_control_ui_state()
        self.refresh_exp_time_ui_state()

    # Interactivity slots
    def on_state_widget_changed(self):
        self.refresh_ui_state()


