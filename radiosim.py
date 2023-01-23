#!/usr/bin/env python3
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

import sys
import re

import radiosim.InterpolatedResponse
import radiosim.CompoundResponse
import radiosim.ResponsePainter
import radiosim.AttenuatedSpectrum
import radiosim.InterpolatedSpectrum
import radiosim.SpectrumPainter
import radiosim.DetectorSimulator
import radiosim.Parameters

from radiosim.Parameters import \
    HARMONI_FINEST_SPAXEL_SIZE, HARMONI_PX_PER_SP_ALONG, \
    HARMONI_PX_PER_SP_ACROSS, HARMONI_PX_AREA

import numpy as np
import matplotlib.pyplot as plt
import sys, argparse
import traceback

params = radiosim.Parameters()
params.load_defaults()

def debugResponse():
    painter  = radiosim.ResponsePainter('Optical train response')

    painter.plot(response, grating_spec + ", " + ao)

    fig, ax = plt.subplots(1, 3)
    fig.tight_layout()
    painter = radiosim.SpectrumPainter('Output spectrum')

    config = grating_spec + ", " + ao

    painter.plot(lamp,     "IFS output", ax = ax[0], log = log, frequency = freq)
    painter.plot(spectrum, "Filtered (" + config + ")", ax = ax[0], log = log, frequency = freq)

    painter.title = "Photon field"

    painter.plot(lamp,     "IFS output", ax = ax[1], log = log, photons = True, frequency = freq)
    painter.plot(spectrum, "Filtered (" + config + ")", ax = ax[1], log = log, photons = True, frequency = freq)

    painter.title = "Total attenuation (w.r.t Planck)"
    painter.compare_to_planck(lamp,     ax = ax[2], log = log, frequency = freq)
    painter.compare_to_planck(spectrum, ax = ax[2], log = log, frequency = freq)

    plt.show()


############################# Argument parsing ###############################
log      = False
freq     = False
do_debug = False
poisson  = False
grating_spec  = "VIS"
ao       = "NOAO"
f        = 17.757 # Relay optics f/N (HRM-00509, page 16)
lampcfg  = "150W"
scale_s  = "4x4"
t_exp    = -1
exp_est  = False
max_c    = 20000
ron      = 5      # electrons per exposure. This is actually the
                  # standard deviation of a normal distribution
G        = 1      # gain (electrons per count)
counts   = False  # Plot counts instead of electrons
power    = -1     # Adjust power rating of the lamp

parser = argparse.ArgumentParser(
        description = "Simulate total amount of photoelectrons")

parser.add_argument(
    "-g",
    dest = "grating",
    default = grating_spec,
    help = "define the grating configuration according to HRM-0114")

parser.add_argument(
    "-s",
    dest = "scale",
    default = scale_s,
    help = "define the instrument scale configuration according to HRM-0114")

parser.add_argument(
    "-a",
    dest = "ao",
    default = ao,
    help = "define the AO dichroic configuration (NOAO, SCAO or LTAO)")

parser.add_argument(
    "-l",
    dest = "lampcfg",
    default = lampcfg,
    help = "define the lamp configuration (150W or NORMAL)")

parser.add_argument(
    "-d",
    dest = "do_debug",
    action = 'store_true',
    default = do_debug,
    help = "debug the transmission spectrum of the current optical train")

parser.add_argument(
    "-t",
    dest = "t_exp",
    type = float,
    default = t_exp,
    help = "specify a given exposition time (seconds)")

parser.add_argument(
    "-G",
    dest = "G",
    type = float,
    default = G,
    help = "specify CCD gain in electrons per count (default 1)")

parser.add_argument(
    "-L",
    dest = "log",
    action = 'store_true',
    default = log,
    help = "use logarithmic scales")

parser.add_argument(
    "-c",
    dest = "counts",
    action = 'store_true',
    default = counts,
    help = "plot counts instead of photoelectrons (includes RON)")

parser.add_argument(
    "-r",
    dest = "ron",
    type = float,
    default = ron,
    help = "specify readout noise (in electrons, default 5)")

parser.add_argument(
    "-P",
    dest = "power",
    type = float,
    default = power,
    help = "specify lamp power (only for lamp sources with nominal power rating)")

parser.add_argument(
    "-p",
    dest = "poisson",
    action = 'store_true',
    default = poisson,
    help = "simulate photon arrival as shot noise (Poisson)")

parser.add_argument(
    "-e",
    dest = "exp_est",
    action = 'store_true',
    default = exp_est,
    help = "estimate exposition time before saturation")

parser.add_argument(
    "-C",
    dest = "max_c",
    type = int,
    default = max_c,
    help = "max number of counts before saturation")

parser.add_argument(
    "-f",
    action = 'store_true',
    dest = "freq",
    default = freq,
    help = "use frequency instead of wavelength for spectrum representation")

args = parser.parse_args()

log      = args.log
freq     = args.freq
do_debug = args.do_debug
grating_spec  = args.grating
ao       = args.ao
lampcfg  = args.lampcfg
scale_s  = args.scale
poisson  = args.poisson
t_exp    = args.t_exp
G        = args.G
counts   = args.counts
ron      = args.ron
power    = args.power
exp_est  = args.exp_est
max_c    = args.max_c

# Sanity checks
result = re.search(r"(\d+)x(\d+)", scale_s)
if result is None:
    print("Invalid scale setting {0}".format(sys.argv[3]))
    sys.exit(1)
scale_spec = (int(result.group(1)), int(result.group(2)))

scale = params.get_scale(scale_spec)

if scale is None:
    print("Scale {0}x{1} not supported by HARMONI".format(scale_spec[0], scale_spec[1]))
    print("Supported scales are:", ", ".join([fr'{s[0]}x{s[1]}' for s in  params.get_scales()]))
    sys.exit(1)

lamp = params.get_lamp(lampcfg)
if lamp is None:
    print("Lamp configuration {0} not understood".format(lampcfg))
    print("Supported lamps are:", ", ".join(params.get_lamp_names()))
    sys.exit(1)

grating = params.get_grating(grating_spec)
if grating is None:
    print(fr"Unsupported grating '{grating_spec}'.")
    print("Supported gratings are:", ", ".join(params.get_grating_names()))
    sys.exit(1)

lambda_min = grating[3]
lambda_max = grating[4]

########################### Model initialization #############################

try:
    # Initialize optical train
    response = params.make_response(grating = grating_spec, ao = ao)

    # Initialize spectrum
    spectrum = radiosim.AttenuatedSpectrum(lamp)
    spectrum.push_filter(response)
    spectrum.set_fnum(f)

    if power > 0:
        spectrum.adjust_power(power)
    
    # Initialize detector
    dimRelX = scale[0] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ALONG)
    dimRelY = scale[1] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ACROSS)
    A_sp    = HARMONI_PX_AREA * dimRelX * dimRelY

    det = radiosim.DetectorSimulator(
            spectrum,
            A_sp    = A_sp,
            R       = grating[2],
            poisson = poisson,
            G       = G,
            ron     = ron)
    
    if exp_est:
        max_wl = spectrum.get_max_wl()
        print('Brightest wavelength: {0:g} µm'.format(max_wl * 1e6))
        prob = det.getTexpDistribution(max_wl, max_c)
        plt.figure()
        plt.plot(
            prob[0,:],
            prob[1,:],
            label = '$\lambda = {0:g}{{\mu}}m$, $c_{{max}}$ = {1} ADU, scale ${2}x{3}$'.format(
                max_wl * 1e6,
                max_c,
                scale_spec[0],
                scale_spec[1]
            ))

        title = 'Exposition time estimate ({0}, {1}, RON = {2} $e^-$, G = {3} $e^-/$adu)'.format(
            grating_spec,
            ao,
            ron,
            G)
        
        plt.xlabel('$t_{exp} (s)$')
        plt.ylabel('$p(t_{exp}|c_{max})$')

    else:
        # Compute photoelectrons per pixel
        if t_exp < 0:
            exps = [5, 10, 30, 60, 120]
        else:
            exps = [t_exp]

        wl = np.linspace(lambda_min, lambda_max, 1000)

        for t in exps:
            if counts:
                y = det.countsPerPixel(wl = wl, t = t)
            else:
                y = det.electronsPerPixel(wl = wl, t = t)
            plt.plot(wl * 1e6, y, label = '$t_{exp}=$' + str(t) + ' s')

        plt.xlabel('Wavelength ($\mu m$)')

        if counts:
            plt.ylabel('ADC output')
            title = 'Counts vs spaxel $\lambda$ ({0}, {1}, {2}x{3}, RON = {4} $e^-$, G = {5} $e^-/$adu)'.format(
                grating_spec,
                ao,
                scale_spec[0],
                scale_spec[1],
                ron,
                G)
        else:
            plt.ylabel('Total $e^-$')
            title = 'Photoelectrons vs spaxel $\lambda$ ({0}, {1}, {2}x{3})'.format(
                grating_spec,
                ao,
                scale_spec[0],
                scale_spec[1])

    if power > 0:
        title += ', {0:g} W source'.format(power)

    plt.title(title)
    plt.legend()

except Exception as e:
    print("\033[1;31mSimulator exception: \033[0;1m{0}\033[0m".format(e))
    print("\033[1;30m")
    traceback.print_exc()
    print("\033[0m")
    sys.exit(1)


plt.grid()

if do_debug:
    debugResponse()

plt.show()
