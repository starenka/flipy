from settings.base import *

try:
    from settings.local import *
except ImportError:
    pass
    
