import numpy as np
from . import StageResponse
import scipy.interpolate

class InterpolatedResponse(StageResponse.StageResponse):
    def __init__(self, file):
        super().__init__()
        
        resp = np.genfromtxt(file, delimiter = ',')

        # This looks transposed
        if resp.shape[0] == 2 and resp.shape[1] != 2:
            resp = resp.transpose()
        
        resp[:, 0] *= 1e-6 # Adjust units from µm to m

        self.interpolator = scipy.interpolate.interp1d(
            resp[:, 0],
            resp[:, 1],
            bounds_error = False,
            fill_value = 0.)
    
    def get_t(self, wl):
        # Numpy horrors
        return self.interpolator(wl).ravel()[0]

    def get_t_matrix(self, wl):
        return self.interpolator(wl)
