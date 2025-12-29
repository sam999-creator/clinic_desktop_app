"""Prepare a local wheelhouse (.wheels) for CI installs.
Downloads wheels from PyPI when .wheels is missing or empty.
This script is simple and cross-platform (works in bash and PowerShell).
"""

import os
import sys
import subprocess

WHEEL_DIR = ".wheels"

if not os.path.exists(WHEEL_DIR) or not any(os.scandir(WHEEL_DIR)):
    print("Preparing wheelhouse in .wheels (this may take a while)")
    subprocess.run([sys.executable, "-m", "pip", "install", "wheel"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "download", "-r", "requirements.txt", "-d", WHEEL_DIR], check=True)
    print("Wheelhouse prepared")
else:
    print("Wheel cache restored; skipping download")
