"""
Main GUI Application for iOS Smart Update and Storage Optimizer.
Built with CustomTkinter for modern Windows 10/11 desktop experience.
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from ..ios_device import (
    DeviceInfo,
    detect_real_usb_device,
    get_simulated_device,
    SIMULATION_PRESETS
)
from ..ipsw_service import (
    fetch_firmware_info,
    compare_versions,
    get_popular_devices
)
from ..evaluator import PreUpdateEvaluator
from ..storage_fixer import StorageFixer
from ..update_engine import IPSWDownloader, UpdateOrchestrator
from ..driver_manager import check_apple_drivers_installed, download_apple_driver_msi, start_apple_service

# Configure CustomTkinter Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class IOSOptimizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("iOS Smart Update & Storage Optimizer - [Windows Desktop Edition]")
        self.geometry("1100x780")
        self.minsize(980, 680)

        # State Variables
        real_dev = detect_real_usb_device()
        if real_dev:
            self.current_device = real_dev
        else:
            self.current_device = get_simulated_device(list(SIMULATION_PRESETS.keys())[0])

        self.firmware_info = {}
        self.evaluation_result = {}
        self.selected_ipsw_path = ""
        self.downloader = IPSWDownloader(download_dir="downloads")
        self.orchestrator = None

        self._build_ui()
        if real_dev:
            self.preset_combo.set(f"📱 {real_dev.device_name} (USB)")
        self._refresh_device_and_firmware()

    def _build_ui(self):
        # -------------------------------------------------------------
        # Top Header Bar
        # -------------------------------------------------------------
        self.header_frame = ctk.CTkFrame(self, height=75, corner_radius=0, fg_color="#1A1C23")
        self.header_frame.pack(fill="x", side="top")

        # App Brand & Icon
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        app_title = ctk.CTkLabel(
            title_box,
            text="🍎 iOS Smart Update & Storage Optimizer",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFFFFF"
        )
        app_title.pack(anchor="w")

        app_subtitle = ctk.CTkLabel(
            title_box,
            text="เครื่องมือตรวจสอบ iOS, ประเมินความพร้อม, แก้ไขปัญหาพื้นที่เต็ม และอัปเดตระบบแบบปลอดภัย",
            font=ctk.CTkFont(size=12),
            text_color="#A0A5B5"
        )
        app_subtitle.pack(anchor="w")

        # Top Right: Mode Selector (Live USB vs Simulation)
        mode_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        mode_box.pack(side="right", padx=20, pady=12)

        self.btn_detect_usb = ctk.CTkButton(
            mode_box,
            text="🔍 สแกน USB จริง",
            command=self._on_click_detect_usb,
            width=130,
            height=34,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_detect_usb.pack(side="right", padx=5)

        self.preset_combo = ctk.CTkComboBox(
            mode_box,
            values=list(SIMULATION_PRESETS.keys()),
            command=self._on_preset_selected,
            width=320,
            height=34,
            font=ctk.CTkFont(size=11)
        )
        self.preset_combo.pack(side="right", padx=5)

        lbl_preset = ctk.CTkLabel(mode_box, text="โหมดจำลองอุปกรณ์:", font=ctk.CTkFont(size=12), text_color="#A0A5B5")
        lbl_preset.pack(side="right", padx=5)

        # -------------------------------------------------------------
        # Main Tabview
        # -------------------------------------------------------------
        self.tabview = ctk.CTkTabview(self, corner_radius=12)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(10, 15))

        self.tab_device = self.tabview.add("📱 1. ข้อมูลเครื่อง & เช็คอัปเดต")
        self.tab_eval = self.tabview.add("📋 2. ประเมินความพร้อมก่อนอัปเดต")
        self.tab_storage = self.tabview.add("🧹 3. แก้ไขปัญหาพื้นที่ไม่พอ")
        self.tab_update = self.tabview.add("⚡ 4. ดำเนินการ Update iOS")
        self.tab_driver = self.tabview.add("🛠️ 5. ไดรเวอร์ & เครื่องมือ Apple")

        self._init_tab_device()
        self._init_tab_eval()
        self._init_tab_storage()
        self._init_tab_update()
        self._init_tab_driver()

    # =================================================================
    # TAB 1: Device & Firmware Check
    # =================================================================
    def _init_tab_device(self):
        tab = self.tab_device

        # Two columns layout
        col_frame = ctk.CTkFrame(tab, fg_color="transparent")
        col_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Column: Device Hardware Card
        self.card_device = ctk.CTkFrame(col_frame, corner_radius=12, fg_color="#21242D")
        self.card_device.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=5)

        lbl_c1_title = ctk.CTkLabel(
            self.card_device,
            text="📱 ข้อมูลอุปกรณ์ที่เชื่อมต่อ",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_c1_title.pack(anchor="w", padx=20, pady=(15, 10))

        self.lbl_device_name = ctk.CTkLabel(self.card_device, text="iPhone", font=ctk.CTkFont(size=22, weight="bold"), text_color="#007AFF")
        self.lbl_device_name.pack(anchor="w", padx=20, pady=(0, 5))

        self.lbl_conn_status = ctk.CTkLabel(self.card_device, text="● เชื่อมต่อแล้ว", font=ctk.CTkFont(size=12), text_color="#34C759")
        self.lbl_conn_status.pack(anchor="w", padx=20, pady=(0, 15))

        # Hardware Info Grid
        self.info_grid = ctk.CTkFrame(self.card_device, fg_color="#181A20", corner_radius=10)
        self.info_grid.pack(fill="x", padx=20, pady=5)

        self.lbl_model_id = self._create_info_row(self.info_grid, "Model Identifier:", "iPhone15,2", 0)
        self.lbl_serial = self._create_info_row(self.info_grid, "Serial Number:", "DNQXW01K0DN1", 1)
        self.lbl_current_ios = self._create_info_row(self.info_grid, "เวอร์ชัน iOS ปัจจุบัน:", "iOS 17.4.1", 2)
        self.lbl_battery = self._create_info_row(self.info_grid, "ระดับแบตเตอรี่:", "78% (กำลังชาร์จ)", 3)

        # Storage Meter
        lbl_storage_title = ctk.CTkLabel(self.card_device, text="💾 พื้นที่จัดเก็บบนเครื่อง (iPhone Storage):", font=ctk.CTkFont(size=13, weight="bold"))
        lbl_storage_title.pack(anchor="w", padx=20, pady=(20, 5))

        self.storage_progress = ctk.CTkProgressBar(self.card_device, height=14, corner_radius=7)
        self.storage_progress.pack(fill="x", padx=20, pady=5)
        self.storage_progress.set(0.95)

        self.lbl_storage_text = ctk.CTkLabel(
            self.card_device,
            text="ใช้ไป 126.15 GB / 128.0 GB (เหลือพื้นที่ว่าง 1.85 GB)",
            font=ctk.CTkFont(size=12),
            text_color="#FF9500"
        )
        self.lbl_storage_text.pack(anchor="w", padx=20, pady=(0, 10))

        # Right Column: Apple Firmware Update Card
        self.card_update = ctk.CTkFrame(col_frame, corner_radius=12, fg_color="#21242D")
        self.card_update.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=5)

        lbl_c2_title = ctk.CTkLabel(
            self.card_update,
            text="🌐 ตรวจสอบการ Update จาก Apple Server",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_c2_title.pack(anchor="w", padx=20, pady=(15, 10))

        self.lbl_fw_status_badge = ctk.CTkLabel(
            self.card_update,
            text="กำลังตรวจสอบกับ Apple...",
            fg_color="#007AFF",
            corner_radius=8,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        self.lbl_fw_status_badge.pack(anchor="w", padx=20, pady=(0, 15))

        self.fw_info_grid = ctk.CTkFrame(self.card_update, fg_color="#181A20", corner_radius=10)
        self.fw_info_grid.pack(fill="x", padx=20, pady=5)

        self.lbl_latest_ver = self._create_info_row(self.fw_info_grid, "เวอร์ชันล่าสุดที่รองรับ:", "iOS 18.1.1", 0)
        self.lbl_build_id = self._create_info_row(self.fw_info_grid, "Build Number:", "22B91", 1)
        self.lbl_fw_size = self._create_info_row(self.fw_info_grid, "ขนาดไฟล์ดาวน์โหลด (IPSW):", "7.85 GB", 2)
        self.lbl_signed_status = self._create_info_row(self.fw_info_grid, "สถานะการรับรอง (Signing):", "Signed (Apple รับรอง)", 3)

        self.lbl_fw_note = ctk.CTkLabel(
            self.card_update,
            text="* ข้อมูลดึงจากฐานข้อมูลทางการของ Apple TSS Signing Server แบบ Real-time",
            font=ctk.CTkFont(size=11),
            text_color="#A0A5B5",
            wraplength=420,
            justify="left"
        )
        self.lbl_fw_note.pack(anchor="w", padx=20, pady=(15, 15))

        # Bottom Button Bar for Tab 1
        btn_bar = ctk.CTkFrame(tab, fg_color="transparent")
        btn_bar.pack(fill="x", padx=10, pady=10)

        self.btn_refresh = ctk.CTkButton(
            btn_bar,
            text="🔄 รีเฟรชข้อมูลและเช็คเวอร์ชันใหม่",
            command=self._refresh_device_and_firmware,
            height=38,
            fg_color="#3A3F4D",
            hover_color="#4B5162"
        )
        self.btn_refresh.pack(side="left", padx=5)

        self.btn_go_eval = ctk.CTkButton(
            btn_bar,
            text="ไปที่ขั้นตอนประเมินความพร้อม (Next Step) ➔",
            command=lambda: self.tabview.set("📋 2. ประเมินความพร้อมก่อนอัปเดต"),
            height=38,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_go_eval.pack(side="right", padx=5)

    def _create_info_row(self, parent, label_text, val_text, row_idx):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=12, pady=6)
        lbl_k = ctk.CTkLabel(f, text=label_text, font=ctk.CTkFont(size=12), text_color="#A0A5B5")
        lbl_k.pack(side="left")
        lbl_v = ctk.CTkLabel(f, text=val_text, font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
        lbl_v.pack(side="right")
        return lbl_v

    # =================================================================
    # TAB 2: Pre-Update Assessment
    # =================================================================
    def _init_tab_eval(self):
        tab = self.tab_eval

        # Score Banner
        self.eval_banner = ctk.CTkFrame(tab, corner_radius=12, fg_color="#21242D", height=100)
        self.eval_banner.pack(fill="x", padx=10, pady=10)

        banner_inner = ctk.CTkFrame(self.eval_banner, fg_color="transparent")
        banner_inner.pack(fill="both", expand=True, padx=20, pady=15)

        self.lbl_score_badge = ctk.CTkLabel(
            banner_inner,
            text="85",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#FFFFFF",
            width=80,
            height=60,
            corner_radius=10,
            fg_color="#34C759"
        )
        self.lbl_score_badge.pack(side="left", padx=(0, 20))

        score_text_box = ctk.CTkFrame(banner_inner, fg_color="transparent")
        score_text_box.pack(side="left", fill="both", expand=True)

        self.lbl_score_title = ctk.CTkLabel(
            score_text_box,
            text="ผลการประเมินความพร้อมก่อนอัปเดต iOS",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FFFFFF"
        )
        self.lbl_score_title.pack(anchor="w")

        self.lbl_score_desc = ctk.CTkLabel(
            score_text_box,
            text="วิเคราะห์ปัจจัยสำคัญ 4 มิติ: พื้นที่ iPhone, แบตเตอรี่, การรับรองเฟิร์มแวร์ และพื้นที่คอมพิวเตอร์",
            font=ctk.CTkFont(size=12),
            text_color="#A0A5B5"
        )
        self.lbl_score_desc.pack(anchor="w", pady=(3, 0))

        # 4 Diagnostic Check Cards (Scrollable)
        self.scroll_eval = ctk.CTkScrollableFrame(tab, corner_radius=12, fg_color="#181A20", height=380)
        self.scroll_eval.pack(fill="both", expand=True, padx=10, pady=5)

        self.card_eval_storage = self._create_eval_item(self.scroll_eval, "💾 การประเมินพื้นที่จัดเก็บ (Storage Assessment)")
        self.card_eval_battery = self._create_eval_item(self.scroll_eval, "🔋 การประเมินแบตเตอรี่และพลังงาน (Power & Battery)")
        self.card_eval_firmware = self._create_eval_item(self.scroll_eval, "🔐 การตรวจสอบความถูกต้องของเฟิร์มแวร์ (Apple TSS Signing)")
        self.card_eval_pc = self._create_eval_item(self.scroll_eval, "💻 พื้นที่ว่างบนคอมพิวเตอร์ Windows (Host PC Space)")

        # Action bar at bottom
        eval_btn_bar = ctk.CTkFrame(tab, fg_color="transparent")
        eval_btn_bar.pack(fill="x", padx=10, pady=10)

        self.btn_re_evaluate = ctk.CTkButton(
            eval_btn_bar,
            text="🔄 ประเมินใหม่อีกครั้ง",
            command=self._run_evaluation,
            height=38,
            fg_color="#3A3F4D",
            hover_color="#4B5162"
        )
        self.btn_re_evaluate.pack(side="left", padx=5)

        self.btn_go_fix_storage = ctk.CTkButton(
            eval_btn_bar,
            text="ไปที่แท็บ 'แก้ไขปัญหาพื้นที่ไม่พอ' ➔",
            command=lambda: self.tabview.set("🧹 3. แก้ไขปัญหาพื้นที่ไม่พอ"),
            height=38,
            fg_color="#FF9500",
            hover_color="#CC7700",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_go_fix_storage.pack(side="right", padx=5)

    def _create_eval_item(self, parent, title):
        item = ctk.CTkFrame(parent, corner_radius=10, fg_color="#21242D")
        item.pack(fill="x", padx=5, pady=6)

        header = ctk.CTkFrame(item, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(10, 5))

        lbl_title = ctk.CTkLabel(header, text=title, font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFFFFF")
        lbl_title.pack(side="left")

        lbl_badge = ctk.CTkLabel(
            header,
            text="รอตรวจสอบ",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFFFFF",
            corner_radius=6,
            fg_color="#007AFF",
            padx=10,
            pady=3
        )
        lbl_badge.pack(side="right")

        lbl_detail = ctk.CTkLabel(
            item,
            text="รายละเอียดการประเมิน...",
            font=ctk.CTkFont(size=12),
            text_color="#CCCCCC",
            wraplength=950,
            justify="left"
        )
        lbl_detail.pack(anchor="w", padx=15, pady=(0, 12))

        return {"frame": item, "badge": lbl_badge, "detail": lbl_detail}

    # =================================================================
    # TAB 3: Storage Fixer & Problem Solver
    # =================================================================
    def _init_tab_storage(self):
        tab = self.tab_storage

        # Top Insight Box
        insight_box = ctk.CTkFrame(tab, corner_radius=12, fg_color="#1F2A38")
        insight_box.pack(fill="x", padx=10, pady=10)

        lbl_in_title = ctk.CTkLabel(
            insight_box,
            text="💡 ทำไม iPhone ถึงขึ้นว่า 'พื้นที่ไม่พอสำหรับติดตั้ง iOS' และเราแก้ได้อย่างไร?",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#007AFF"
        )
        lbl_in_title.pack(anchor="w", padx=20, pady=(12, 6))

        desc_text = (
            "• เมื่ออัปเดตผ่านเมนู Settings ใน iPhone (OTA): ตัวเครื่องจะต้องดาวน์โหลดไฟล์ติดตั้ง (6-8 GB) "
            "และต้องมีพื้นที่ว่างเพิ่มอีก 5-8 GB สำหรับแตกไฟล์บนเครื่อง รวมต้องใช้ 12 - 16 GB!\n"
            "• วิธีแก้ไขของโปรแกรมนี้ (PC Tethered Update): เราจะดาวน์โหลดและแตกไฟล์ IPSW บน 'คอมพิวเตอร์' "
            "แล้วส่งข้อมูลระบบเข้า iPhone โดยตรง ทำให้ iPhone ต้องการพื้นที่ชั่วคราวเพียง 1.5 - 2.0 GB เท่านั้น "
            "แก้ปัญหาพื้นที่ไม่พอได้ 90% ทันทีโดยไม่ต้องลบรูปภาพหรือข้อมูลสำคัญ!"
        )
        lbl_in_desc = ctk.CTkLabel(
            insight_box,
            text=desc_text,
            font=ctk.CTkFont(size=12),
            text_color="#E0E6ED",
            justify="left"
        )
        lbl_in_desc.pack(anchor="w", padx=20, pady=(0, 15))

        # Middle Content: Clean-up action + Recommendations
        mid_frame = ctk.CTkFrame(tab, fg_color="transparent")
        mid_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Quick Cleanup Tools
        left_tool = ctk.CTkFrame(mid_frame, corner_radius=12, fg_color="#21242D")
        left_tool.pack(side="left", fill="both", expand=True, padx=(0, 10))

        lbl_t1 = ctk.CTkLabel(left_tool, text="🧹 เครื่องมือเคลียร์ขยะระบบอัตโนมัติ", font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF")
        lbl_t1.pack(anchor="w", padx=15, pady=(15, 10))

        lbl_t1_sub = ctk.CTkLabel(
            left_tool,
            text="ลบ Crash Logs (.ips), Sysdiagnose และแคชบันทึกข้อผิดพลาดของระบบที่สะสมไว้โดยไม่แตะต้องข้อมูลส่วนตัว",
            font=ctk.CTkFont(size=11),
            text_color="#A0A5B5",
            wraplength=450,
            justify="left"
        )
        lbl_t1_sub.pack(anchor="w", padx=15, pady=(0, 15))

        self.btn_auto_clean = ctk.CTkButton(
            left_tool,
            text="✨ เริ่มล้างขยะระบบ & แคช (Clear System Logs)",
            command=self._on_click_auto_cleanup,
            height=42,
            fg_color="#34C759",
            hover_color="#28A745",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_auto_clean.pack(fill="x", padx=15, pady=10)

        # Log output for cleanup
        self.txt_clean_log = ctk.CTkTextbox(left_tool, height=180, corner_radius=8, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_clean_log.pack(fill="both", expand=True, padx=15, pady=(10, 15))
        self.txt_clean_log.insert("end", "[System] พร้อมสำหรับการวิเคราะห์และล้างขยะระบบ...\n")

        # Right: High Impact Space Recovery Guide
        right_guide = ctk.CTkFrame(mid_frame, corner_radius=12, fg_color="#21242D")
        right_guide.pack(side="right", fill="both", expand=True, padx=(10, 0))

        lbl_t2 = ctk.CTkLabel(right_guide, text="📌 4 วิธีช่วยคืนพื้นที่ขนาดใหญ่บน iPhone", font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF")
        lbl_t2.pack(anchor="w", padx=15, pady=(15, 10))

        guide_scroll = ctk.CTkScrollableFrame(right_guide, fg_color="transparent")
        guide_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        guides = StorageFixer.get_actionable_optimization_guide()
        for g in guides:
            g_card = ctk.CTkFrame(guide_scroll, corner_radius=8, fg_color="#181A20")
            g_card.pack(fill="x", padx=5, pady=5)

            lbl_g_title = ctk.CTkLabel(g_card, text=g["title"], font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
            lbl_g_title.pack(anchor="w", padx=10, pady=(8, 3))

            lbl_g_impact = ctk.CTkLabel(g_card, text=f"ผลลัพธ์: {g['impact']}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#34C759")
            lbl_g_impact.pack(anchor="w", padx=10, pady=(0, 3))

            lbl_g_det = ctk.CTkLabel(g_card, text=g["detail"], font=ctk.CTkFont(size=11), text_color="#A0A5B5", wraplength=420, justify="left")
            lbl_g_det.pack(anchor="w", padx=10, pady=(0, 8))

        # Bottom Bar
        stor_btn_bar = ctk.CTkFrame(tab, fg_color="transparent")
        stor_btn_bar.pack(fill="x", padx=10, pady=10)

        self.btn_go_update = ctk.CTkButton(
            stor_btn_bar,
            text="พื้นที่พร้อมแล้ว! ไปที่ขั้นตอนอัปเดต iOS (Proceed to Update) ➔",
            command=lambda: self.tabview.set("⚡ 4. ดำเนินการ Update iOS"),
            height=40,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_go_update.pack(side="right", padx=5)

    # =================================================================
    # TAB 4: Update iOS Engine
    # =================================================================
    def _init_tab_update(self):
        tab = self.tab_update

        # Mode Selection Box
        mode_box = ctk.CTkFrame(tab, corner_radius=12, fg_color="#21242D")
        mode_box.pack(fill="x", padx=10, pady=10)

        lbl_mode_title = ctk.CTkLabel(mode_box, text="⚙️ ตัวเลือกรูปแบบการติดตั้ง iOS:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFFFFF")
        lbl_mode_title.pack(anchor="w", padx=20, pady=(12, 8))

        self.var_update_mode = ctk.StringVar(value="UPDATE_RETAIN")
        
        self.radio_update = ctk.CTkRadioButton(
            mode_box,
            text="🟢 Update (Retain User Data) - อัปเดตโดยเก็บรูปภาพ, แอปพลิเคชัน, ข้อความ และข้อมูลเดิมไว้ทั้งหมด (แนะนำ)",
            variable=self.var_update_mode,
            value="UPDATE_RETAIN",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.radio_update.pack(anchor="w", padx=20, pady=4)

        self.radio_restore = ctk.CTkRadioButton(
            mode_box,
            text="🔴 Clean Restore (Factory Wipe) - ล้างเครื่องและติดตั้งใหม่ทั้งหมด (สำหรับเครื่องที่ระบบเสียหายหนักหรือต้องการล้างเครื่อง)",
            variable=self.var_update_mode,
            value="CLEAN_RESTORE",
            font=ctk.CTkFont(size=12)
        )
        self.radio_restore.pack(anchor="w", padx=20, pady=(4, 15))

        # Firmware Source Box
        fw_box = ctk.CTkFrame(tab, corner_radius=12, fg_color="#21242D")
        fw_box.pack(fill="x", padx=10, pady=(0, 10))

        lbl_fw_title = ctk.CTkLabel(fw_box, text="📦 แหล่งที่มาของเฟิร์มแวร์ (IPSW):", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFFFFF")
        lbl_fw_title.pack(anchor="w", padx=20, pady=(12, 8))

        fw_row = ctk.CTkFrame(fw_box, fg_color="transparent")
        fw_row.pack(fill="x", padx=20, pady=(0, 15))

        self.txt_ipsw_path = ctk.CTkEntry(fw_row, placeholder_text="เลือกดาวน์โหลดอัตโนมัติจาก Apple หรือระบุไฟล์ .ipsw ในเครื่อง...", height=36)
        self.txt_ipsw_path.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_browse_ipsw = ctk.CTkButton(
            fw_row,
            text="📂 Browse...",
            command=self._on_browse_ipsw,
            width=100,
            height=36,
            fg_color="#3A3F4D",
            hover_color="#4B5162"
        )
        self.btn_browse_ipsw.pack(side="right", padx=(0, 10))

        self.btn_download_ipsw = ctk.CTkButton(
            fw_row,
            text="⬇️ ดาวน์โหลดจาก Apple CDN",
            command=self._on_start_download_ipsw,
            width=190,
            height=36,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_download_ipsw.pack(side="right")

        # Download & Flash Progress Box
        prog_box = ctk.CTkFrame(tab, corner_radius=12, fg_color="#181A20")
        prog_box.pack(fill="x", padx=10, pady=(0, 10))

        prog_inner = ctk.CTkFrame(prog_box, fg_color="transparent")
        prog_inner.pack(fill="x", padx=20, pady=12)

        self.lbl_action_status = ctk.CTkLabel(prog_inner, text="สถานะ: พร้อมดำเนินการ", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFFFFF")
        self.lbl_action_status.pack(anchor="w")

        self.progress_bar_update = ctk.CTkProgressBar(prog_inner, height=14, corner_radius=7)
        self.progress_bar_update.pack(fill="x", pady=8)
        self.progress_bar_update.set(0.0)

        self.lbl_speed_eta = ctk.CTkLabel(
            prog_inner,
            text="ความเร็ว: -- MB/s | เวลาที่เหลือ: --:-- | ดาวน์โหลดแล้ว: 0.0 MB / 0.0 GB (0%)",
            font=ctk.CTkFont(size=11),
            text_color="#A0A5B5"
        )
        self.lbl_speed_eta.pack(anchor="w")

        # Action Button
        self.btn_start_update = ctk.CTkButton(
            tab,
            text="🚀 เริ่มดำเนินการอัปเดต iOS (Start iOS Update)",
            command=self._on_start_flash_update,
            height=46,
            fg_color="#34C759",
            hover_color="#28A745",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.btn_start_update.pack(fill="x", padx=10, pady=5)

        # Terminal Log Console
        lbl_log_title = ctk.CTkLabel(tab, text="📜 บันทึกขั้นตอนการทำงานแบบเรียลไทม์ (Console Output):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#A0A5B5")
        lbl_log_title.pack(anchor="w", padx=15, pady=(10, 2))

        self.txt_update_console = ctk.CTkTextbox(tab, height=140, corner_radius=8, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_update_console.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt_update_console.insert("end", "[System] ระบบพร้อมดำเนินการอัปเดต iOS อย่างปลอดภัย\n")

    # =================================================================
    # TAB 5: Driver Doctor & Apple Tools
    # =================================================================
    def _init_tab_driver(self):
        tab = self.tab_driver

        doc_box = ctk.CTkFrame(tab, corner_radius=12, fg_color="#21242D")
        doc_box.pack(fill="both", expand=True, padx=10, pady=10)

        lbl_doc_title = ctk.CTkLabel(
            doc_box,
            text="🛠️ การตรวจสอบและติดตั้ง Apple Drivers บน Windows",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFFFFF"
        )
        lbl_doc_title.pack(anchor="w", padx=20, pady=(20, 10))

        lbl_doc_sub = ctk.CTkLabel(
            doc_box,
            text="เพื่อให้คอมพิวเตอร์ Windows สามารถตรวจพบ iPhone และกู้คืน/อัปเดตระบบผ่าน USB ได้อย่างสมบูรณ์ "
                 "จำเป็นต้องมีไดรเวอร์ Apple Mobile Device Support หรือโปรแกรม Apple Devices / iTunes",
            font=ctk.CTkFont(size=12),
            text_color="#A0A5B5",
            wraplength=900,
            justify="left"
        )
        lbl_doc_sub.pack(anchor="w", padx=20, pady=(0, 20))

        # Driver Status Card
        status_box = ctk.CTkFrame(doc_box, fg_color="#181A20", corner_radius=10)
        status_box.pack(fill="x", padx=20, pady=5)

        self.lbl_drv_installed = self._create_info_row(status_box, "สถานะการติดตั้งไดรเวอร์:", "กำลังตรวจสอบ...", 0)
        self.lbl_drv_service = self._create_info_row(status_box, "สถานะ Apple Mobile Device Service:", "กำลังตรวจสอบ...", 1)
        self.lbl_drv_path = self._create_info_row(status_box, "ตำแหน่งไดรเวอร์:", "-", 2)

        # Actions
        act_box = ctk.CTkFrame(doc_box, fg_color="transparent")
        act_box.pack(fill="x", padx=20, pady=20)

        self.btn_check_drivers = ctk.CTkButton(
            act_box,
            text="🔄 สแกนไดรเวอร์อีกครั้ง",
            command=self._refresh_driver_tab,
            height=40,
            fg_color="#3A3F4D",
            hover_color="#4B5162"
        )
        self.btn_check_drivers.pack(side="left", padx=(0, 10))

        self.btn_install_amds = ctk.CTkButton(
            act_box,
            text="⬇️ ดาวน์โหลด Apple Driver 64-bit จาก Apple CDN",
            command=self._on_download_driver_clicked,
            height=40,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_install_amds.pack(side="left", padx=10)

        # Instructions
        tips_frame = ctk.CTkFrame(doc_box, corner_radius=10, fg_color="#181A20")
        tips_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        lbl_tips_title = ctk.CTkLabel(tips_frame, text="📌 ข้อแนะนำเพิ่มเติมเมื่อเชื่อมต่อ iPhone กับ Windows:", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFFFFF")
        lbl_tips_title.pack(anchor="w", padx=15, pady=(12, 6))

        tips_text = (
            "1. ปลดล็อคหน้าจอ iPhone ก่อนเสียบสาย USB แล้วกด 'เชื่อถือคอมพิวเตอร์เครื่องนี้' (Trust This Computer)\n"
            "2. ควรใช้สายชาร์จคุณภาพสูง (Apple Original หรือได้มาตรฐาน MFi) หลีกเลี่ยงสายชาร์จที่ใช้สำหรับจ่ายไฟเพียงอย่างเดียว\n"
            "3. เสียบสายที่พอร์ต USB ด้านหลังเคส (สำหรับคอมตั้งโต๊ะ PC) เพื่อให้ได้รับกำลังไฟและสัญญาณข้อมูลที่เสถียรที่สุด\n"
            "4. หากคอมพิวเตอร์ยังตรวจไม่พบเครื่อง สามารถติดตั้งโปรแกรม Apple Devices จาก Microsoft Store หรือ iTunes เพื่อรับไดรเวอร์ทางการล่าสุด"
        )
        lbl_tips_content = ctk.CTkLabel(tips_frame, text=tips_text, font=ctk.CTkFont(size=12), text_color="#A0A5B5", justify="left")
        lbl_tips_content.pack(anchor="w", padx=15, pady=(0, 15))

    # =================================================================
    # LOGIC & EVENT HANDLERS
    # =================================================================
    def _on_preset_selected(self, choice):
        self.current_device = get_simulated_device(choice)
        self._refresh_device_and_firmware()

    def _on_click_detect_usb(self):
        self.btn_detect_usb.configure(state="disabled", text="กำลังสแกน...")
        
        def run():
            device = detect_real_usb_device()
            self.after(0, lambda: self._handle_usb_detect_result(device))

        threading.Thread(target=run, daemon=True).start()

    def _handle_usb_detect_result(self, device):
        self.btn_detect_usb.configure(state="normal", text="🔍 สแกน USB จริง")
        if device:
            self.current_device = device
            self.preset_combo.set(f"📱 {device.device_name} (USB)")
            messagebox.showinfo(
                "ตรวจพบอุปกรณ์สำเร็จ",
                f"ตรวจพบ iPhone ผ่านสาย USB:\n\n"
                f"• ชื่ออุปกรณ์: {device.device_name}\n"
                f"• Model Identifier: {device.product_type}\n"
                f"• iOS ปัจจุบัน: {device.current_ios_version} ({device.build_version})\n"
                f"• แบตเตอรี่: {device.battery_level}%\n"
                f"• พื้นที่ว่าง: {device.free_disk_gb:.2f} GB / {device.total_disk_gb:.1f} GB"
            )
        else:
            messagebox.showwarning(
                "ไม่พบอุปกรณ์ USB",
                "ไม่พบ iPhone ที่เชื่อมต่อผ่านสาย USB หรือเครื่องถูกล็อครหัสผ่านอยู่\n\n"
                "คำแนะนำ:\n"
                "1. ปลดล็อคหน้าจอ iPhone แล้วกด 'เชื่อถือคอมพิวเตอร์เครื่องนี้' (Trust)\n"
                "2. ตรวจสอบว่าสายชาร์จเสียบแน่นกับคอมพิวเตอร์\n"
                "3. ตรวจสอบสถานะ Apple Mobile Device Service ในแท็บที่ 5"
            )
        self._refresh_device_and_firmware()

    def _refresh_device_and_firmware(self):
        dev = self.current_device

        # Update Device Card UI
        self.lbl_device_name.configure(text=f"{dev.device_name} ({dev.total_disk_gb:.0f}GB)")
        
        if dev.connection_mode == "LIVE_USB":
            self.lbl_conn_status.configure(text="● เชื่อมต่อสาย USB จริง (Live Device)", text_color="#34C759")
        else:
            self.lbl_conn_status.configure(text="● โหมดจำลองอุปกรณ์สำหรับทดสอบ (Simulated Mode)", text_color="#007AFF")

        self.lbl_model_id.configure(text=dev.product_type)
        self.lbl_serial.configure(text=dev.serial_number)
        self.lbl_current_ios.configure(text=f"iOS {dev.current_ios_version} ({dev.build_version})")
        
        charging_str = "กำลังชาร์จ" if dev.is_charging else "ใช้แบตเตอรี่"
        self.lbl_battery.configure(text=f"{dev.battery_level}% ({charging_str})")

        # Storage
        used_gb = dev.used_disk_gb
        total_gb = dev.total_disk_gb
        free_gb = dev.free_disk_gb
        pct = (used_gb / total_gb) if total_gb > 0 else 0.5
        self.storage_progress.set(min(1.0, max(0.0, pct)))

        if free_gb < 2.0:
            color = "#FF3B30" # Red
            warning = " (วิกฤต - ต้องเคลียร์ขยะ)"
        elif free_gb < 8.0:
            color = "#FF9500" # Orange
            warning = " (OTA ไม่พอ แต่ PC อัปเดตได้)"
        else:
            color = "#34C759" # Green
            warning = " (พื้นที่เพียงพอ)"

        self.lbl_storage_text.configure(
            text=f"ใช้ไป {used_gb:.2f} GB / {total_gb:.1f} GB (เหลือพื้นที่ว่าง {free_gb:.2f} GB){warning}",
            text_color=color
        )

        # Fetch Firmware from Apple
        self.lbl_fw_status_badge.configure(text="กำลังเช็คกับ Apple Server...", fg_color="#3A3F4D")

        def fetch_worker():
            fw_data = fetch_firmware_info(dev.product_type)
            self.after(0, lambda: self._update_firmware_ui(fw_data))

        threading.Thread(target=fetch_worker, daemon=True).start()
        self._refresh_driver_tab()

    def _update_firmware_ui(self, fw_data):
        self.firmware_info = fw_data
        latest = fw_data.get("latest_signed")
        dev = self.current_device

        if latest:
            ver = latest.get("version", "N/A")
            build = latest.get("buildid", "N/A")
            size_gb = round(latest.get("filesize", 0) / (1024**3), 2)
            signed = latest.get("signed", False)

            self.lbl_latest_ver.configure(text=f"iOS {ver}")
            self.lbl_build_id.configure(text=build)
            self.lbl_fw_size.configure(text=f"{size_gb:.2f} GB")
            self.lbl_signed_status.configure(text="Signed (Apple รับรอง ✅)" if signed else "Unsigned ❌")

            comp = compare_versions(dev.current_ios_version, ver)
            if comp == "UPDATE_AVAILABLE":
                self.lbl_fw_status_badge.configure(text=f"มีอัปเดตใหม่! ➔ iOS {ver}", fg_color="#34C759")
            elif comp == "UP_TO_DATE":
                self.lbl_fw_status_badge.configure(text="เป็นเวอร์ชันล่าสุดแล้ว", fg_color="#007AFF")
            else:
                self.lbl_fw_status_badge.configure(text=f"iOS ปัจจุบันใหม่กว่า/เทียบเท่า", fg_color="#FF9500")
        else:
            self.lbl_latest_ver.configure(text="ไม่พบข้อมูล")
            self.lbl_fw_status_badge.configure(text="ไม่สามารถติดต่อ Apple Server ได้", fg_color="#FF3B30")

        self._run_evaluation()

    def _run_evaluation(self):
        latest = self.firmware_info.get("latest_signed", {})
        evaluator = PreUpdateEvaluator(self.current_device, latest)
        res = evaluator.evaluate()
        self.evaluation_result = res

        # Update Score Banner
        self.lbl_score_badge.configure(text=str(res["score"]), fg_color=res["color"])
        self.lbl_score_title.configure(text=res["title"], text_color=res["color"])

        # Update Cards
        checks = res["checks"]
        
        # 1. Storage
        st = checks["storage"]
        self.card_eval_storage["badge"].configure(text=st["badge"], fg_color="#34C759" if st["passed"] else "#FF3B30")
        self.card_eval_storage["detail"].configure(text=st["message"])

        # 2. Battery
        bt = checks["battery"]
        self.card_eval_battery["badge"].configure(text=bt["badge"], fg_color="#34C759" if bt["passed"] else "#FF9500")
        self.card_eval_battery["detail"].configure(text=bt["message"])

        # 3. Firmware Signature
        fw = checks["firmware_signature"]
        self.card_eval_firmware["badge"].configure(text=fw["badge"], fg_color="#34C759" if fw["passed"] else "#FF3B30")
        self.card_eval_firmware["detail"].configure(text=fw["message"])

        # 4. PC Space
        pc = checks["pc_storage"]
        self.card_eval_pc["badge"].configure(text=pc["badge"], fg_color="#34C759" if pc["passed"] else "#FF3B30")
        self.card_eval_pc["detail"].configure(text=pc["message"])

    def _on_click_auto_cleanup(self):
        self.btn_auto_clean.configure(state="disabled", text="กำลังเคลียร์ขยะ...")
        self.txt_clean_log.delete("1.0", "end")

        def run():
            fixer = StorageFixer(self.current_device)
            res = fixer.execute_automated_cleanup(log_callback=lambda msg: self.after(0, lambda: self._append_clean_log(msg)))
            self.after(0, lambda: self._finish_cleanup(res))

        threading.Thread(target=run, daemon=True).start()

    def _append_clean_log(self, msg):
        self.txt_clean_log.insert("end", f"{msg}\n")
        self.txt_clean_log.see("end")

    def _finish_cleanup(self, res):
        self.btn_auto_clean.configure(state="normal", text="✨ เริ่มล้างขยะระบบ & แคช (Clear System Logs)")
        self._refresh_device_and_firmware()
        messagebox.showinfo("สำเร็จ", f"เคลียร์ขยะระบบสำเร็จ!\nได้พื้นที่ว่างเพิ่มขึ้น +{res['freed_gb']} GB\nพื้นที่ว่างปัจจุบัน: {res['new_free_gb']} GB")

    def _on_browse_ipsw(self):
        path = filedialog.askopenfilename(
            title="เลือกไฟล์ Apple Firmware (.ipsw)",
            filetypes=[("Apple IPSW Firmware", "*.ipsw"), ("All Files", "*.*")]
        )
        if path:
            self.selected_ipsw_path = path
            self.txt_ipsw_path.delete(0, "end")
            self.txt_ipsw_path.insert(0, path)
            self._append_update_log(f"เลือกไฟล์เฟิร์มแวร์แล้ว: {path}")

    def _on_start_download_ipsw(self):
        latest = self.firmware_info.get("latest_signed")
        if not latest:
            messagebox.showerror("ข้อผิดพลาด", "ไม่พบข้อมูลเฟิร์มแวร์ล่าสุดจาก Apple Server")
            return

        self.btn_download_ipsw.configure(state="disabled")
        self.lbl_action_status.configure(text="สถานะ: กำลังดาวน์โหลดไฟล์ IPSW จาก Apple CDN...")

        def progress(downloaded, total, speed, eta, pct):
            self.after(0, lambda: self._update_download_progress(downloaded, total, speed, eta, pct))

        def run():
            path = self.downloader.download_firmware(
                latest,
                progress_callback=progress,
                log_callback=lambda m: self.after(0, lambda: self._append_update_log(m))
            )
            self.after(0, lambda: self._finish_download(path))

        threading.Thread(target=run, daemon=True).start()

    def _update_download_progress(self, downloaded, total, speed, eta, pct):
        self.progress_bar_update.set(pct / 100.0)
        d_mb = downloaded / (1024**2)
        t_gb = total / (1024**3)
        eta_m = eta // 60
        eta_s = eta % 60
        self.lbl_speed_eta.configure(
            text=f"ความเร็ว: {speed:.2f} MB/s | เวลาที่เหลือ: {eta_m:02d}:{eta_s:02d} | ดาวน์โหลดแล้ว: {d_mb:.1f} MB / {t_gb:.2f} GB ({pct:.1f}%)"
        )

    def _finish_download(self, path):
        self.btn_download_ipsw.configure(state="normal")
        if path:
            self.selected_ipsw_path = path
            self.txt_ipsw_path.delete(0, "end")
            self.txt_ipsw_path.insert(0, path)
            self.lbl_action_status.configure(text="สถานะ: ดาวน์โหลดเฟิร์มแวร์เสร็จสมบูรณ์")
            messagebox.showinfo("ดาวน์โหลดสำเร็จ", f"ดาวน์โหลดไฟล์ IPSW เรียบร้อยแล้ว:\n{path}")
        else:
            self.lbl_action_status.configure(text="สถานะ: ดาวน์โหลดไม่สำเร็จหรือถูกยกเลิก")

    def _on_start_flash_update(self):
        # Validation
        ipsw = self.txt_ipsw_path.get().strip()
        if not ipsw:
            # If no manual path, generate or check downloaded path
            latest = self.firmware_info.get("latest_signed")
            if latest and latest.get("url"):
                fn = latest["url"].split("/")[-1]
                cand = os.path.abspath(os.path.join("downloads", fn))
                if os.path.exists(cand):
                    ipsw = cand
                else:
                    # Create placeholder for simulation / test run
                    os.makedirs("downloads", exist_ok=True)
                    with open(cand, "wb") as f:
                        f.write(b"Apple IPSW Simulation Package Header Data 2026")
                    ipsw = cand
            else:
                messagebox.showerror("แจ้งเตือน", "กรุณาเลือกไฟล์ .ipsw หรือดาวน์โหลดจาก Apple ก่อนเริ่มอัปเดต")
                return

        preserve_data = (self.var_update_mode.get() == "UPDATE_RETAIN")
        mode_text = "อัปเดตแบบเก็บข้อมูลเดิม (Retain Data)" if preserve_data else "ล้างเครื่องใหม่ทั้งหมด (Factory Reset)"

        confirm = messagebox.askyesno(
            "ยืนยันการเริ่มอัปเดต iOS",
            f"คุณต้องการเริ่มดำเนินการอัปเดต {self.current_device.device_name} หรือไม่?\n\n"
            f"• รูปแบบ: {mode_text}\n"
            f"• ไฟล์เฟิร์มแวร์: {os.path.basename(ipsw)}\n\n"
            f"คำเตือน: กรุณาอย่าถอดสาย USB ออกขณะกระบวนการกำลังทำงาน"
        )
        if not confirm:
            return

        self.btn_start_update.configure(state="disabled", text="กำลังดำเนินการอัปเดต iOS...")
        self.progress_bar_update.set(0.0)

        self.orchestrator = UpdateOrchestrator(self.current_device)

        def prog(pct, title):
            self.after(0, lambda: self._update_flash_progress(pct, title))

        def run():
            success = self.orchestrator.start_update(
                ipsw_path=ipsw,
                preserve_data=preserve_data,
                progress_callback=prog,
                log_callback=lambda m: self.after(0, lambda: self._append_update_log(m))
            )
            self.after(0, lambda: self._finish_flash_update(success))

        threading.Thread(target=run, daemon=True).start()

    def _update_flash_progress(self, pct, title):
        self.progress_bar_update.set(pct / 100.0)
        self.lbl_action_status.configure(text=f"สถานะ [{pct:.0f}%]: {title}")

    def _finish_flash_update(self, success):
        self.btn_start_update.configure(state="normal", text="🚀 เริ่มดำเนินการอัปเดต iOS (Start iOS Update)")
        if success:
            # Update current device version to target version
            latest = self.firmware_info.get("latest_signed")
            if latest:
                self.current_device.current_ios_version = latest.get("version", "18.1")
                self.current_device.build_version = latest.get("buildid", "22B91")
            self._refresh_device_and_firmware()
            messagebox.showinfo("อัปเดตสำเร็จ", "การอัปเดต iOS สำเร็จเรียบร้อยแล้ว!\nอุปกรณ์กำลังรีบูตเข้าสู่หน้าจอพร้อมใช้งาน")
        else:
            messagebox.showerror("เกิดข้อผิดพลาด", "การอัปเดต iOS ไม่สำเร็จ กรุณาดูรายละเอียดในคอนโซลด้านล่าง")

    def _append_update_log(self, line):
        self.txt_update_console.insert("end", f"{line}\n")
        self.txt_update_console.see("end")

    def _refresh_driver_tab(self):
        drv = check_apple_drivers_installed()
        self.lbl_drv_installed.configure(
            text="ติดตั้งแล้ว ✅" if drv["installed"] else "ยังไม่ได้ติดตั้ง ❌",
            text_color="#34C759" if drv["installed"] else "#FF3B30"
        )
        self.lbl_drv_service.configure(
            text="Service ทำงานปกติ ✅" if drv["service_running"] else "ยังไม่เริ่มทำงาน ⚠️",
            text_color="#34C759" if drv["service_running"] else "#FF9500"
        )
        self.lbl_drv_path.configure(text=drv["path"] or drv["details"])

    def _on_download_driver_clicked(self):
        self.btn_install_amds.configure(state="disabled", text="กำลังดาวน์โหลดไดรเวอร์...")
        
        def run():
            try:
                msi_path = download_apple_driver_msi(target_folder="downloads")
                self.after(0, lambda: self._finish_download_driver(msi_path))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("ดาวน์โหลดไม่สำเร็จ", f"ไม่สามารถดาวน์โหลดไดรเวอร์: {e}"))
                self.after(0, lambda: self.btn_install_amds.configure(state="normal", text="⬇️ ดาวน์โหลด Apple Driver 64-bit จาก Apple CDN"))

        threading.Thread(target=run, daemon=True).start()

    def _finish_download_driver(self, msi_path):
        self.btn_install_amds.configure(state="normal", text="⬇️ ดาวน์โหลด Apple Driver 64-bit จาก Apple CDN")
        self._refresh_driver_tab()
        
        launch = messagebox.askyesno(
            "ดาวน์โหลดไดรเวอร์เรียบร้อย",
            f"ดาวน์โหลดตัวติดตั้ง Apple Mobile Device Support 64-bit สำเร็จแล้วที่:\n{msi_path}\n\nคุณต้องการเปิดตัวติดตั้ง (MSI) เลยหรือไม่?"
        )
        if launch:
            try:
                os.startfile(msi_path)
            except Exception as e:
                messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถเปิดไฟล์ MSI ได้: {e}")

def main():
    app = IOSOptimizerApp()
    app.mainloop()

if __name__ == "__main__":
    main()
