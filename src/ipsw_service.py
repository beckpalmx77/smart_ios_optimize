"""
Apple IPSW and Firmware Service.
Queries Apple's official signed firmware availability via IPSW API and Apple TSS.
Supports all iOS 8+ compatible devices (iPhone 4s through latest, iPad, iPod touch).
"""

import warnings
warnings.filterwarnings("ignore")

import re
import requests
from packaging import version as pkg_version

# Pre-defined list of common devices for immediate offline / quick UI selection (iOS 8+ through latest)
POPULAR_DEVICES = [
    {"name": "iPhone 16 Pro Max", "identifier": "iPhone17,2"},
    {"name": "iPhone 16 Pro", "identifier": "iPhone17,1"},
    {"name": "iPhone 16 Plus", "identifier": "iPhone17,4"},
    {"name": "iPhone 16", "identifier": "iPhone17,3"},
    {"name": "iPhone 15 Pro Max", "identifier": "iPhone16,2"},
    {"name": "iPhone 15 Pro", "identifier": "iPhone16,1"},
    {"name": "iPhone 15 Plus", "identifier": "iPhone15,5"},
    {"name": "iPhone 15", "identifier": "iPhone15,4"},
    {"name": "iPhone 14 Pro Max", "identifier": "iPhone15,3"},
    {"name": "iPhone 14 Pro", "identifier": "iPhone15,2"},
    {"name": "iPhone 14 Plus", "identifier": "iPhone14,8"},
    {"name": "iPhone 14", "identifier": "iPhone14,7"},
    {"name": "iPhone 13 Pro Max", "identifier": "iPhone14,3"},
    {"name": "iPhone 13 Pro", "identifier": "iPhone14,2"},
    {"name": "iPhone 13", "identifier": "iPhone14,5"},
    {"name": "iPhone 13 mini", "identifier": "iPhone14,4"},
    {"name": "iPhone SE (3rd gen)", "identifier": "iPhone14,6"},
    {"name": "iPhone 12 Pro Max", "identifier": "iPhone13,4"},
    {"name": "iPhone 12 Pro", "identifier": "iPhone13,3"},
    {"name": "iPhone 12", "identifier": "iPhone13,2"},
    {"name": "iPhone 12 mini", "identifier": "iPhone13,1"},
    {"name": "iPhone 11 Pro Max", "identifier": "iPhone12,5"},
    {"name": "iPhone 11 Pro", "identifier": "iPhone12,3"},
    {"name": "iPhone 11", "identifier": "iPhone12,1"},
    {"name": "iPhone XS Max", "identifier": "iPhone11,6"},
    {"name": "iPhone XS", "identifier": "iPhone11,2"},
    {"name": "iPhone XR", "identifier": "iPhone11,8"},
    {"name": "iPhone X", "identifier": "iPhone10,6"},
    {"name": "iPhone 8 Plus", "identifier": "iPhone10,5"},
    {"name": "iPhone 8", "identifier": "iPhone10,4"},
    {"name": "iPhone 7 Plus", "identifier": "iPhone9,2"},
    {"name": "iPhone 7", "identifier": "iPhone9,1"},
    {"name": "iPhone SE (1st gen)", "identifier": "iPhone8,4"},
    {"name": "iPhone 6s Plus", "identifier": "iPhone8,2"},
    {"name": "iPhone 6s", "identifier": "iPhone8,1"},
    {"name": "iPhone 6 Plus", "identifier": "iPhone7,1"},
    {"name": "iPhone 6", "identifier": "iPhone7,2"},
    {"name": "iPhone 5s", "identifier": "iPhone6,1"},
    {"name": "iPhone 5c", "identifier": "iPhone5,3"},
    {"name": "iPhone 5", "identifier": "iPhone5,1"},
    {"name": "iPhone 4s", "identifier": "iPhone4,1"},
    {"name": "iPad Pro 13-inch (M4)", "identifier": "iPad16,5"},
    {"name": "iPad Pro 11-inch (M4)", "identifier": "iPad16,3"},
    {"name": "iPad Air 13-inch (M2)", "identifier": "iPad14,10"},
    {"name": "iPad Air 11-inch (M2)", "identifier": "iPad14,8"},
    {"name": "iPad Air 2", "identifier": "iPad5,3"},
    {"name": "iPad mini 4", "identifier": "iPad5,1"},
]

_FIRMWARE_CACHE = {}


def _clean_version_str(ver: str) -> str:
    """Strips Rapid Security Response suffixes like '(a)' before version parsing."""
    cleaned = re.sub(r"\s*\([^)]*\)", "", str(ver or "")).strip()
    return cleaned or "0"


def get_popular_devices():
    """Returns list of commonly used iOS devices (iOS 8+ compatible)."""
    return POPULAR_DEVICES


def fetch_firmware_info(identifier: str):
    """
    Fetches firmware list for an iOS device identifier (e.g. 'iPhone7,2', 'iPhone15,2').
    Returns:
        dict: {
            "device_name": str,
            "identifier": str,
            "latest_signed": dict or None,
            "all_signed": list of dict,
            "raw_firmwares": list
        }
    """
    if identifier in _FIRMWARE_CACHE:
        return _FIRMWARE_CACHE[identifier]

    url = f"https://api.ipsw.me/v4/device/{identifier}"
    try:
        resp = requests.get(url, timeout=12)
        resp.raise_for_status()
        data = resp.json()

        firmwares = data.get("firmwares", [])
        signed_firmwares = [f for f in firmwares if f.get("signed", False)]

        # Sort signed firmwares by version descending to get true latest release
        def _sort_ver(fw):
            try:
                return pkg_version.parse(_clean_version_str(fw.get("version", "0")))
            except Exception:
                return pkg_version.parse("0")

        signed_firmwares.sort(key=_sort_ver, reverse=True)
        latest_signed = signed_firmwares[0] if signed_firmwares else None

        result = {
            "device_name": data.get("name", identifier),
            "identifier": identifier,
            "latest_signed": latest_signed,
            "all_signed": signed_firmwares,
            "raw_firmwares": firmwares
        }
        _FIRMWARE_CACHE[identifier] = result
        return result
    except Exception as e:
        # Fallback in case of no internet or network error
        return {
            "device_name": identifier,
            "identifier": identifier,
            "latest_signed": None,
            "all_signed": [],
            "error": str(e)
        }


def compare_versions(current_ver: str, target_ver: str) -> str:
    """
    Compares current iOS version against target version (supports iOS 8.0 through latest,
    including Rapid Security Response tags like '17.4.1 (a)').
    Returns:
        'UPDATE_AVAILABLE': target is newer
        'UP_TO_DATE': current is same or newer
        'DOWNGRADE': current is newer than target
    """
    c_clean = _clean_version_str(current_ver)
    t_clean = _clean_version_str(target_ver)
    try:
        c_ver = pkg_version.parse(c_clean)
        t_ver = pkg_version.parse(t_clean)
        if t_ver > c_ver:
            return "UPDATE_AVAILABLE"
        elif t_ver == c_ver:
            return "UP_TO_DATE"
        else:
            return "DOWNGRADE"
    except Exception:
        if t_clean != c_clean:
            return "UPDATE_AVAILABLE"
        return "UP_TO_DATE"
