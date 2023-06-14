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

SPEED_OF_LIGHT  = 299792458      # m / s
PLANCK_CONSTANT = 6.62607015e-34 # J * s
WIEN_B          = 2.897771955e-3 # m * K
BOLTZMANN       = 1.380649e-23   # J / K
PROTONMASS      = 1.6726219e-27  # kg

from .CompoundResponse       import CompoundResponse
from .InterpolatedResponse   import InterpolatedResponse
from .ResponsePainter        import ResponsePainter
from .StageResponse          import StageResponse
from .AllPassResponse        import AllPassResponse

from .PowerSpectrum          import PowerSpectrum
from .IsotropicRadiatorSpectrum import IsotropicRadiatorSpectrum

from .AttenuatedSpectrum     import AttenuatedSpectrum
from .InterpolatedSpectrum   import InterpolatedSpectrum
from .SpectrumPainter        import SpectrumPainter
from .RadianceSpectrum       import RadianceSpectrum
from .OverlappedSpectrum     import OverlappedSpectrum
from .LineSpectrum           import LineSpectrum
from .ISRadianceSpectrum     import ISRadianceSpectrum

from .DetectorSimulator      import DetectorSimulator
from .DetectorSimulator      import TExpSimulator

from .Parameters             import Parameters
from .SimulationConfig       import SimulationConfig
from .SimulationConfig       import DetectorConfig
from .SimulationConfig       import LampConfig

