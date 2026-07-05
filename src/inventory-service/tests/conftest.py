"""Configure Python path so tests can import from inventory-service."""

import sys
from pathlib import Path

# Add the parent service directory to sys.path so that
# `from main import app` works during test collection.
SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))
