#!/usr/bin/env python3

import sys
import re

import radiosim.InterpolatedResponse
import radiosim.CompoundResponse
import radiosim.ResponsePainter
import radiosim.AttenuatedSpectrum
import radiosim.InterpolatedSpectrum
import radiosim.SpectrumPainter
import radiosim.DetectorSimulator

import numpy as np
import matplotlib.pyplot as plt
import sys, argparse
import traceback

# Input spectrums
lamp_2_150W   = radiosim.InterpolatedSpectrum('data/lamp-spectrum.csv')
lamp_2_150W.set_nominal_power_rating(2 * 150) # We know this consists of 2 x 150W watt sources

lamp_normal   = radiosim.InterpolatedSpectrum('data/lamp-spectrum-2.csv')

# Transmission coefficients
cryostat     = radiosim.InterpolatedResponse('data/t-cryostat.csv')
detector     = radiosim.InterpolatedResponse('data/t-detector.csv')
fprs         = radiosim.InterpolatedResponse('data/t-fprs.csv')
h_high       = radiosim.InterpolatedResponse('data/t-h-high.csv')
h            = radiosim.InterpolatedResponse('data/t-h.csv')
hk           = radiosim.InterpolatedResponse('data/t-hk.csv')
ifu          = radiosim.InterpolatedResponse('data/t-ifu.csv')
iz           = radiosim.InterpolatedResponse('data/t-iz.csv')
izj          = radiosim.InterpolatedResponse('data/t-izj.csv')
j            = radiosim.InterpolatedResponse('data/t-j.csv')
k            = radiosim.InterpolatedResponse('data/t-k.csv')
k_long       = radiosim.InterpolatedResponse('data/t-k-long.csv')
k_short      = radiosim.InterpolatedResponse('data/t-k-short.csv')
ltao_d       = radiosim.InterpolatedResponse('data/t-ltao-d.csv')
misalign     = radiosim.InterpolatedResponse('data/t-misalignment.csv')
preoptics    = radiosim.InterpolatedResponse('data/t-preoptics.csv')
scao_d       = radiosim.InterpolatedResponse('data/t-scao-d.csv')
spectrograph = radiosim.InterpolatedResponse('data/t-spectrograph.csv')
vis          = radiosim.InterpolatedResponse('data/t-vis.csv')
z            = radiosim.InterpolatedResponse('data/t-z.csv')

# Equalizer filters
eq_vis       = radiosim.InterpolatedResponse('data/f-vis.csv')
eq_lr1       = radiosim.InterpolatedResponse('data/f-lr1.csv')
eq_lr2       = radiosim.InterpolatedResponse('data/f-lr2.csv')
eq_mr1       = radiosim.InterpolatedResponse('data/f-mr1.csv')
eq_mr2       = radiosim.InterpolatedResponse('data/f-mr2.csv')
eq_mr3       = radiosim.InterpolatedResponse('data/f-mr3.csv')
eq_mr4       = radiosim.InterpolatedResponse('data/f-mr4.csv')
eq_hr1       = radiosim.InterpolatedResponse('data/f-hr1.csv')
eq_hr2       = radiosim.InterpolatedResponse('data/f-hr2.csv')
eq_hr3       = radiosim.InterpolatedResponse('data/f-hr3.csv')
eq_hr4       = radiosim.InterpolatedResponse('data/f-hr4.csv')

# Grating configurations (passband filter, equalizer, R, lambda_min, lambda_max)
# This was taken from HRM-0114 (2D11)
gratings = {
    "VIS" : (vis,     eq_vis,  3000, 0.462e-6, 0.812e-6),
    "LR1" : (izj,     eq_lr1,  3327, 0.811e-6, 1.369e-6),
    "LR2" : (hk,      eq_lr2,  3327, 1.450e-6, 2.450e-6),
    "MR1" : (iz,      eq_mr1,  7050, 0.830e-6, 1.050e-6),
    "MR2" : (j,       eq_mr2,  7050, 1.046e-6, 1.324e-6),
    "MR3" : (h,       eq_mr3,  7050, 1.435e-6, 1.815e-6),
    "MR4" : (k,       eq_mr4,  7050, 1.951e-6, 2.469e-6),
    "HR1" : (z,       eq_hr1, 18000, 0.827e-6, 0.903e-6),
    "HR2" : (h_high,  eq_hr2, 18000, 1.538e-6, 1.678e-6),
    "HR3" : (k_short, eq_hr3, 18000, 2.017e-6, 2.201e-6),
    "HR4" : (k_long,  eq_hr4, 18000, 2.199e-6, 2.399e-6)
}

# Scale configurations (scale to A_p, binning)
# Calculation of the effective light gathered by a pixel is calculated
# with respect to the finest scale. We need to take into account that:
#
# 1. Nominal scales do not correspond exactly to actual spaxel sizes.
# 2. HRM-00190: 1 spaxel maps to 1 px along the slice (spatial x direction)
#    and 2 px across the slice (spectral direction). This implies that the
#    light is distributed along 2 pixels.
# 3. HRM-00178: 1 spaxel is made to fit exactly 1 slice width.
# 4. Pixel size is 13.3 µm 
# 5. The coarsest scale (60x30) consists of a patch in the sky that is
#    larger in the X direction than in the Y direction.
# 6. The finest scale must correspond to a 1:1 magnification w.r.t ELT's focal plane
#

HARMONI_FINEST_SPAXEL_SIZE = 4.14    # mas
HARMONI_PIXEL_SIZE         = 13.3e-6 # m
HARMONI_PX_PER_SP_ALONG    = 1       # From: HRM-00190
HARMONI_PX_PER_SP_ACROSS   = 2       # From: HRM-00190
HARMONI_PX_AREA            = HARMONI_PIXEL_SIZE * HARMONI_PIXEL_SIZE

# Format of the array:
scales = {
    ( 4,   4) : (  HARMONI_FINEST_SPAXEL_SIZE, HARMONI_FINEST_SPAXEL_SIZE ),
    (10,  10) : (                          10,                         10 ),
    (20,  20) : (                          20,                         20 ),
    (60,  30) : (                          60,                         30 )
}

def makeResponse(grating = "VIS", ao = "NOAO"):
    response = radiosim.CompoundResponse()
    ao       = ao.upper()
    grating  = grating.upper()

    if ao == "SCAO":
        response.push_back(scao_d)
    elif ao == "LTAO":
        response.push_back(ltao_d)
    elif ao != "NOAO":
        raise Exception("Undefined AO configuration " + ao)
    
    if not grating in gratings:
        raise Exception("No such grating configuration: " + grating)
    
    response.push_back(fprs)
    response.push_back(cryostat)
    response.push_back(preoptics)
    response.push_back(ifu)
    response.push_back(spectrograph)

    # Push appropriate band filter
    response.push_back(gratings[grating][0])

    # Push equalizer
    response.push_back(gratings[grating][1])

    response.push_back(misalign)
    response.push_back(detector)

    return response


def debugResponse():
    painter  = radiosim.ResponsePainter('Optical train response')

    painter.plot(response, grating + ", " + ao)

    fig, ax = plt.subplots(1, 3)
    fig.tight_layout()
    painter = radiosim.SpectrumPainter('Output spectrum')

    config = grating + ", " + ao

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
grating  = "VIS"
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
    default = grating,
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
grating  = args.grating
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
scale = (int(result.group(1)), int(result.group(2)))

if scale not in scales:
    print("Scale %dx%d not supported by HARMONI".format(scale[0], scale[1]))
    sys.exit(1)

if lampcfg == "150W":
    lamp = lamp_2_150W
elif lampcfg == "NORMAL":
    lamp = lamp_normal
else:
    print("Lamp configuration {0} not understood".format(lampcfg))
    sys.exit(1)

lambda_min = gratings[grating][3]
lambda_max = gratings[grating][4]

########################### Model initialization #############################

try:
    # Initialize optical train
    response = makeResponse(grating = grating, ao = ao)

    # Initialize spectrum
    spectrum = radiosim.AttenuatedSpectrum(lamp)
    spectrum.push_filter(response)
    spectrum.set_fnum(f)

    if power > 0:
        spectrum.adjust_power(power)
    
    # Initialize detector
    dimRelX = scales[scale][0] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ALONG)
    dimRelY = scales[scale][1] / (HARMONI_FINEST_SPAXEL_SIZE * HARMONI_PX_PER_SP_ACROSS)
    A_sp    = HARMONI_PX_AREA * dimRelX * dimRelY

    det = radiosim.DetectorSimulator(
            spectrum,
            A_sp    = A_sp,
            R       = gratings[grating][2],
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
                scale[0],
                scale[1]
            ))

        title = 'Exposition time estimate ({0}, {1}, RON = {2} $e^-$, G = {3} $e^-/$adu)'.format(
            grating,
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
                grating,
                ao,
                scale[0],
                scale[1],
                ron,
                G)
        else:
            plt.ylabel('Total $e^-$')
            title = 'Photoelectrons vs spaxel $\lambda$ ({0}, {1}, {2}x{3})'.format(
                grating,
                ao,
                scale[0],
                scale[1])

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
