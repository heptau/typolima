# PyInstaller runtime hook: disable multiprocessing resource tracker.
#
# PyInstaller --onefile bundles on macOS cannot properly spawn the
# multiprocessing resource_tracker daemon because the Python shared
# library is not available at the expected path. The daemon fails
# silently and pollutes stderr with:
#   - "resource_tracker: process died unexpectedly, relaunching"
#   - "Failed to load Python shared library"
#
# TypoLima does not use multiprocessing, so we can safely disable the
# resource tracker to suppress these spurious messages.
import multiprocessing
import multiprocessing.resource_tracker as _rt

# Replace the resource tracker's register/unregister methods with no-ops
# so the daemon is never started.
_orig_register = _rt.register
_orig_unregister = _rt.unregister


def _noop_register(*args, **kwargs):
    return None


def _noop_unregister(*args, **kwargs):
    return None


_rt.register = _noop_register
_rt.unregister = _noop_unregister

# Also patch the private _ResourceTracker class so __del__ / ensure_running
# do not start the daemon.
try:
    _rt._ResourceTracker._fd = -1
except (AttributeError, TypeError):
    pass

# Suppress the "process died unexpectedly" UserWarning
import warnings
warnings.filterwarnings(
    "ignore",
    message="resource_tracker: process died unexpectedly",
    category=UserWarning,
    module="multiprocessing.resource_tracker",
)
