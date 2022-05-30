from . import StageResponse
import numpy as np

class CompoundResponse(StageResponse.StageResponse):
    def __init__(self):
        self.stages = []
    
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

