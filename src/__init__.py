"""
iOS Smart Update & Storage Optimizer Package.
"""

from .storage_fixer import (
    StorageFixer,
    IOSOptimizer,
    tune_ios_speed,
    assess_device_speed_state,
    get_speed_tuning_recommendations
)
from .ios_device import DeviceInfo, detect_real_usb_device, get_simulated_device

__all__ = [
    "StorageFixer",
    "IOSOptimizer",
    "tune_ios_speed",
    "assess_device_speed_state",
    "get_speed_tuning_recommendations",
    "DeviceInfo",
    "detect_real_usb_device",
    "get_simulated_device"
]
