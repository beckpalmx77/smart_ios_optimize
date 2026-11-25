"""
Apple IPSW and Firmware Service.
Queries Apple's official signed firmware availability via IPSW API and Apple TSS.
"""

import warnings
warnings.filterwarnings("ignore")

import requests
from packaging import version as pkg_version

# Pre-defined list of common devices for immediate offline / quick UI selection (Apple Official Hardware Identifiers)
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
    {"name": "iPad Pro 13-inch (M4)", "identifier": "iPad16,5"},
    {"name": "iPad Pro 11-inch (M4)", "identifier": "iPad16,3"},
    {"name": "iPad Air 13-inch (M2)", "identifier": "iPad14,10"},
    {"name": "iPad Air 11-inch (M2)", "identifier": "iPad14,8"},
]

_FIRMWARE_CACHE = {}

def get_popular_devices():
    """Returns list of commonly used iOS devices."""
    return POPULAR_DEVICES

def fetch_firmware_info(identifier: str):
    """
    Fetches firmware list for an iOS device identifier (e.g. 'iPhone15,2').
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
                return pkg_version.parse(str(fw.get("version", "0")))
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
    Compares current iOS version against target version.
    Returns:
        'UPDATE_AVAILABLE': target is newer
        'UP_TO_DATE': current is same or newer
        'DOWNGRADE': current is newer than target
    """
    try:
        c_ver = pkg_version.parse(str(current_ver).strip())
        t_ver = pkg_version.parse(str(target_ver).strip())
        if t_ver > c_ver:
            return "UPDATE_AVAILABLE"
        elif t_ver == c_ver:
            return "UP_TO_DATE"
        else:
            return "DOWNGRADE"
    except Exception:
        if str(target_ver).strip() != str(current_ver).strip():
            return "UPDATE_AVAILABLE"
        return "UP_TO_DATE"
