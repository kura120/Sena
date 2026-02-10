# src/__init__.py
"""
Sena - Self-Evolving AI Assistant

A sophisticated AI assistant with dynamic memory, intelligent routing,
and extensible capabilities.
"""

import os

# Read version from VERSION file
_version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "VERSION")
try:
    with open(_version_file) as f:
        __version__ = f.read().strip()
except (FileNotFoundError, IOError):
    __version__ = "1.0.0"

__author__ = "kura120"
__license__ = "MIT"