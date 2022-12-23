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

