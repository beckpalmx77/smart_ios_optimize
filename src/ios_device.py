"""
iOS Device Interface Module.
Handles USB detection, Lockdownd communication, hardware telemetry,
iOS 8+ compatibility profiling, and realistic device simulation for
pre-update assessment and testing.
"""

import warnings
warnings.filterwarnings("ignore")

import asyncio
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple

# Try importing pymobiledevice3 modules
try:
    from pymobiledevice3.usbmux import list_devices
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.afc import AfcService
    from pymobiledevice3.services.diagnostics import DiagnosticsService
    from pymobiledevice3.exceptions import (
        ConnectionFailedToUsbmuxdError,
        NoDeviceConnectedError,
        PyMobileDevice3Exception
    )
    PYMD3_AVAILABLE = True
except ImportError:
    PYMD3_AVAILABLE = False

MIN_SUPPORTED_IOS_MAJOR = 8


def parse_ios_version_tuple(version_str: str) -> Tuple[int, ...]:
    """Parses an iOS version string (e.g. '8.4.1', '17.4.1 (a)') into a numeric tuple."""
    cleaned = re.sub(r"\s*\([^)]*\)", "", str(version_str or "")).strip()
    parts = []
    for token in cleaned.split("."):
        match = re.match(r"(\d+)", token.strip())
        if match:
            parts.append(int(match.group(1)))
    return tuple(parts) if parts else (0,)


def get_ios_major_version(version_str: str) -> int:
    """Returns the major integer iOS version (e.g. 8 for '8.4.1', 17 for '17.4.1 (a)')."""
    return parse_ios_version_tuple(version_str)[0]


def is_ios_8_or_later(version_str: str) -> bool:
    """Returns True if the given version string represents iOS 8.0 or newer."""
    return get_ios_major_version(version_str) >= MIN_SUPPORTED_IOS_MAJOR


# Maximum known iOS major.minor versions for legacy devices that cannot upgrade to latest iOS
LEGACY_MAX_IOS_MAP: Dict[str, str] = {
    "iPhone4,1": "9.3.6",
    "iPhone5,1": "10.3.4",
    "iPhone5,2": "10.3.4",
    "iPhone5,3": "10.3.3",
    "iPhone5,4": "10.3.3",
    "iPhone6,1": "12.5.7",
    "iPhone6,2": "12.5.7",
    "iPhone7,1": "12.5.7",
    "iPhone7,2": "12.5.7",
    "iPhone8,1": "15.8.3",
    "iPhone8,2": "15.8.3",
    "iPhone8,4": "15.8.3",
    "iPhone9,1": "15.8.3",
    "iPhone9,2": "15.8.3",
    "iPhone9,3": "15.8.3",
    "iPhone9,4": "15.8.3",
    "iPhone10,1": "16.7.10",
    "iPhone10,2": "16.7.10",
    "iPhone10,3": "16.7.10",
    "iPhone10,4": "16.7.10",
    "iPhone10,5": "16.7.10",
    "iPhone10,6": "16.7.10",
    "iPad2,1": "9.3.5",
    "iPad2,2": "9.3.6",
    "iPad2,3": "9.3.6",
    "iPad2,4": "9.3.5",
    "iPad2,5": "9.3.5",
    "iPad2,6": "9.3.6",
    "iPad2,7": "9.3.6",
    "iPad3,1": "9.3.5",
    "iPad3,2": "9.3.6",
    "iPad3,3": "9.3.6",
    "iPad3,4": "10.3.3",
    "iPad3,5": "10.3.4",
    "iPad3,6": "10.3.4",
    "iPad4,1": "12.5.7",
    "iPad4,2": "12.5.7",
    "iPad4,3": "12.5.7",
    "iPad4,4": "12.5.7",
    "iPad4,5": "12.5.7",
    "iPad4,6": "12.5.7",
    "iPad4,7": "12.5.7",
    "iPad4,8": "12.5.7",
    "iPad4,9": "12.5.7",
    "iPad5,1": "15.8.3",
    "iPad5,2": "15.8.3",
    "iPad5,3": "15.8.3",
    "iPad5,4": "15.8.3",
    "iPod5,1": "9.3.5",
    "iPod7,1": "12.5.7",
    "iPod9,1": "15.8.3",
}

ARCH_32BIT_MODELS = {
    "iPhone4,1", "iPhone5,1", "iPhone5,2", "iPhone5,3", "iPhone5,4",
    "iPad2,1", "iPad2,2", "iPad2,3", "iPad2,4", "iPad2,5", "iPad2,6", "iPad2,7",
    "iPad3,1", "iPad3,2", "iPad3,3", "iPad3,4", "iPad3,5", "iPad3,6",
    "iPod5,1",
}


def get_ios_compatibility_profile(version_str: str, product_type: str = "") -> Dict[str, Any]:
    """
    Returns architecture, filesystem, service endpoints, and feature compatibility
    flags for any iOS 8+ device.
    """
    ver_tuple = parse_ios_version_tuple(version_str)
    major = ver_tuple[0]
    minor = ver_tuple[1] if len(ver_tuple) > 1 else 0

    supported = major >= MIN_SUPPORTED_IOS_MAJOR
    is_32bit = product_type in ARCH_32BIT_MODELS or major < 11 and product_type.startswith(("iPhone4,", "iPhone5,", "iPad2,", "iPad3,", "iPod5,"))
    arch = "32-bit (ARMv7/ARMv7s)" if is_32bit else "64-bit (ARM64)"

    # APFS was introduced in iOS 10.3
    uses_apfs = (major > 10) or (major == 10 and minor >= 3)
    filesystem = "APFS" if uses_apfs else "HFS+"

    # Diagnostics relay name changed around iOS 9/10
    prefer_legacy_diag = major <= 9
    # Crash log format (.crash/.plist on iOS 8-14, .ips JSON on iOS 15+)
    crash_log_format = ".ips (JSON)" if major >= 15 else ".crash / .plist"

    # Settings & feature availability across iOS eras
    supports_offload_apps = major >= 11
    supports_battery_health_ui = (major > 11) or (major == 11 and minor >= 3)
    supports_optimized_charging = major >= 13
    supports_80_limit = major >= 17 and any(
        product_type.startswith(p) for p in ("iPhone15,4", "iPhone15,5", "iPhone16,", "iPhone17,")
    )
    # Typical OTA overhead is much smaller on iOS 8-12 than iOS 13+
    is_legacy_ota = major <= 12

    if major <= 10:
        era_label = "Legacy Era (iOS 8 - 10)"
    elif major <= 12:
        era_label = "Classic 64-bit Era (iOS 11 - 12)"
    elif major <= 15:
        era_label = "Modern Era (iOS 13 - 15)"
    else:
        era_label = "Latest Era (iOS 16+)"

    return {
        "major": major,
        "minor": minor,
        "supported": supported,
        "arch": arch,
        "is_32bit": is_32bit,
        "filesystem": filesystem,
        "uses_apfs": uses_apfs,
        "prefer_legacy_diag": prefer_legacy_diag,
        "crash_log_format": crash_log_format,
        "supports_offload_apps": supports_offload_apps,
        "supports_battery_health_ui": supports_battery_health_ui,
        "supports_optimized_charging": supports_optimized_charging,
        "supports_80_limit": supports_80_limit,
        "is_legacy_ota": is_legacy_ota,
        "era_label": era_label,
        "max_supported_ios": LEGACY_MAX_IOS_MAP.get(product_type),
    }


@dataclass
class DeviceInfo:
    device_name: str
    product_type: str
    serial_number: str
    udid: str
    current_ios_version: str
    build_version: str
    battery_level: int          # 0 - 100%
    is_charging: bool
    total_disk_gb: float        # Total NAND storage in GB
    free_disk_gb: float         # Free storage in GB
    used_disk_gb: float         # Used storage in GB
    connection_mode: str        # 'LIVE_USB' or 'SIMULATED'
    state_details: str
    battery_health_pct: int = 95
    battery_cycle_count: int = 180
    battery_temp_c: float = 29.5
    battery_voltage_mv: int = 0
    battery_design_mah: int = 0
    battery_current_mah: int = 0

    def to_dict(self):
        return asdict(self)


# Preset mapping for friendly names (Apple Official Hardware Identifiers - iOS 8+ through latest)
MODEL_MAP = {
    # Legacy iOS 8 - 12 iPhones
    "iPhone4,1": "iPhone 4s",
    "iPhone5,1": "iPhone 5 (GSM)",
    "iPhone5,2": "iPhone 5 (Global)",
    "iPhone5,3": "iPhone 5c (GSM)",
    "iPhone5,4": "iPhone 5c (Global)",
    "iPhone6,1": "iPhone 5s (GSM)",
    "iPhone6,2": "iPhone 5s (Global)",
    "iPhone7,1": "iPhone 6 Plus",
    "iPhone7,2": "iPhone 6",
    "iPhone8,1": "iPhone 6s",
    "iPhone8,2": "iPhone 6s Plus",
    "iPhone8,4": "iPhone SE (1st gen)",
    "iPhone9,1": "iPhone 7 (Global)",
    "iPhone9,2": "iPhone 7 Plus (Global)",
    "iPhone9,3": "iPhone 7 (GSM)",
    "iPhone9,4": "iPhone 7 Plus (GSM)",
    "iPhone10,1": "iPhone 8 (Global)",
    "iPhone10,2": "iPhone 8 Plus (Global)",
    "iPhone10,3": "iPhone X (Global)",
    "iPhone10,4": "iPhone 8 (GSM)",
    "iPhone10,5": "iPhone 8 Plus (GSM)",
    "iPhone10,6": "iPhone X (GSM)",
    # iPhone XS / XR series
    "iPhone11,2": "iPhone XS",
    "iPhone11,4": "iPhone XS Max (China)",
    "iPhone11,6": "iPhone XS Max",
    "iPhone11,8": "iPhone XR",
    # iPhone 11 series
    "iPhone12,1": "iPhone 11",
    "iPhone12,3": "iPhone 11 Pro",
    "iPhone12,5": "iPhone 11 Pro Max",
    "iPhone12,8": "iPhone SE (2nd gen)",
    # iPhone 12 series
    "iPhone13,1": "iPhone 12 mini",
    "iPhone13,2": "iPhone 12",
    "iPhone13,3": "iPhone 12 Pro",
    "iPhone13,4": "iPhone 12 Pro Max",
    # iPhone 13 series & SE 3
    "iPhone14,2": "iPhone 13 Pro",
    "iPhone14,3": "iPhone 13 Pro Max",
    "iPhone14,4": "iPhone 13 mini",
    "iPhone14,5": "iPhone 13",
    "iPhone14,6": "iPhone SE (3rd gen)",
    # iPhone 14 series
    "iPhone14,7": "iPhone 14",
    "iPhone14,8": "iPhone 14 Plus",
    "iPhone15,2": "iPhone 14 Pro",
    "iPhone15,3": "iPhone 14 Pro Max",
    # iPhone 15 series
    "iPhone15,4": "iPhone 15",
    "iPhone15,5": "iPhone 15 Plus",
    "iPhone16,1": "iPhone 15 Pro",
    "iPhone16,2": "iPhone 15 Pro Max",
    # iPhone 16 series
    "iPhone17,1": "iPhone 16 Pro",
    "iPhone17,2": "iPhone 16 Pro Max",
    "iPhone17,3": "iPhone 16",
    "iPhone17,4": "iPhone 16 Plus",
    "iPhone17,5": "iPhone 16e",
    # Legacy & Modern iPad series (iOS 8+)
    "iPad2,1": "iPad 2 (Wi-Fi)",
    "iPad2,2": "iPad 2 (GSM)",
    "iPad2,3": "iPad 2 (CDMA)",
    "iPad2,4": "iPad 2 (Rev A)",
    "iPad2,5": "iPad mini (Wi-Fi)",
    "iPad2,6": "iPad mini (GSM)",
    "iPad2,7": "iPad mini (Global)",
    "iPad3,1": "iPad (3rd gen, Wi-Fi)",
    "iPad3,2": "iPad (3rd gen, CDMA)",
    "iPad3,3": "iPad (3rd gen, GSM)",
    "iPad3,4": "iPad (4th gen, Wi-Fi)",
    "iPad3,5": "iPad (4th gen, GSM)",
    "iPad3,6": "iPad (4th gen, Global)",
    "iPad4,1": "iPad Air (Wi-Fi)",
    "iPad4,2": "iPad Air (Cellular)",
    "iPad4,3": "iPad Air (China)",
    "iPad4,4": "iPad mini 2 (Wi-Fi)",
    "iPad4,5": "iPad mini 2 (Cellular)",
    "iPad4,7": "iPad mini 3 (Wi-Fi)",
    "iPad4,8": "iPad mini 3 (Cellular)",
    "iPad5,1": "iPad mini 4 (Wi-Fi)",
    "iPad5,2": "iPad mini 4 (Cellular)",
    "iPad5,3": "iPad Air 2 (Wi-Fi)",
    "iPad5,4": "iPad Air 2 (Cellular)",
    "iPad6,3": "iPad Pro 9.7-inch (Wi-Fi)",
    "iPad6,4": "iPad Pro 9.7-inch (Cellular)",
    "iPad6,7": "iPad Pro 12.9-inch (1st gen, Wi-Fi)",
    "iPad6,8": "iPad Pro 12.9-inch (1st gen, Cellular)",
    "iPad6,11": "iPad (5th gen, Wi-Fi)",
    "iPad6,12": "iPad (5th gen, Cellular)",
    "iPad7,5": "iPad (6th gen, Wi-Fi)",
    "iPad7,6": "iPad (6th gen, Cellular)",
    "iPad7,11": "iPad (7th gen, Wi-Fi)",
    "iPad7,12": "iPad (7th gen, Cellular)",
    "iPad11,3": "iPad Air (3rd gen, Wi-Fi)",
    "iPad11,6": "iPad (8th gen, Wi-Fi)",
    "iPad12,1": "iPad (9th gen, Wi-Fi)",
    "iPad13,18": "iPad (10th gen, Wi-Fi)",
    "iPad14,8": "iPad Air 11-inch (M2)",
    "iPad14,9": "iPad Air 11-inch (M2) Cellular",
    "iPad14,10": "iPad Air 13-inch (M2)",
    "iPad14,11": "iPad Air 13-inch (M2) Cellular",
    "iPad16,3": "iPad Pro 11-inch (M4)",
    "iPad16,4": "iPad Pro 11-inch (M4) Cellular",
    "iPad16,5": "iPad Pro 13-inch (M4)",
    "iPad16,6": "iPad Pro 13-inch (M4) Cellular",
    # iPod touch (iOS 8+)
    "iPod5,1": "iPod touch (5th gen)",
    "iPod7,1": "iPod touch (6th gen)",
    "iPod9,1": "iPod touch (7th gen)",
}

# Preset devices for simulation and testing (spanning iOS 8 through iOS 18+)
SIMULATION_PRESETS = {
    "iPhone 15 Pro (128GB - พื้นที่เหลือน้อย 1.8GB)": {
        "device_name": "iPhone 15 Pro",
        "product_type": "iPhone16,1",
        "serial_number": "DNQXW01K0DN1",
        "udid": "00008130-001234567890001E",
        "current_ios_version": "17.4.1",
        "build_version": "21E236",
        "battery_level": 78,
        "is_charging": True,
        "total_disk_gb": 128.0,
        "free_disk_gb": 1.85,
        "used_disk_gb": 126.15,
        "state_details": "จำลองสถานการณ์: พื้นที่ไม่พอสำหรับ OTA Update (ต้องการการแก้ปัญหา)",
        "battery_health_pct": 94,
        "battery_cycle_count": 218,
        "battery_temp_c": 30.2
    },
    "iPhone 6 (16GB - iOS 8.4.1 รุ่นเก่าพื้นที่จำกัด 0.9GB)": {
        "device_name": "iPhone 6",
        "product_type": "iPhone7,2",
        "serial_number": "FK1N9821G5MN",
        "udid": "4e89ab10c234567890abcdef1234567890abcdef",
        "current_ios_version": "8.4.1",
        "build_version": "12H321",
        "battery_level": 68,
        "is_charging": True,
        "total_disk_gb": 16.0,
        "free_disk_gb": 0.95,
        "used_disk_gb": 15.05,
        "state_details": "จำลองสถานการณ์: อุปกรณ์ iOS 8 (HFS+) พื้นที่ 16GB เหลือน้อย",
        "battery_health_pct": 81,
        "battery_cycle_count": 690,
        "battery_temp_c": 31.0
    },
    "iPhone 6s (32GB - iOS 10.3.3 พร้อมปรับแต่ง)": {
        "device_name": "iPhone 6s",
        "product_type": "iPhone8,1",
        "serial_number": "C39QG123GRYD",
        "udid": "8a12bc34d5678901234567890abcdef123456789",
        "current_ios_version": "10.3.3",
        "build_version": "14G60",
        "battery_level": 82,
        "is_charging": True,
        "total_disk_gb": 32.0,
        "free_disk_gb": 3.40,
        "used_disk_gb": 28.60,
        "state_details": "จำลองสถานการณ์: อุปกรณ์ iOS 10 (APFS รุ่นแรก) พร้อมอัปเดตผ่าน PC",
        "battery_health_pct": 84,
        "battery_cycle_count": 510,
        "battery_temp_c": 29.8
    },
    "iPhone 7 (32GB - iOS 12.4.1 พื้นที่เหลือน้อย)": {
        "device_name": "iPhone 7",
        "product_type": "iPhone9,1",
        "serial_number": "F17SW889HG7F",
        "udid": "7b23cd45e678901234567890abcdef1234567890",
        "current_ios_version": "12.4.1",
        "build_version": "16G102",
        "battery_level": 74,
        "is_charging": False,
        "total_disk_gb": 32.0,
        "free_disk_gb": 1.65,
        "used_disk_gb": 30.35,
        "state_details": "จำลองสถานการณ์: อุปกรณ์ iOS 12 ต้องการเคลียร์แคชก่อนอัปเดต",
        "battery_health_pct": 80,
        "battery_cycle_count": 640,
        "battery_temp_c": 32.1
    },
    "iPhone 14 (128GB - พื้นที่วิกฤต 0.8GB แบตเตอรี่ต่ำ)": {
        "device_name": "iPhone 14",
        "product_type": "iPhone14,7",
        "serial_number": "F2LW9811N70M",
        "udid": "00008110-000987654321002A",
        "current_ios_version": "16.6.1",
        "build_version": "20G81",
        "battery_level": 32,
        "is_charging": False,
        "total_disk_gb": 128.0,
        "free_disk_gb": 0.82,
        "used_disk_gb": 127.18,
        "state_details": "จำลองสถานการณ์: พื้นที่วิกฤตและแบตเตอรี่ไม่เพียงพอ",
        "battery_health_pct": 83,
        "battery_cycle_count": 542,
        "battery_temp_c": 33.4
    },
    "iPhone 13 Pro (256GB - พร้อมอัปเดต 24GB Free)": {
        "device_name": "iPhone 13 Pro",
        "product_type": "iPhone14,2",
        "serial_number": "H7TX9901M22Q",
        "udid": "00008101-000456123789003B",
        "current_ios_version": "17.2",
        "build_version": "21C62",
        "battery_level": 88,
        "is_charging": True,
        "total_disk_gb": 256.0,
        "free_disk_gb": 24.50,
        "used_disk_gb": 231.50,
        "state_details": "จำลองสถานการณ์: อุปกรณ์พร้อมอัปเดตทันที",
        "battery_health_pct": 89,
        "battery_cycle_count": 395,
        "battery_temp_c": 28.5
    },
    "iPhone 11 (64GB - พื้นที่เหลือน้อย 2.4GB)": {
        "device_name": "iPhone 11",
        "product_type": "iPhone12,1",
        "serial_number": "C39ZX80LP0K4",
        "udid": "00008030-001928374650004C",
        "current_ios_version": "16.1",
        "build_version": "20B82",
        "battery_level": 64,
        "is_charging": False,
        "total_disk_gb": 64.0,
        "free_disk_gb": 2.40,
        "used_disk_gb": 61.60,
        "state_details": "จำลองสถานการณ์: iPhone 64GB พื้นที่จำกัด",
        "battery_health_pct": 77,
        "battery_cycle_count": 885,
        "battery_temp_c": 34.1
    },
    "iPhone 16 Pro Max (256GB - เครื่องใหม่ 180GB Free)": {
        "device_name": "iPhone 16 Pro Max",
        "product_type": "iPhone17,2",
        "serial_number": "NP09QWER1234",
        "udid": "00008140-001122334455005D",
        "current_ios_version": "18.0",
        "build_version": "22A3354",
        "battery_level": 95,
        "is_charging": True,
        "total_disk_gb": 256.0,
        "free_disk_gb": 182.0,
        "used_disk_gb": 74.0,
        "state_details": "จำลองสถานการณ์: อุปกรณ์รุ่นใหม่ล่าสุด สมบูรณ์แบบ",
        "battery_health_pct": 100,
        "battery_cycle_count": 22,
        "battery_temp_c": 26.8
    }
}


def _normalize_battery_temp(raw_val: Any) -> float:
    """Normalizes battery temperature reported across iOS 8-18+ (0.01C, 0.1C, or C)."""
    try:
        raw_temp = float(raw_val)
    except (TypeError, ValueError):
        return 29.5
    if raw_temp > 1000:
        return round(raw_temp / 100.0, 1)
    if raw_temp > 100:
        return round(raw_temp / 10.0, 1)
    return round(raw_temp, 1)


async def _query_legacy_or_modern_diagnostics_battery(lockdown, major_ios: int) -> Dict[str, Any]:
    """Queries battery IORegistry telemetry, falling back to iOS 8/9 diagnostics relay if needed."""
    service_names = (
        [DiagnosticsService.OLD_SERVICE_NAME, DiagnosticsService.SERVICE_NAME]
        if major_ios <= 9
        else [DiagnosticsService.SERVICE_NAME, DiagnosticsService.OLD_SERVICE_NAME]
    )
    for svc_name in service_names:
        diag = None
        try:
            diag = DiagnosticsService(lockdown, service_name=svc_name)
            await diag.connect()
            data = await diag.get_battery()
            if isinstance(data, dict) and data:
                return data
        except Exception:
            continue
        finally:
            if diag is not None:
                try:
                    await diag.close()
                except Exception:
                    pass
    return {}


async def _detect_usb_async() -> Optional[DeviceInfo]:
    """Asynchronous worker to query usbmuxd and lockdown across iOS 8 through latest."""
    if not PYMD3_AVAILABLE:
        return None

    lockdown = None
    try:
        devices = await list_devices()
        if not devices:
            return None

        # Prefer USB connection if multiple transports exist
        usb_devices = [d for d in devices if getattr(d, "connection_type", "USB") == "USB"]
        target = usb_devices[0] if usb_devices else devices[0]
        udid = target.serial

        # Connect to lockdown (autopair handles Trust prompt on iOS 8 - 18+)
        lockdown = await create_using_usbmux(serial=udid, pair_timeout=15.0)

        # Read root lockdown values (all_values is populated during initialize, refresh if empty)
        all_vals = dict(getattr(lockdown, "all_values", {}) or {})
        if not all_vals:
            try:
                val = await lockdown.get_value()
                if isinstance(val, dict):
                    all_vals = val
            except Exception:
                pass

        raw_name = all_vals.get("DeviceName") or (await lockdown.get_value(key="DeviceName")) or "iPhone"
        product_type = all_vals.get("ProductType") or (await lockdown.get_value(key="ProductType")) or "iPhone"
        product_version = all_vals.get("ProductVersion") or (await lockdown.get_value(key="ProductVersion")) or "17.0"
        build_version = all_vals.get("BuildVersion") or (await lockdown.get_value(key="BuildVersion")) or "Unknown"
        serial_number = all_vals.get("SerialNumber") or (await lockdown.get_value(key="SerialNumber")) or udid[:12]

        # Handle Supplemental Security Response (e.g. "(a)", "(c)")
        supp_extra = all_vals.get("SupplementalVersionExtra")
        if supp_extra and supp_extra not in str(product_version):
            product_version = f"{product_version} {supp_extra}"

        major_ios = get_ios_major_version(str(product_version))
        friendly_model = MODEL_MAP.get(product_type, product_type)
        device_name = f"{friendly_model} ({raw_name})" if raw_name and raw_name != friendly_model else friendly_model

        # Query Disk Usage (supports both HFS+ on iOS 8-10.2 and APFS on iOS 10.3+)
        total_gb = 0.0
        free_gb = 0.0
        try:
            disk_info = await lockdown.get_value(domain="com.apple.disk_usage")
            if isinstance(disk_info, dict) and disk_info:
                total_bytes = disk_info.get("TotalDiskCapacity") or disk_info.get("TotalDataCapacity") or 0
                free_bytes = disk_info.get("TotalDataAvailable")
                if free_bytes is None:
                    free_bytes = disk_info.get("AmountDataAvailable", 0)
                if total_bytes > 0:
                    total_gb = round(total_bytes / (1024**3), 2)
                    free_gb = round(max(0, free_bytes) / (1024**3), 2)
        except Exception:
            pass

        # Fallback to AFC GET_DEVINFO if com.apple.disk_usage was unavailable (e.g. older iOS states)
        if total_gb <= 0:
            afc = None
            try:
                afc = AfcService(lockdown)
                await afc.connect()
                afc_info = await afc.get_device_info()
                total_bytes = int(afc_info.get("FSTotalBytes", 0))
                free_bytes = int(afc_info.get("FSFreeBytes", 0))
                if total_bytes > 0:
                    total_gb = round(total_bytes / (1024**3), 2)
                    free_gb = round(max(0, free_bytes) / (1024**3), 2)
            except Exception:
                pass
            finally:
                if afc is not None:
                    try:
                        await afc.close()
                    except Exception:
                        pass

        if total_gb <= 0:
            total_gb = 16.0 if major_ios <= 10 else 128.0
            free_gb = 2.0 if major_ios <= 10 else 10.0

        used_gb = max(0.0, round(total_gb - free_gb, 2))

        # Query Battery & Health (Lockdown com.apple.mobile.battery + DiagnosticsService IOPMPowerSource)
        battery_level = 85
        is_charging = True
        battery_health = 95
        battery_cycle = 180
        battery_temp = 29.5
        battery_voltage = 0
        battery_design_mah = 0
        battery_current_mah = 0

        try:
            battery_info = await lockdown.get_value(domain="com.apple.mobile.battery")
            if isinstance(battery_info, dict) and battery_info:
                battery_level = int(battery_info.get("BatteryCurrentCapacity", battery_level))
                is_charging = bool(
                    battery_info.get("ExternalConnected", battery_info.get("BatteryIsCharging", True))
                )
                if "CycleCount" in battery_info:
                    battery_cycle = int(battery_info["CycleCount"])
                if "MaximumCapacityPercent" in battery_info:
                    battery_health = int(battery_info["MaximumCapacityPercent"])
                elif "NominalChargeCapacity" in battery_info and "DesignCapacity" in battery_info:
                    nom = float(battery_info["NominalChargeCapacity"])
                    des = float(battery_info["DesignCapacity"])
                    battery_design_mah = int(des)
                    battery_current_mah = int(nom)
                    if des > 0:
                        battery_health = min(100, max(40, int((nom / des) * 100)))
                if "BatteryTemperature" in battery_info:
                    battery_temp = _normalize_battery_temp(battery_info["BatteryTemperature"])
        except Exception:
            pass

        # On iOS 8-18+, IORegistry IOPMPowerSource has CycleCount, DesignCapacity, Temperature, Voltage
        try:
            ioreg_bat = await _query_legacy_or_modern_diagnostics_battery(lockdown, major_ios)
            if ioreg_bat:
                if "CycleCount" in ioreg_bat:
                    battery_cycle = int(ioreg_bat["CycleCount"])
                if "DesignCapacity" in ioreg_bat:
                    battery_design_mah = int(ioreg_bat["DesignCapacity"])
                raw_max = (
                    ioreg_bat.get("NominalChargeCapacity")
                    or ioreg_bat.get("AppleRawMaxCapacity")
                    or ioreg_bat.get("MaxCapacity")
                )
                if raw_max is not None and battery_design_mah > 0:
                    nom_val = float(raw_max)
                    # On some older iOS devices MaxCapacity is reported in % (<= 100) rather than mAh
                    if nom_val <= 100 and battery_design_mah > 500:
                        battery_health = min(100, max(40, int(nom_val)))
                        battery_current_mah = int(battery_design_mah * (battery_health / 100.0))
                    else:
                        battery_current_mah = int(nom_val)
                        battery_health = min(100, max(40, int((nom_val / battery_design_mah) * 100)))
                if "Temperature" in ioreg_bat:
                    battery_temp = _normalize_battery_temp(ioreg_bat["Temperature"])
                if "Voltage" in ioreg_bat:
                    battery_voltage = int(ioreg_bat["Voltage"])
        except Exception:
            pass

        profile = get_ios_compatibility_profile(str(product_version), product_type)
        compat_note = (
            f"เชื่อมต่อ USB สำเร็จ ({profile['era_label']} | {profile['filesystem']} | {profile['arch']})"
        )

        return DeviceInfo(
            device_name=device_name,
            product_type=product_type,
            serial_number=serial_number,
            udid=udid,
            current_ios_version=str(product_version),
            build_version=str(build_version),
            battery_level=battery_level,
            is_charging=is_charging,
            total_disk_gb=total_gb,
            free_disk_gb=free_gb,
            used_disk_gb=used_gb,
            connection_mode="LIVE_USB",
            state_details=compat_note,
            battery_health_pct=battery_health,
            battery_cycle_count=battery_cycle,
            battery_temp_c=battery_temp,
            battery_voltage_mv=battery_voltage,
            battery_design_mah=battery_design_mah,
            battery_current_mah=battery_current_mah,
        )
    except Exception:
        return None
    finally:
        if lockdown is not None:
            try:
                await lockdown.close()
            except Exception:
                pass


def detect_real_usb_device() -> Optional[DeviceInfo]:
    """Synchronous entry point to detect real USB connected device."""
    try:
        return asyncio.run(_detect_usb_async())
    except Exception:
        return None


def get_simulated_device(preset_key: str, override_free_gb=None, override_battery=None) -> DeviceInfo:
    """Returns a DeviceInfo instance configured from simulation presets."""
    if preset_key not in SIMULATION_PRESETS:
        preset_key = list(SIMULATION_PRESETS.keys())[0]

    data = dict(SIMULATION_PRESETS[preset_key])

    if override_free_gb is not None:
        try:
            data["free_disk_gb"] = float(override_free_gb)
            data["used_disk_gb"] = max(0.0, round(data["total_disk_gb"] - data["free_disk_gb"], 2))
        except ValueError:
            pass

    if override_battery is not None:
        try:
            data["battery_level"] = int(override_battery)
        except ValueError:
            pass

    return DeviceInfo(
        device_name=data["device_name"],
        product_type=data["product_type"],
        serial_number=data["serial_number"],
        udid=data["udid"],
        current_ios_version=data["current_ios_version"],
        build_version=data["build_version"],
        battery_level=data["battery_level"],
        is_charging=data["is_charging"],
        total_disk_gb=data["total_disk_gb"],
        free_disk_gb=data["free_disk_gb"],
        used_disk_gb=data["used_disk_gb"],
        connection_mode="SIMULATED",
        state_details=data["state_details"],
        battery_health_pct=data.get("battery_health_pct", 95),
        battery_cycle_count=data.get("battery_cycle_count", 180),
        battery_temp_c=data.get("battery_temp_c", 29.5),
        battery_voltage_mv=data.get("battery_voltage_mv", 0),
        battery_design_mah=data.get("battery_design_mah", 0),
        battery_current_mah=data.get("battery_current_mah", 0),
    )
