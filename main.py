"""
iOS Smart Update & Storage Optimizer
Windows Desktop Application Entry Point
"""

import sys
import os

# Add root directory to sys.path so modules resolve correctly in both source and PyInstaller
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.ui.app import main

if __name__ == "__main__":
    main()
