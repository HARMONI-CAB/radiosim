#!/usr/bin/env python3

import simui

import radiosim.Parameters

params = radiosim.Parameters()

params.load_defaults()

simui.startSimUi(params)

