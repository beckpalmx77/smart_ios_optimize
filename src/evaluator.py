"""
Pre-Update Evaluation and Risk Assessment Module.
Evaluates device readiness before iOS update: storage constraints, battery levels,
firmware signing integrity, and host PC disk requirements.
"""

import os
import shutil
from typing import Dict, Any
from .ios_device import DeviceInfo

class PreUpdateEvaluator:
    """Evaluates readiness of an iOS device for firmware update."""

    OTA_MIN_REQUIRED_GB = 12.0      # Typical free space needed on iPhone for OTA download + decompress
    PC_RESTORE_MIN_GB = 2.0         # Space needed on iPhone when updating via USB tethered PC
    PC_HOST_MIN_GB = 15.0           # Space needed on Windows PC to download & unpack IPSW

    def __init__(self, device: DeviceInfo, target_firmware: Dict[str, Any] = None):
        self.device = device
        self.target_firmware = target_firmware or {}

    def evaluate(self) -> Dict[str, Any]:
        """
        Runs comprehensive 6-point pre-update diagnostic.
        Returns detailed report and numerical readiness score (0-100).
        """
        checks = {}
        score = 100
        critical_flags = []
        action_recommendations = []

        # -------------------------------------------------------------
        # 1. Storage Analysis (On Device)
        # -------------------------------------------------------------
        free_gb = self.device.free_disk_gb
        total_gb = self.device.total_disk_gb
        free_percent = round((free_gb / total_gb) * 100, 1) if total_gb > 0 else 0

        firmware_size_gb = round(self.target_firmware.get("filesize", 8 * 1024**3) / (1024**3), 2)
        estimated_ota_needed = round(firmware_size_gb + 4.0, 1)

        if free_gb >= estimated_ota_needed:
            storage_status = "EXCELLENT"
            storage_msg = f"พื้นที่ว่าง {free_gb:.2f} GB ({free_percent}%) เพียงพอสำหรับการอัปเดตทุกรูปแบบ ทั้ง OTA และ ผ่านคอมพิวเตอร์"
            storage_badge = "ผ่านเกณฑ์ดีเยี่ยม"
        elif free_gb >= self.PC_RESTORE_MIN_GB:
            storage_status = "OTA_BLOCKED_PC_READY"
            score -= 15
            storage_msg = (
                f"พื้นที่ว่างบน iPhone มีเพียง {free_gb:.2f} GB "
                f"(อัปเดตผ่านเมนู Settings ในเครื่องจะไม่ผ่าน เพราะต้องใช้ ~{estimated_ota_needed} GB) "
                f"แต่วิธี 'อัปเดตผ่าน PC' สามารถทำได้ทันที เนื่องจากไฟล์ IPSW จะแตกบนคอมพิวเตอร์!"
            )
            storage_badge = "OTA ไม่พอ แต่ PC อัปเดตได้"
            action_recommendations.append("ใช้วิธี 'Update ผ่าน PC' ในโปรแกรมนี้ โดยไม่ต้องลบรูปภาพหรือข้อมูลส่วนตัว")
        else:
            storage_status = "CRITICAL_LOW"
            score -= 45
            critical_flags.append("พื้นที่บนเครื่อง iPhone เหลือน้อยกว่า 2 GB")
            storage_msg = (
                f"พื้นที่ว่างวิกฤต ({free_gb:.2f} GB) อาจทำให้ระบบบันทึก Log ไฟล์ไม่พอขณะแฟลช "
                f"จำเป็นต้องเปิดระบบ 'เคลียร์ขยะ & เคลียร์แคช' ก่อนจึงจะเริ่มอัปเดตได้"
            )
            storage_badge = "พื้นที่วิกฤต ต้องเคลียร์ก่อน"
            action_recommendations.append("กดแท็บ 'เคลียร์ขยะ & ปรับแต่ง iOS' เพื่อล้าง Crash logs, แคชระบบ, ปล่อยคืน RAM หรือ Offload Apps")

        checks["storage"] = {
            "status": storage_status,
            "badge": storage_badge,
            "message": storage_msg,
            "free_gb": free_gb,
            "total_gb": total_gb,
            "ota_needed_gb": estimated_ota_needed,
            "pc_needed_gb": self.PC_RESTORE_MIN_GB,
            "passed": storage_status != "CRITICAL_LOW"
        }

        # -------------------------------------------------------------
        # 2. Battery & Power Analysis
        # -------------------------------------------------------------
        batt = self.device.battery_level
        is_charging = self.device.is_charging

        if batt >= 50 or (batt >= 35 and is_charging):
            batt_status = "PASS"
            batt_msg = f"แบตเตอรี่ {batt}% ({'กำลังชาร์จ' if is_charging else 'ไม่เสียบชาร์จ'}) ปลอดภัยสำหรับกระบวนการอัปเดต"
            batt_badge = "พร้อม"
        elif batt >= 25:
            batt_status = "WARNING"
            score -= 20
            batt_msg = f"แบตเตอรี่ {batt}% ค่อนข้างต่ำ แนะนำให้เสียบชาร์จให้เกิน 50% เพื่อป้องกันเครื่องดับกะทันหันขณะแฟลช"
            batt_badge = "ควรชาร์จเพิ่ม"
            action_recommendations.append("เสียบสายชาร์จกับคอมพิวเตอร์หรืออแดปเตอร์ให้แบตเตอรี่เกิน 50%")
        else:
            batt_status = "FAIL"
            score -= 40
            critical_flags.append(f"แบตเตอรี่วิกฤต ({batt}%) ห้ามอัปเดตเด็ดขาด")
            batt_msg = f"แบตเตอรี่ต่ำเกินไป ({batt}%) เสี่ยงเครื่องติด Recovery Mode หรือ DFU loop หากไฟดับระหว่างเขียน NAND"
            batt_badge = "อันตราย"
            action_recommendations.append("ชาร์จแบตเตอรี่ iPhone อย่างน้อย 50% ก่อนเริ่มขั้นตอนแฟลช")

        checks["battery"] = {
            "status": batt_status,
            "badge": batt_badge,
            "message": batt_msg,
            "level": batt,
            "is_charging": is_charging,
            "passed": batt_status == "PASS"
        }

        # -------------------------------------------------------------
        # 3. Firmware Signature Check (Apple TSS)
        # -------------------------------------------------------------
        is_signed = self.target_firmware.get("signed", True)
        target_version = self.target_firmware.get("version", "Latest")
        
        if is_signed:
            fw_status = "PASS"
            fw_msg = f"iOS {target_version} กำลังเปิด Signing โดย Apple Server (สามารถแฟลชผ่านได้ 100%)"
            fw_badge = "Signed โดย Apple"
        else:
            fw_status = "FAIL"
            score = 0
            critical_flags.append("เฟิร์มแวร์นี้ปิดการ Signed แล้ว ไม่สามารถติดตั้งได้")
            fw_msg = f"iOS {target_version} ถูก Apple ปิดการรับรองแล้ว (TSS Rejected) หากฝืนติดตั้งจะติด Error 3194"
            fw_badge = "Unsigned (ห้ามแฟลช)"
            action_recommendations.append("เลือกเวอร์ชันที่ Apple ยังเปิด Signed เท่านั้น")

        checks["firmware_signature"] = {
            "status": fw_status,
            "badge": fw_badge,
            "message": fw_msg,
            "target_version": target_version,
            "signed": is_signed,
            "passed": is_signed
        }

        # -------------------------------------------------------------
        # 4. Host PC Hard Drive Free Space
        # -------------------------------------------------------------
        try:
            total_pc, used_pc, free_pc = shutil.disk_usage(os.path.abspath("."))
            free_pc_gb = round(free_pc / (1024**3), 2)
        except Exception:
            free_pc_gb = 50.0

        if free_pc_gb >= self.PC_HOST_MIN_GB:
            pc_status = "PASS"
            pc_msg = f"คอมพิวเตอร์มีพื้นที่ว่าง {free_pc_gb:.1f} GB เพียงพอสำหรับดาวน์โหลดและแตกไฟล์ IPSW ({firmware_size_gb} GB)"
            pc_badge = "PC พื้นที่พอ"
        else:
            pc_status = "FAIL"
            score -= 30
            critical_flags.append(f"พื้นที่ไดรฟ์ของคอมพิวเตอร์เหลือเพียง {free_pc_gb:.1f} GB (ต้องการอย่างน้อย {self.PC_HOST_MIN_GB} GB)")
            pc_msg = f"ไดรฟ์คอมพิวเตอร์ใกล้เต็ม ต้องการพื้นที่อย่างน้อย {self.PC_HOST_MIN_GB} GB เพื่อโหลดและขยายไฟล์ IPSW"
            pc_badge = "PC พื้นที่เหลือน้อย"
            action_recommendations.append("เคลียร์พื้นที่บนฮาร์ดดิสก์ของคอมพิวเตอร์ให้มีว่างอย่างน้อย 15 GB")

        checks["pc_storage"] = {
            "status": pc_status,
            "badge": pc_badge,
            "message": pc_msg,
            "free_pc_gb": free_pc_gb,
            "required_pc_gb": self.PC_HOST_MIN_GB,
            "passed": pc_status == "PASS"
        }

        # -------------------------------------------------------------
        # 5. Data Backup Advice
        # -------------------------------------------------------------
        checks["backup"] = {
            "status": "INFO",
            "badge": "แนะนำให้สำรองข้อมูล",
            "message": "การอัปเดตแบบ 'Retain User Data' จะเก็บข้อมูลเดิมไว้ทั้งหมด แต่เพื่อความปลอดภัยสูงสุดแนะนำให้ Backup เก็บไว้ 1 ชุด",
            "passed": True
        }

        # Overall Status Calculation
        score = max(0, min(100, score))
        if score >= 85 and not critical_flags:
            overall_verdict = "READY"
            overall_title = "อุปกรณ์มีความพร้อมเต็มที่ (Ready to Update)"
            overall_color = "#34C759"  # Apple Green
        elif score >= 50:
            overall_verdict = "WARNING"
            overall_title = "สามารถอัปเดตได้ แต่มีคำแนะนำที่ต้องจัดการ (Action Needed)"
            overall_color = "#FF9500"  # Apple Orange
        else:
            overall_verdict = "BLOCKED"
            overall_title = "ยังไม่พร้อมอัปเดต มีความเสี่ยงสูง (Blocked - Fix Required)"
            overall_color = "#FF3B30"  # Apple Red

        return {
            "score": score,
            "verdict": overall_verdict,
            "title": overall_title,
            "color": overall_color,
            "checks": checks,
            "critical_flags": critical_flags,
            "action_recommendations": action_recommendations
        }
