from abc import ABC, abstractmethod
import numpy as np

class StageResponse(ABC):
    @abstractmethod
    def get_t(self, wl):
        pass

    def get_t_matrix(self, wl_matrix):
        if len(wl_matrix.shape) != 1:
            raise Exception("High-order tensors not yet supported")
        
        return np.apply_along_axis(self.get_t, 1, wl_matrix)

    def t(self, wl):
        if isinstance(wl, np.ndarray):
            return self.get_t_matrix(wl)
        else:
            return self.get_t(wl)
    
    def apply(self, wl, spectrum = None):
        if isinstance(wl, np.ndarray):
            if spectrum is None:
                # Compound call
                if len(wl.shape) != 2 or wl.shape[0] != 2:
                    raise Exception("Invalid shape for the compound wavelength / spectrum array")
                
                return self.apply(wl[0, :], wl[1, :])
            elif isinstance(spectrum, np.ndarray):
                # Separate call
                if len(wl.shape) != 1:
                    raise Exception("Invalid shape for the wavelength axis " + str(wl.shape))
                
                if len(wl) != len(spectrum):
                    raise Exception("Wavelength and spectrum arrays size mismatch")

                # Just a product
                return self.get_t_matrix(wl) * spectrum
        elif isinstance(wl, float) and isinstance(spectrum, float):
            return self.get_t(wl) * spectrum
        else:
            raise Exception("Invalid combination of wavelength and spectrum parameter types ({0} and {1})".format(str(type(wl)), str(type(spectrum))))
