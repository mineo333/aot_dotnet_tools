#from .rtr import *
#from .rehydrate import *

from .rehydrate import *
from .rtr import *
from .utils import *
from .method_parser import *
from .nativeformat import *
from .dotnet_enums import *
from .autogen.autogen_nativeformat import *
from .misc import *
from .autogen.autogen_nativeformat_enums import *
import importlib

def doit(bv):
    utils.initialize_utils(bv)
    rtr.initialize_types(bv)
    rtr.populate_sections(bv)
    rehydrate.do_rehydration(bv)
    nativeformat.create_metadata_reader()
    method_parser.parse_methods()


'''
to reload in binja run the following line in the binja console:
import importlib; import aot_dotnet; importlib.reload(aot_dotnet); aot_dotnet.reload_all()

for m in [x for x in sys.modules if 'aot_dotnet' in x]:  
    del sys.modules[m]
del aot_dotnet; import aot_dotnet; aot_dotnet.doit(bv)

'''
def reload_all():
    importlib.reload(rehydrate)
    importlib.reload(rtr)
    importlib.reload(utils)
    importlib.reload(method_parser)
    importlib.reload(nativeformat)
    importlib.reload(dotnet_enums)
    importlib.reload(misc)
    importlib.reload(autogen.autogen_nativeformat_enums)
    importlib.reload(autogen.autogen_nativeformat)