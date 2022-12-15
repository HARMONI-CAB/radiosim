import pathlib
from .InterpolatedSpectrum import InterpolatedSpectrum
from .InterpolatedResponse import InterpolatedResponse
from .BlackBodySpectrum    import BlackBodySpectrum
from .CompoundResponse     import CompoundResponse

RADIOSIM_RELATIVE_DATA_DIR = '../data'
HARMONI_FINEST_SPAXEL_SIZE = 4.14    # mas
HARMONI_PIXEL_SIZE         = 13.3e-6 # m
HARMONI_PX_PER_SP_ALONG    = 1       # From: HRM-00190
HARMONI_PX_PER_SP_ACROSS   = 2       # From: HRM-00190
HARMONI_PX_AREA            = HARMONI_PIXEL_SIZE * HARMONI_PIXEL_SIZE

class Parameters():
    def __init__(self):
        self.stages     = {}
        self.lamps      = {}
        self.filters    = {}
        self.equalizers = {}
        self.gratings   = {}
        self.scales     = {}

        self.finest_spaxel_size_mas = HARMONI_FINEST_SPAXEL_SIZE
        self.pixel_size             = HARMONI_PIXEL_SIZE

        self.load_stage('Cryostat',      't-cryostat.csv')
        self.load_stage('Detector',      't-detector.csv')
        self.load_stage('FPRS',          't-fprs.csv')
        self.load_stage('LTAO Dichroic', 't-ltao-d.csv')
        self.load_stage('SCAO Dichroic', 't-scao-d.csv')
        self.load_stage('Misalignments', 't-misalignment.csv')
        self.load_stage('Preoptics',     't-preoptics.csv')
        self.load_stage('Spectrograph',  't-spectrograph.csv')
        self.load_stage('IFU',           't-ifu.csv')


    def resolve_data_file(self, path):
        if len(path) == 0:
            raise RuntimeError('Path is empty')
        
        if path[0] == '/' or path[0] == '.':
            return path

        dir = str(pathlib.Path(__file__).parent.resolve())

        return dir + fr'/{RADIOSIM_RELATIVE_DATA_DIR}/' + path
    
    def load_lamp(self, name, path, rating = None):
        full_path = self.resolve_data_file(path)
        spectrum = InterpolatedSpectrum(full_path)

        if rating is not None:
            spectrum.set_nominal_power_rating(rating)
        self.lamps[name] = spectrum

    def load_black_body_lamp(self, name, T, rating):
        spectrum = BlackBodySpectrum(T)

        if rating is not None:
            spectrum.set_nominal_power_rating(rating)
        
        self.lamps[name] = spectrum

    def get_lamp(self, name):
        if name not in self.lamps:
            return None

        return self.lamps[name]
    
    def get_lamp_names(self):
        return list(self.lamps.keys())
    
    def load_stage(self, name, path):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path)
        self.stages[name] = response

    def get_stage(self, name):
        if name not in self.stages:
            raise RuntimeError('No such stage filter')
        
        return self.stages[name]
    
    def get_stage_names(self):
        return list(self.stages.keys())
    
    def load_filter(self, name, path):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path)
        self.filters[name] = response

    def get_filter(self, name):
        if name not in self.filters:
            return None
        return self.filters[name]
    
    def get_filter_names(self):
        return list(self.filters.keys())
    
    def load_equalizer(self, name, path):
        full_path = self.resolve_data_file(path)
        response = InterpolatedResponse(full_path)
        self.equalizers[name] = response
        return self.equalizers[name]
    
    def get_equalizer(self, name):
        if name not in self.equalizers:
            return None
        return self.equalizers[name]
    
    def get_equalizer_names(self):
        return list(self.equalizers.keys())
    
    def register_grating(self, grating, filter, equalizer, R, lambda_min, lambda_max):
        filter_obj = self.get_filter(filter)
        if filter_obj is None:
            raise RuntimeError(fr'No such passband filter: {filter}')
        
        eq_obj = self.get_equalizer(equalizer)
        if eq_obj is None:
            raise RuntimeError(fr'No such equalizer filter: {equalizer}')

        self.gratings[grating] = (filter_obj, eq_obj, R, lambda_min, lambda_max)
    
    def get_grating(self, name):
        if name not in self.gratings:
            return None

        return self.gratings[name]

    def get_grating_names(self):
        return list(self.gratings.keys())
    
    def register_scale(self, scale, spaxel_x, spaxel_y):
        if type(scale) is not tuple or len(scale) != 2:
            raise RuntimeError(fr'Scales must be defined as 2-tuples')
        
        self.scales[scale] = (spaxel_x, spaxel_y)

    def get_scale(self, scale):
        if scale not in self.scales:
            return None
        return self.scales[scale]
    
    def get_scales(self):
        return self.scales.keys()

    def make_response(self, grating, ao):
        response = CompoundResponse()
        ao       = ao.upper()
        grating  = grating.upper()

        if ao == "SCAO":
            response.push_back(self.get_stage("SCAO Dichroic"))
        elif ao == "LTAO":
            response.push_back(self.get_stage("LTAO Dichroic"))
        elif ao != "NOAO":
            raise Exception("Undefined AO configuration " + ao)
        
        response.push_back(self.get_stage("FPRS"))
        response.push_back(self.get_stage("Cryostat"))
        response.push_back(self.get_stage("Preoptics"))
        response.push_back(self.get_stage("IFU"))
        response.push_back(self.get_stage("Spectrograph"))

        gr_obj = self.get_grating(grating)
        if gr_obj is None:
            raise Exception(fr'Undefined grating: {grating}')
        
        # Push passband filter
        response.push_back(gr_obj[0])

        # Push equalizer
        response.push_back(gr_obj[1])

        response.push_back(self.get_stage("Misalignments"))
        response.push_back(self.get_stage("Detector"))

        return response

    def load_defaults(self):
        # Load lamps
        self.load_lamp("150W",        "lamp-spectrum.csv", 2 * 150)
        self.load_lamp("NORMAL",      "lamp-spectrum-2.csv")

        # Load passband filters for the different gratings
        self.load_filter("H (high)",  "t-h-high.csv")
        self.load_filter("H",         "t-h.csv")
        self.load_filter("HK",        "t-hk.csv")
        self.load_filter("IZ",        "t-iz.csv")
        self.load_filter("IZJ",       "t-izj.csv")
        self.load_filter("J",         "t-j.csv")
        self.load_filter("K",         "t-k.csv")
        self.load_filter("K (long)",  "t-k-long.csv")
        self.load_filter("K (short)", "t-k-short.csv")
        self.load_filter("VIS",       "t-vis.csv")
        self.load_filter("Z",         "t-z.csv")

        # Load equalizers
        self.load_equalizer("VIS",    "f-vis.csv")
        self.load_equalizer("LR1",    "f-lr1.csv")
        self.load_equalizer("LR2",    "f-lr2.csv")
        self.load_equalizer("MR1",    "f-mr1.csv")
        self.load_equalizer("MR2",    "f-mr2.csv")
        self.load_equalizer("MR3",    "f-mr3.csv")
        self.load_equalizer("MR4",    "f-mr4.csv")
        self.load_equalizer("HR1",    "f-hr1.csv")
        self.load_equalizer("HR2",    "f-hr2.csv")
        self.load_equalizer("HR3",    "f-hr3.csv")
        self.load_equalizer("HR4",    "f-hr4.csv")
        
        # Register available gratings
        self.register_grating("VIS", "VIS", "VIS", 3000, 0.462e-6, 0.812e-6)
        
        self.register_grating("LR1", "IZJ", "LR1", 3327, 0.811e-6, 1.369e-6)
        self.register_grating("LR2", "HK",  "LR2", 3327, 1.450e-6, 2.450e-6)
        
        self.register_grating("MR1", "IZ",  "MR1", 7050, 0.830e-6, 1.050e-6)
        self.register_grating("MR2", "J",   "MR2", 7050, 1.046e-6, 1.324e-6)
        self.register_grating("MR3", "H" ,  "MR3", 7050, 1.435e-6, 1.815e-6)
        self.register_grating("MR4", "K" ,  "MR4", 7050, 1.951e-6, 2.469e-6)
        
        self.register_grating("HR1", "Z",         "HR1", 18000, 0.827e-6, 0.903e-6)
        self.register_grating("HR2", "H (high)",  "HR2", 18000, 1.538e-6, 1.678e-6)
        self.register_grating("HR3", "K (short)", "HR3", 18000, 2.017e-6, 2.201e-6)
        self.register_grating("HR4", "K (long)",  "HR4", 18000, 2.199e-6, 2.399e-6)

        # Register scales
        self.register_scale((4, 4), HARMONI_FINEST_SPAXEL_SIZE, HARMONI_FINEST_SPAXEL_SIZE)
        self.register_scale((10, 10), 10, 10)
        self.register_scale((20, 20), 20, 20)
        self.register_scale((60, 30), 60, 30)
