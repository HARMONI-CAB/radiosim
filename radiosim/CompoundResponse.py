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
    def __init__(self):
        self.stages = []
    
    def get_entrance_node_name(self):
        return self.stages[0].get_entrance_node_name()

    def get_exit_node_name(self):
        return self.stages[-1].get_exit_node_name()

    def gen_graphivz_internal_nodes(self):
        output = ''

        # Step 1: Generate all graphiz data
        for s in self.stages:
            graphviz = s.get_graphviz()
            output += graphviz + '\n'

        output += '\n'

        # Step 2: Connect
        prev = None
        for s in self.stages:
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

    def push_front(self, stage):
        self.stages.insert(0, stage)

    def push_back(self, stage):
        self.stages.append(stage)

    def get_t(self, wl):
        response = 1.

        for s in self.stages:
            response *= s.get_t(wl)
        
        return response
    
    def get_t_matrix(self, wl):
        response = np.ones(wl.shape)

        for s in self.stages:
            response *= s.get_t_matrix(wl)

        return response

