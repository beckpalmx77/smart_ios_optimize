"""
Driver Manager for Apple Mobile Device Support and usbmuxd on Windows.
Checks presence of Apple drivers (iTunes / Apple Devices / AMDS), usbmuxd service,
and offers official Apple MSI download for iOS 8+ devices.
"""

import os
import subprocess
import winreg
import requests

APPLE_AMDS_URL = "https://swcdn.apple.com/content/downloads/20/49/047-76422/qcw2a7028lr8yp4rdkrfyzkvlhi9q1gg2g/AppleMobileDeviceSupport64.msi"


def check_apple_drivers_installed():
    """
    Checks if Apple Mobile Device Support (or Apple Devices / iTunes) is installed
    and if its usbmuxd service is active for iOS 8+ USB detection.
    """
    installed = False
    version = None
    service_running = False
    driver_path = None

    # 1. Check Registry for Apple Mobile Device Support
    reg_paths = [
        r"SOFTWARE\Apple Inc.\Apple Mobile Device Support",
        r"SOFTWARE\WOW6432Node\Apple Inc.\Apple Mobile Device Support",
    ]
    for reg_path in reg_paths:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                installed = True
                try:
                    version, _ = winreg.QueryValueEx(key, "Version")
                except FileNotFoundError:
                    version = "Detected (Registry)"
                try:
                    driver_path, _ = winreg.QueryValueEx(key, "InstallDir")
                except FileNotFoundError:
                    pass
                break
        except FileNotFoundError:
            continue
        except Exception:
            pass

    # 2. Check standard Program Files folder & Windows driver store
    common_paths = [
        r"C:\Program Files\Common Files\Apple\Mobile Device Support\AppleMobileDeviceService.exe",
        r"C:\Program Files (x86)\Common Files\Apple\Mobile Device Support\AppleMobileDeviceService.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            installed = True
            driver_path = os.path.dirname(p)
            break

    # 3. Check Windows Service status (classic AMDS or Apple Devices UWP usbmuxd)
    for svc_name in ("Apple Mobile Device Service", "usbmuxd"):
        try:
            res = subprocess.run(
                ["sc", "query", svc_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if "RUNNING" in res.stdout:
                installed = True
                service_running = True
                if not driver_path:
                    driver_path = f"Windows Service: {svc_name}"
                break
        except Exception:
            pass

    if installed and service_running:
        details = "ติดตั้งเรียบร้อยและ Service ทำงานปกติ (พร้อมเชื่อมต่อ iOS 8 ขึ้นไป)"
    elif installed and not service_running:
        details = "ติดตั้งไดรเวอร์แล้ว แต่ Apple Mobile Device Service ยังไม่เริ่มทำงาน"
    else:
        details = "ยังไม่ได้ติดตั้ง Apple Mobile Device Support บนคอมพิวเตอร์เครื่องนี้"

    return {
        "installed": installed,
        "version": version or ("Installed" if installed else "None"),
        "service_running": service_running,
        "path": driver_path,
        "details": details
    }


def start_apple_service():
    """Attempts to start Apple Mobile Device Service."""
    try:
        subprocess.run(["sc", "start", "Apple Mobile Device Service"], capture_output=True, text=True, check=False)
        return True
    except Exception:
        return False


def download_apple_driver_msi(target_folder="downloads", progress_callback=None):
    """
    Downloads AppleMobileDeviceSupport64.msi directly from Apple CDN.
    """
    os.makedirs(target_folder, exist_ok=True)
    destination = os.path.abspath(os.path.join(target_folder, "AppleMobileDeviceSupport64.msi"))

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    with requests.get(APPLE_AMDS_URL, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        total_size = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(destination, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        percent = (downloaded / total_size) * 100
                        progress_callback(downloaded, total_size, percent)

    return destination
