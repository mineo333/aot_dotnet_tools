#from .rtr import *
#from .rehydrate import *

from .rehydrate import *
from .rtr import *

def rehydration(bv):
    rtr.initialize_types(bv)
    rtr.populate_sections(bv)
    rehydrate.do_rehydration(bv)
