
# Testovi nikad ne smiju pisati statistiku na pravi GitHub (tools/vlastita.py), ni slučajno (4.10.2026).
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "tools"))
try:
    import vlastita as _vlastita

    def _no_real_gh(*args, **kwargs):
        raise RuntimeError("test je pokušao pravi gh za statistiku")

    _vlastita._gh = _no_real_gh
    _vlastita.record.__defaults__ = (_no_real_gh,)
except ImportError:
    pass
