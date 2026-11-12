"""
Build Script for compiling iOS Smart Update & Storage Optimizer into a standalone Windows .EXE
Uses PyInstaller with full dependency bundling.
"""

import os
import subprocess
import sys
import shutil

def build():
    print("=" * 60)
    print("Building SmartIOSOptimizer.exe for Windows...")
    print("=" * 60)

    project_root = os.path.abspath(os.path.dirname(__file__))
    os.chdir(project_root)

    entry_point = "main.py"
    icon_path = os.path.join(project_root, "assets", "app_icon.ico")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",                       # Generate onedir first or onefile
        "--windowed",                     # Hide console window
        "--name=SmartIOSOptimizer",
        f"--icon={icon_path}",
        "--collect-all=customtkinter",
        "--hidden-import=requests",
        "--hidden-import=packaging",
        "--hidden-import=packaging.version",
        "--hidden-import=packaging.specifiers",
        "--hidden-import=PIL",
        "--hidden-import=pymobiledevice3",
        entry_point
    ]

    print("Running command:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("Output Directory: dist\\SmartIOSOptimizer\\SmartIOSOptimizer.exe")
        print("=" * 60)
    else:
        print("\nBUILD FAILED with return code:", res.returncode)

if __name__ == "__main__":
    build()
