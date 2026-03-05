import sys
import os

# To ensure imports work when packaged by PyInstaller or run directly
if getattr(sys, 'frozen', False):
    # If running as executable
    sys.path.insert(0, sys._MEIPASS)
else:
    # If running from source
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We import absolute instead of relative to avoid package parent issues
try:
    from typolima.core import main
except ImportError:
    # Fallback to direct import if inside the typolima folder
    from core import main

if __name__ == "__main__":
    main()
