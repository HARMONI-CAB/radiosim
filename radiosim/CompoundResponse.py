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

from . import StageResponse
import numpy as np

class CompoundResponse(StageResponse.StageResponse):
    def __init__(self, repeat_train = False):
        super().__init__()
        self._stages = []
        self._repeat_train = repeat_train

    def set_multiplicity(self, mult):
        if self._repeat_train:
            # Repeat train: multiplicity set at compound level
            StageResponse.set_multiplicity(mult)
        else:
            # Do not repeat train: multiplicity set at component level
            for s in self._stages:
                s.set_multiplicity(mult)
        
    def get_components(self):
        labels = []

        for stage in self._stages:
            labels.append(stage.get_label())
        
        return labels

    def prune_forward(self, what):
        ndx = -1
        for i in range(len(self._stages)):
            if self._stages[i].get_label() == what:
                ndx = i
                break
        
        if ndx >= 0:
            self._stages = self._stages[:ndx]
        return ndx

    def prune(self, what: list):
        actual_stages = []

        for i in range(len(self._stages)):
            label = self._stages[i].get_label()
            if label not in what:
                actual_stages.append(self._stages[i])

        self._stages = actual_stages

    def stages(self):
        return self._stages
    
    def get_entrance_node_name(self):
        return self._stages[0].get_entrance_node_name()

    def get_exit_node_name(self):
        return self._stages[-1].get_exit_node_name()

    def gen_graphivz_internal_nodes(self):
        output = ''

        # Step 1: Generate all graphiz data
        for s in self._stages:
            graphviz = s.get_graphviz()
            output += graphviz + '\n'

        output += '\n'

        # Step 2: Connect
        prev = None
        for s in self._stages:
            if prev is not None:
                output += f'{prev.get_exit_node_name()} -> {s.get_entrance_node_name()};\n'
            prev = s

        return output

    def get_graphviz(self):
        return fr'''
        subgraph {self._name} {{
            label="{self._label}";
            {self.gen_graphivz_internal_nodes()}
        }}
        '''

    def push_front(self, stage, fnum = None):
        if fnum is not None:
            stage.set_fnum(fnum)
        self._stages.insert(0, stage)

    def push_back(self, stage, fnum = None):
        if fnum is not None:
            stage.set_fnum(fnum)
        self._stages.append(stage)

    def get_t(self, wl):
        response = 1.

        for s in self._stages:
            response *= s.t(wl)
        
        return response
    
    def get_t_matrix(self, wl):
        response = np.ones(wl.shape)

        for s in self._stages:
            response *= s.t(wl)

        return response
    
    #
    # The reason why we rewrite apply_array and apply_scalar here is because
    # the different stages may be at different temperatures. If we rely on the
    # default implementation, we would end up calculating a non-realistic emissivity
    # based on a fixed temperature.
    #
    # On the other hand, apply_array/apply_scalar assumes that the multiplicity has
    # already been applied to the response. Since set_multiplicity is applied at
    # CompoundResponse level and not individual response level (since the multiplicity
    # of a compound response refers to how many times the whole train is repeated and
    # not to how many times each individual component is consecutively repeated), we
    # need to round up self._exp to the nearest integer and apply the whole train
    # repeatedly.
    #

    def apply_array(self, wl, spectrum = None, thermal = True):
        result = spectrum
        n = int(np.round(self.get_multiplicity()))
        
        while n > 0:
            for s in self._stages:
                result = s.apply_array(wl, result, thermal)
            n -= 1
        return result

    def apply_scalar(self, wl, spectrum = None, thermal = True):
        result = spectrum
        n = int(np.round(self.get_multiplicity()))
        
        while n > 0:
            for s in self._stages:
                result = s.apply_scalar(wl, result, thermal)
            n -= 1
        return result