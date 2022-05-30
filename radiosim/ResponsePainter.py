import matplotlib.pyplot as plt
import numpy as np

class ResponsePainter:
    def __init__(self, title = "Untitled filter"):
        self.title    = title

    def plot(self, response, desc = 'Untitled filter', start = 400e-9, end = 2.5e-6, step = 1e-9, ax = None, log = False):
        if ax is None:
            plt.figure()
            ax = plt.gca()
        
        wl = np.linspace(start, end, int((end - start) / step))
        ax.plot(wl * 1e6, response.t(wl), label = desc)
        ax.set_xlabel('Wavelength (µm)')
        ax.set_ylabel('Transmission coefficient')
        ax.set_xlim([start * 1e6, end * 1e6])
        ax.set_ylim([1e-9, 1])
        ax.grid(True)
        ax.legend()
        ax.set_title(self.title)
        if log:
            ax.set_yscale('log')
    
    