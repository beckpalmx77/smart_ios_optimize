"""
iOS Device Interface Module.
Handles USB detection, Lockdownd communication, hardware telemetry,
and realistic device simulation for pre-update assessment and testing.
"""

import warnings
warnings.filterwarnings("ignore")

import asyncio
import subprocess
from dataclasses import dataclass, asdict
from typing import Optional

# Try importing pymobiledevice3 modules
try:
    from pymobiledevice3.usbmux import list_devices
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.exceptions import (
        ConnectionFailedToUsbmuxdError,
        NoDeviceConnectedError,
        PyMobileDevice3Exception
    )
    PYMD3_AVAILABLE = True
except ImportError:
    PYMD3_AVAILABLE = False

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

    def to_dict(self):
        return asdict(self)

# Preset mapping for friendly names (Apple Official Hardware Identifiers)
MODEL_MAP = {
    # iPhone 16 series
    "iPhone17,1": "iPhone 16 Pro",
    "iPhone17,2": "iPhone 16 Pro Max",
    "iPhone17,3": "iPhone 16",
    "iPhone17,4": "iPhone 16 Plus",
    # iPhone 15 series
    "iPhone16,1": "iPhone 15 Pro",
    "iPhone16,2": "iPhone 15 Pro Max",
    "iPhone15,4": "iPhone 15",
    "iPhone15,5": "iPhone 15 Plus",
    # iPhone 14 series
    "iPhone15,2": "iPhone 14 Pro",
    "iPhone15,3": "iPhone 14 Pro Max",
    "iPhone14,7": "iPhone 14",
    "iPhone14,8": "iPhone 14 Plus",
    # iPhone 13 series
    "iPhone14,2": "iPhone 13 Pro",
    "iPhone14,3": "iPhone 13 Pro Max",
    "iPhone14,4": "iPhone 13 mini",
    "iPhone14,5": "iPhone 13",
    # iPhone SE
    "iPhone14,6": "iPhone SE (3rd gen)",
    "iPhone12,8": "iPhone SE (2nd gen)",
    # iPhone 12 series
    "iPhone13,1": "iPhone 12 mini",
    "iPhone13,2": "iPhone 12",
    "iPhone13,3": "iPhone 12 Pro",
    "iPhone13,4": "iPhone 12 Pro Max",
    # iPhone 11 series
    "iPhone12,1": "iPhone 11",
    "iPhone12,3": "iPhone 11 Pro",
    "iPhone12,5": "iPhone 11 Pro Max",
    # iPad series
    "iPad16,3": "iPad Pro 11-inch (M4)",
    "iPad16,4": "iPad Pro 11-inch (M4) Cellular",
    "iPad16,5": "iPad Pro 13-inch (M4)",
    "iPad16,6": "iPad Pro 13-inch (M4) Cellular",
    "iPad14,8": "iPad Air 11-inch (M2)",
    "iPad14,9": "iPad Air 11-inch (M2) Cellular",
    "iPad14,10": "iPad Air 13-inch (M2)",
    "iPad14,11": "iPad Air 13-inch (M2) Cellular",
}

# Preset devices for simulation and testing
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

async def _detect_usb_async() -> Optional[DeviceInfo]:
    """Asynchronous worker to query usbmuxd and lockdown."""
    if not PYMD3_AVAILABLE:
        return None

    try:
        devices = await list_devices()
        if not devices:
            return None

        # Take first connected device
        target = devices[0]
        udid = target.serial
        
        # Connect to lockdown (awaiting coroutine in pymobiledevice3 11+)
        lockdown = await create_using_usbmux(serial=udid)
        
        # Read root lockdown values
        all_vals = {}
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

        friendly_model = MODEL_MAP.get(product_type, product_type)
        device_name = f"{friendly_model} ({raw_name})" if raw_name != friendly_model else friendly_model

        # Query Disk Usage
        total_gb = 128.0
        free_gb = 10.0
        try:
            disk_info = await lockdown.get_value(domain="com.apple.disk_usage")
            if disk_info:
                total_bytes = disk_info.get("TotalDiskCapacity", 0)
                free_bytes = disk_info.get("TotalDataAvailable", 0)
                if total_bytes > 0:
                    total_gb = round(total_bytes / (1024**3), 2)
                    free_gb = round(free_bytes / (1024**3), 2)
        except Exception:
            pass
        used_gb = max(0.0, round(total_gb - free_gb, 2))

        # Query Battery & Health
        battery_level = 85
        is_charging = True
        battery_health = 95
        battery_cycle = 180
        battery_temp = 29.5
        try:
            battery_info = await lockdown.get_value(domain="com.apple.mobile.battery")
            if battery_info:
                battery_level = int(battery_info.get("BatteryCurrentCapacity", 85))
                is_charging = bool(battery_info.get("ExternalConnected", True))
                if "CycleCount" in battery_info:
                    battery_cycle = int(battery_info.get("CycleCount", 180))
                if "MaximumCapacityPercent" in battery_info:
                    battery_health = int(battery_info.get("MaximumCapacityPercent", 95))
                elif "NominalChargeCapacity" in battery_info and "DesignCapacity" in battery_info:
                    nom = float(battery_info["NominalChargeCapacity"])
                    des = float(battery_info["DesignCapacity"])
                    if des > 0:
                        battery_health = min(100, max(50, int((nom / des) * 100)))
                if "BatteryTemperature" in battery_info:
                    raw_temp = float(battery_info.get("BatteryTemperature", 295))
                    battery_temp = round(raw_temp / 10.0, 1) if raw_temp > 100 else round(raw_temp, 1)
        except Exception:
            pass

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
            state_details="เชื่อมต่อผ่านสาย USB จริง และอ่านค่าจากเครื่องสำเร็จ",
            battery_health_pct=battery_health,
            battery_cycle_count=battery_cycle,
            battery_temp_c=battery_temp
        )
    except Exception as e:
        return None

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
        battery_temp_c=data.get("battery_temp_c", 29.5)
    )
