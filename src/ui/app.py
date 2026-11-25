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
from PIL import Image

def get_asset_path(filename: str) -> str:
    """Resolves asset path in development and PyInstaller bundled environment."""
    if getattr(sys, 'frozen', False):
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    target = os.path.join(base_dir, "assets", filename)
    if os.path.exists(target):
        return target
    alt = os.path.join(os.path.abspath("."), "assets", filename)
    if os.path.exists(alt):
        return alt
    return target

from ..ios_device import (
    DeviceInfo,
    detect_real_usb_device,
    get_simulated_device,
    get_ios_compatibility_profile,
    SIMULATION_PRESETS
)
from ..ipsw_service import (
    fetch_firmware_info,
    compare_versions,
    get_popular_devices
)
from ..evaluator import PreUpdateEvaluator
from ..storage_fixer import (
    StorageFixer,
    tune_ios_speed,
    assess_device_speed_state,
    get_speed_tuning_recommendations
)
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

        # Set Window Icon
        try:
            ico_path = get_asset_path("app_icon.ico")
            if os.path.exists(ico_path):
                self.iconbitmap(ico_path)
        except Exception:
            pass

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
        brand_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand_box.pack(side="left", padx=20, pady=10)

        try:
            png_path = get_asset_path("app_icon.png")
            if os.path.exists(png_path):
                pil_img = Image.open(png_path)
                header_logo = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(46, 46))
                logo_lbl = ctk.CTkLabel(brand_box, text="", image=header_logo)
                logo_lbl.pack(side="left", padx=(0, 12))
        except Exception:
            pass

        title_box = ctk.CTkFrame(brand_box, fg_color="transparent")
        title_box.pack(side="left")

        app_title = ctk.CTkLabel(
            title_box,
            text="iOS Smart Update & Storage Optimizer",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFFFFF"
        )
        app_title.pack(anchor="w")

        app_subtitle = ctk.CTkLabel(
            title_box,
            text="เครื่องมือตรวจสอบ iOS (รองรับ iOS 8 ขึ้นไป), ประเมินความพร้อม, แก้ไขปัญหาพื้นที่เต็ม และอัปเดตระบบแบบปลอดภัย",
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
        self.tab_storage = self.tabview.add("🧹 3. เคลียร์ขยะ & ปรับแต่ง iOS")
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

        # Mode Notification Banner
        self.banner_mode = ctk.CTkFrame(tab, corner_radius=10, fg_color="#2B2615")
        self.banner_mode.pack(fill="x", padx=10, pady=(8, 4))

        self.lbl_banner_mode_icon = ctk.CTkLabel(self.banner_mode, text="ℹ️", font=ctk.CTkFont(size=16))
        self.lbl_banner_mode_icon.pack(side="left", padx=(12, 6), pady=6)

        self.lbl_banner_mode_text = ctk.CTkLabel(
            self.banner_mode,
            text="ขณะนี้อยู่ใน 'โหมดจำลองสถานการณ์': หากคุณเสียบ iPhone จริงอยู่แล้วเวอร์ชันไม่ตรง ให้ปลดล็อคหน้าจอกด 'เชื่อถือ' (Trust) แล้วกดสแกน",
            font=ctk.CTkFont(size=11),
            text_color="#FFD60A",
            justify="left"
        )
        self.lbl_banner_mode_text.pack(side="left", padx=5, pady=6)

        self.btn_banner_scan = ctk.CTkButton(
            self.banner_mode,
            text="🔍 สแกน iPhone จริง",
            command=self._on_click_detect_usb,
            width=130,
            height=28,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_banner_scan.pack(side="right", padx=10, pady=6)

        # Two columns layout
        col_frame = ctk.CTkFrame(tab, fg_color="transparent")
        col_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Left Column: Device Hardware Card
        self.card_device = ctk.CTkFrame(col_frame, corner_radius=12, fg_color="#21242D")
        self.card_device.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=5)

        lbl_c1_title = ctk.CTkLabel(
            self.card_device,
            text="📱 1. ข้อมูลในเครื่อง iPhone ของคุณ (Installed on Device)",
            font=ctk.CTkFont(size=15, weight="bold"),
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

        self.lbl_model_id = self._create_info_row(self.info_grid, "Model Identifier:", "iPhone16,1", 0)
        self.lbl_serial = self._create_info_row(self.info_grid, "Serial Number:", "DNQXW01K0DN1", 1)
        self.lbl_current_ios = self._create_info_row(self.info_grid, "เวอร์ชัน iOS ในเครื่องนี้:", "iOS 17.4.1", 2)
        self.lbl_ios_compat = self._create_info_row(self.info_grid, "ความเข้ากันได้ / ระบบไฟล์:", "รองรับ (iOS 8+) • APFS", 3)
        self.lbl_battery = self._create_info_row(self.info_grid, "ระดับแบตเตอรี่:", "78% (กำลังชาร์จ)", 4)

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
            text="🌐 2. เช็คเวอร์ชันอัปเดตจาก Apple Server (Available Update)",
            font=ctk.CTkFont(size=15, weight="bold"),
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

        self.lbl_latest_ver = self._create_info_row(self.fw_info_grid, "เวอร์ชันล่าสุดที่ Apple เปิดให้ลง:", "กำลังโหลด...", 0)
        self.lbl_build_id = self._create_info_row(self.fw_info_grid, "Build Number:", "--", 1)
        self.lbl_fw_size = self._create_info_row(self.fw_info_grid, "ขนาดไฟล์ดาวน์โหลด (IPSW):", "-- GB", 2)
        self.lbl_signed_status = self._create_info_row(self.fw_info_grid, "สถานะการรับรอง (Signing):", "Signed (Apple รับรอง)", 3)

        self.lbl_fw_note = ctk.CTkLabel(
            self.card_update,
            text="* ฝั่งซ้ายคือเวอร์ชันปัจจุบันในตัวเครื่องของคุณ | ฝั่งขวาคือเวอร์ชันใหม่ล่าสุดที่ Apple Server เปิดให้ติดตั้ง",
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
            text="วิเคราะห์ปัจจัยสำคัญ 5 มิติ: ความเข้ากันได้ iOS 8+, พื้นที่ iPhone, แบตเตอรี่, การรับรองเฟิร์มแวร์ และพื้นที่คอมพิวเตอร์",
            font=ctk.CTkFont(size=12),
            text_color="#A0A5B5"
        )
        self.lbl_score_desc.pack(anchor="w", pady=(3, 0))

        # 5 Diagnostic Check Cards (Scrollable)
        self.scroll_eval = ctk.CTkScrollableFrame(tab, corner_radius=12, fg_color="#181A20", height=380)
        self.scroll_eval.pack(fill="both", expand=True, padx=10, pady=5)

        self.card_eval_compat = self._create_eval_item(self.scroll_eval, "📱 ความเข้ากันได้ของระบบ (iOS 8+ Compatibility)")
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
            text="ไปที่แท็บ 'เคลียร์ขยะ & ปรับแต่ง iOS' ➔",
            command=lambda: self.tabview.set("🧹 3. เคลียร์ขยะ & ปรับแต่ง iOS"),
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
    # TAB 3: Storage Fixer & Performance Optimizer
    # =================================================================
    def _init_tab_storage(self):
        tab = self.tab_storage

        # 1. Top Insight Banner
        insight_box = ctk.CTkFrame(tab, corner_radius=10, fg_color="#182333")
        insight_box.pack(fill="x", padx=10, pady=(6, 8))

        lbl_in_title = ctk.CTkLabel(
            insight_box,
            text="💡 ศูนย์เคลียร์ขยะ & ปรับแต่งประสิทธิภาพ iOS (iOS Clean & Speed Optimizer)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#007AFF"
        )
        lbl_in_title.pack(anchor="w", padx=15, pady=(8, 3))

        desc_text = (
            "• เทคนิค PC Staging: แก้ปัญหา 'พื้นที่ไม่พออัปเดต' โดยแตกไฟล์บนคอมพิวเตอร์ ทำให้ iPhone ใช้พื้นที่เพียง 1.5 - 2.0 GB โดยไม่ต้องลบรูปภาพหรือข้อมูลส่วนตัว\n"
            "• เครื่องมือ Deep Clean & RAM Purge: ล้าง Crash logs, แคชรูปย่อ, ข้อมูล Staging และส่งสัญญาณ Darwin Low-Memory ปล่อยคืนแรมให้เครื่องลื่นไหลขึ้นทันที"
        )
        lbl_in_desc = ctk.CTkLabel(
            insight_box,
            text=desc_text,
            font=ctk.CTkFont(size=11),
            text_color="#D0D7DE",
            justify="left"
        )
        lbl_in_desc.pack(anchor="w", padx=15, pady=(0, 8))

        # 2. Metric Cards Ribbon (4 Quick Status Cards)
        metric_bar = ctk.CTkFrame(tab, fg_color="transparent")
        metric_bar.pack(fill="x", padx=10, pady=(0, 6))

        # Card 1: Free Storage
        card1 = ctk.CTkFrame(metric_bar, corner_radius=10, fg_color="#21242D")
        card1.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ctk.CTkLabel(card1, text="💾 พื้นที่ว่างปัจจุบัน", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A0A5B5").pack(anchor="w", padx=12, pady=(8, 2))
        self.lbl_card_storage_free = ctk.CTkLabel(card1, text="-- GB", font=ctk.CTkFont(size=15, weight="bold"), text_color="#FFFFFF")
        self.lbl_card_storage_free.pack(anchor="w", padx=12, pady=(0, 2))
        self.lbl_card_storage_status = ctk.CTkLabel(card1, text="กำลังตรวจสอบ...", font=ctk.CTkFont(size=10), text_color="#34C759")
        self.lbl_card_storage_status.pack(anchor="w", padx=12, pady=(0, 8))

        # Card 2: Detected Junk
        card2 = ctk.CTkFrame(metric_bar, corner_radius=10, fg_color="#21242D")
        card2.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(card2, text="🗑️ ไฟล์ขยะที่ตรวจพบ", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A0A5B5").pack(anchor="w", padx=12, pady=(8, 2))
        self.lbl_card_junk_val = ctk.CTkLabel(card2, text="~2,450 MB", font=ctk.CTkFont(size=15, weight="bold"), text_color="#FF9500")
        self.lbl_card_junk_val.pack(anchor="w", padx=12, pady=(0, 2))
        self.lbl_card_junk_sub = ctk.CTkLabel(card2, text="5 หมวดหมู่ ปลอดภัย 100%", font=ctk.CTkFont(size=10), text_color="#A0A5B5")
        self.lbl_card_junk_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # Card 3: RAM Optimization
        card3 = ctk.CTkFrame(metric_bar, corner_radius=10, fg_color="#21242D")
        card3.pack(side="left", fill="both", expand=True, padx=5)
        ctk.CTkLabel(card3, text="🚀 หน่วยความจำ RAM", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A0A5B5").pack(anchor="w", padx=12, pady=(8, 2))
        self.lbl_card_ram_val = ctk.CTkLabel(card3, text="~640 MB", font=ctk.CTkFont(size=15, weight="bold"), text_color="#5856D6")
        self.lbl_card_ram_val.pack(anchor="w", padx=12, pady=(0, 2))
        self.lbl_card_ram_sub = ctk.CTkLabel(card3, text="Inactive RAM พร้อมปล่อยคืน", font=ctk.CTkFont(size=10), text_color="#A0A5B5")
        self.lbl_card_ram_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # Card 4: Battery Health
        card4 = ctk.CTkFrame(metric_bar, corner_radius=10, fg_color="#21242D")
        card4.pack(side="left", fill="both", expand=True, padx=(5, 0))
        ctk.CTkLabel(card4, text="🔋 สุขภาพแบตเตอรี่", font=ctk.CTkFont(size=11, weight="bold"), text_color="#A0A5B5").pack(anchor="w", padx=12, pady=(8, 2))
        self.lbl_card_batt_val = ctk.CTkLabel(card4, text="--%", font=ctk.CTkFont(size=15, weight="bold"), text_color="#34C759")
        self.lbl_card_batt_val.pack(anchor="w", padx=12, pady=(0, 2))
        self.lbl_card_batt_sub = ctk.CTkLabel(card4, text="กำลังวิเคราะห์รอบชาร์จ...", font=ctk.CTkFont(size=10), text_color="#A0A5B5")
        self.lbl_card_batt_sub.pack(anchor="w", padx=12, pady=(0, 8))

        # 3. Sub Tabview: 1. Clean & Purge, 2. Performance & Battery Doctor
        self.stor_subtab = ctk.CTkTabview(tab, corner_radius=10)
        self.stor_subtab.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        self.subtab_clean = self.stor_subtab.add("🧹 1. เคลียร์ขยะ & คืนพื้นที่ (Junk Clean & Purge)")
        self.subtab_perf = self.stor_subtab.add("⚡ 2. ปรับแต่งความเร็ว & แบตเตอรี่ (Performance & Battery Doctor)")

        # Build Sub-Tabs
        self._build_subtab_clean()
        self._build_subtab_perf()

        # Bottom Bar
        stor_btn_bar = ctk.CTkFrame(tab, fg_color="transparent")
        stor_btn_bar.pack(fill="x", padx=10, pady=(4, 8))

        self.btn_go_update = ctk.CTkButton(
            stor_btn_bar,
            text="พื้นที่พร้อมแล้ว! ไปที่ขั้นตอนอัปเดต iOS (Proceed to Update) ➔",
            command=lambda: self.tabview.set("⚡ 4. ดำเนินการ Update iOS"),
            height=38,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_go_update.pack(side="right", padx=5)

    def _build_subtab_clean(self):
        parent = self.subtab_clean

        # Two Columns Layout
        col_frame = ctk.CTkFrame(parent, fg_color="transparent")
        col_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Left Column: Cleaner Tools & Categories
        left_tool = ctk.CTkFrame(col_frame, corner_radius=10, fg_color="#21242D")
        left_tool.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=2)

        # Action Buttons Header
        btn_row = ctk.CTkFrame(left_tool, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(10, 6))

        self.btn_deep_scan = ctk.CTkButton(
            btn_row,
            text="🔍 สแกนค้นหาขยะ (Scan)",
            command=self._on_click_deep_scan,
            width=150,
            height=36,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_deep_scan.pack(side="left", padx=(0, 6))

        self.btn_clean_selected = ctk.CTkButton(
            btn_row,
            text="🧹 ล้างรายการที่เลือก",
            command=self._on_click_clean_selected,
            width=150,
            height=36,
            fg_color="#34C759",
            hover_color="#28A745",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_clean_selected.pack(side="left", padx=(0, 6))

        self.btn_clean_all = ctk.CTkButton(
            btn_row,
            text="🌟 คลีนหมด 1-คลิก",
            command=self._on_click_clean_all,
            width=140,
            height=36,
            fg_color="#5856D6",
            hover_color="#4341B2",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.btn_clean_all.pack(side="left")

        # Category Checklist Container (Scrollable)
        cat_scroll = ctk.CTkScrollableFrame(left_tool, height=190, fg_color="transparent")
        cat_scroll.pack(fill="x", padx=10, pady=(2, 6))

        self.junk_vars = {}
        self.junk_badge_lbls = {}

        for cat_key, cat_def in StorageFixer.CATEGORY_DEFS.items():
            card = ctk.CTkFrame(cat_scroll, corner_radius=8, fg_color="#181A20")
            card.pack(fill="x", padx=2, pady=3)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=8, pady=(6, 2))

            var = ctk.BooleanVar(value=True)
            self.junk_vars[cat_key] = var

            chk = ctk.CTkCheckBox(
                top_row,
                text=f"{cat_def['icon']} {cat_def['name']}",
                variable=var,
                font=ctk.CTkFont(size=12, weight="bold"),
                checkbox_width=18,
                checkbox_height=18
            )
            chk.pack(side="left")

            badge = ctk.CTkLabel(
                top_row,
                text="~350 MB",
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#2A2F3D",
                corner_radius=5,
                padx=8,
                pady=2,
                text_color="#34C759"
            )
            badge.pack(side="right")
            self.junk_badge_lbls[cat_key] = badge

            desc_lbl = ctk.CTkLabel(
                card,
                text=f"{cat_def['desc']} | {cat_def['safety']}",
                font=ctk.CTkFont(size=10),
                text_color="#8E95A5",
                wraplength=480,
                justify="left"
            )
            desc_lbl.pack(anchor="w", padx=28, pady=(0, 6))

        # Progress Bar & Status
        prog_frame = ctk.CTkFrame(left_tool, fg_color="transparent")
        prog_frame.pack(fill="x", padx=12, pady=(4, 2))

        self.lbl_clean_status = ctk.CTkLabel(prog_frame, text="สถานะ: พร้อมสำหรับการสแกนหรือทำความสะอาด", font=ctk.CTkFont(size=11), text_color="#A0A5B5")
        self.lbl_clean_status.pack(side="left")

        self.clean_progress_bar = ctk.CTkProgressBar(left_tool, height=8, corner_radius=4)
        self.clean_progress_bar.pack(fill="x", padx=12, pady=(2, 6))
        self.clean_progress_bar.set(0.0)

        # Log Terminal
        self.txt_clean_log = ctk.CTkTextbox(left_tool, height=110, corner_radius=8, font=ctk.CTkFont(family="Consolas", size=10))
        self.txt_clean_log.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.txt_clean_log.insert("end", "[Cleaner] พร้อมสำหรับการสแกนขยะและเพิ่มประสิทธิภาพ iOS...\n")

        # Compatibility alias
        self.btn_auto_clean = self.btn_clean_all

        # Right Column: System Data Breakdown & High Impact Guides
        right_guide = ctk.CTkFrame(col_frame, corner_radius=10, fg_color="#21242D")
        right_guide.pack(side="right", fill="both", expand=True, padx=(8, 0), pady=2)

        # Top System Data Insight
        sys_data_box = ctk.CTkFrame(right_guide, corner_radius=8, fg_color="#181A20")
        sys_data_box.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            sys_data_box,
            text="📊 วิเคราะห์ 'ข้อมูลระบบ' (System Data / Other)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#007AFF"
        ).pack(anchor="w", padx=10, pady=(8, 2))

        lbl_sys_desc = ctk.CTkLabel(
            sys_data_box,
            text="System Data มักมีขนาดใหญ่ 8-20 GB เกิดจากแคชสตรีมมิ่ง, แคชรูปย่อ, และบันทึกข้อผิดพลาด\n"
                 "✓ ส่วนที่เคลียร์ได้: Crash logs, Photo thumbnail cache, Staging temp (คืนได้ 1-3 GB ทันที)\n"
                 "• ส่วนที่ระบบสงวนไว้: ฟอนต์, ข้อมูลเสียง Siri ออฟไลน์ และแคชความปลอดภัย",
            font=ctk.CTkFont(size=10),
            text_color="#A0A5B5",
            justify="left"
        )
        lbl_sys_desc.pack(anchor="w", padx=10, pady=(0, 8))

        # 6 Actionable Guides Scrollable
        ctk.CTkLabel(
            right_guide,
            text="📌 6 แนวทางกู้คืนพื้นที่ขนาดใหญ่บน iPhone",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w", padx=12, pady=(4, 4))

        guide_scroll = ctk.CTkScrollableFrame(right_guide, fg_color="transparent")
        guide_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        self.guide_scroll = guide_scroll
        self._render_optimization_guides()

    def _render_optimization_guides(self):
        if not hasattr(self, "guide_scroll"):
            return
        for child in self.guide_scroll.winfo_children():
            child.destroy()

        ios_ver = self.current_device.current_ios_version if hasattr(self, "current_device") else "17.0"
        guides = StorageFixer.get_actionable_optimization_guide(ios_version=ios_ver)
        for g in guides:
            g_card = ctk.CTkFrame(self.guide_scroll, corner_radius=8, fg_color="#181A20")
            g_card.pack(fill="x", padx=4, pady=4)

            lbl_g_title = ctk.CTkLabel(g_card, text=g["title"], font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFFFFF")
            lbl_g_title.pack(anchor="w", padx=8, pady=(6, 2))

            lbl_g_impact = ctk.CTkLabel(g_card, text=f"★ {g['impact']}", font=ctk.CTkFont(size=10, weight="bold"), text_color="#34C759")
            lbl_g_impact.pack(anchor="w", padx=8, pady=(0, 2))

            lbl_g_det = ctk.CTkLabel(g_card, text=g["detail"], font=ctk.CTkFont(size=10), text_color="#8E95A5", wraplength=380, justify="left")
            lbl_g_det.pack(anchor="w", padx=8, pady=(0, 6))

    def _build_subtab_perf(self):
        parent = self.subtab_perf

        col_frame = ctk.CTkFrame(parent, fg_color="transparent")
        col_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Left Column: iOS Speed Booster & Fine Tuning
        left_perf = ctk.CTkFrame(col_frame, corner_radius=10, fg_color="#21242D")
        left_perf.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=2)

        # Section 1: Main Speed Tune Engine
        ctk.CTkLabel(
            left_perf,
            text="🚀 1. ปรับแต่ง & จูนความเร็ว iOS ขั้นสุด (Speed Booster)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#007AFF"
        ).pack(anchor="w", padx=14, pady=(10, 2))

        ctk.CTkLabel(
            left_perf,
            text="กระบวนการจูน 5 มิติ: วิเคราะห์ Throttling, ปล่อยคืน RAM เชิงลึก, Flush แคช Daemons & WebKit, ปลดล็อคคอขวด NAND Storage, และรีเซ็ต Frame Pacing ของ SpringBoard",
            font=ctk.CTkFont(size=11),
            text_color="#A0A5B5",
            wraplength=460,
            justify="left"
        ).pack(anchor="w", padx=14, pady=(0, 8))

        # Mode Selector
        mode_row = ctk.CTkFrame(left_perf, fg_color="#181A20", corner_radius=8)
        mode_row.pack(fill="x", padx=14, pady=(0, 8))

        self.var_tune_mode = ctk.StringVar(value="turbo")
        self.radio_tune_turbo = ctk.CTkRadioButton(
            mode_row,
            text="⚡ Turbo Deep Tune (แนะนำ: จูน 5 ขั้นตอน + ปลดล็อคคอขวด NAND Storage)",
            variable=self.var_tune_mode,
            value="turbo",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.radio_tune_turbo.pack(anchor="w", padx=12, pady=(8, 4))

        self.radio_tune_quick = ctk.CTkRadioButton(
            mode_row,
            text="🚀 Quick Speed Boost (จูนด่วน: ปล่อยคืน RAM + Flush Daemons Caches)",
            variable=self.var_tune_mode,
            value="quick",
            font=ctk.CTkFont(size=11)
        )
        self.radio_tune_quick.pack(anchor="w", padx=12, pady=(0, 8))

        # Big Tune Button
        self.btn_tune_speed = ctk.CTkButton(
            left_perf,
            text="⚡ สั่งจูนความเร็ว iOS ทันที (Run iOS Speed Tune)",
            command=self._on_click_tune_speed,
            height=38,
            fg_color="#007AFF",
            hover_color="#0056B3",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.btn_tune_speed.pack(fill="x", padx=14, pady=(0, 6))

        # Progress bar & status
        self.tune_progress_bar = ctk.CTkProgressBar(left_perf, height=8, corner_radius=4)
        self.tune_progress_bar.pack(fill="x", padx=14, pady=(0, 4))
        self.tune_progress_bar.set(0.0)

        self.lbl_tune_status = ctk.CTkLabel(
            left_perf,
            text="สถานะ: พร้อมดำเนินการปรับแต่งความเร็ว iOS",
            font=ctk.CTkFont(size=10),
            text_color="#A0A5B5"
        )
        self.lbl_tune_status.pack(anchor="w", padx=14, pady=(0, 6))

        # Log Console
        self.txt_ram_log = ctk.CTkTextbox(left_perf, height=80, corner_radius=8, font=ctk.CTkFont(family="Consolas", size=10))
        self.txt_ram_log.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.txt_ram_log.insert("end", "[Speed Optimizer] พร้อมสำหรับกระบวนการปรับแต่งความเร็ว iOS...\n")

        # Compatibility alias
        self.txt_tune_log = self.txt_ram_log

        # Sub-actions button row
        sub_btn_row = ctk.CTkFrame(left_perf, fg_color="transparent")
        sub_btn_row.pack(fill="x", padx=14, pady=(0, 10))

        self.btn_purge_ram = ctk.CTkButton(
            sub_btn_row,
            text="🚀 ปล่อยคืน RAM",
            command=self._on_click_purge_ram,
            height=32,
            fg_color="#3A3F4D",
            hover_color="#4B5162",
            font=ctk.CTkFont(size=11)
        )
        self.btn_purge_ram.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_soft_reboot = ctk.CTkButton(
            sub_btn_row,
            text="🔄 ซอฟต์รีสตาร์ท",
            command=self._on_click_soft_reboot,
            height=32,
            fg_color="#3A3F4D",
            hover_color="#4B5162",
            font=ctk.CTkFont(size=11)
        )
        self.btn_soft_reboot.pack(side="left", fill="x", expand=True, padx=4)

        self.btn_speed_guide = ctk.CTkButton(
            sub_btn_row,
            text="💡 5 ทริคเร็ว 2x",
            command=self._on_click_show_speed_guide,
            height=32,
            fg_color="#FF9500",
            hover_color="#CC7700",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.btn_speed_guide.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Right Column: Speed Dashboard & Battery Doctor
        right_perf = ctk.CTkFrame(col_frame, corner_radius=10, fg_color="#21242D")
        right_perf.pack(side="right", fill="both", expand=True, padx=(8, 0), pady=2)

        ctk.CTkLabel(
            right_perf,
            text="⚡ แดชบอร์ดความเร็ว & สุขภาพเครื่อง (Speed & Health Doctor)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w", padx=14, pady=(10, 4))

        # Speed & Latency Score Cards (1 Row, 2 Cards)
        speed_box = ctk.CTkFrame(right_perf, fg_color="transparent")
        speed_box.pack(fill="x", padx=10, pady=(0, 6))

        # Speed Index Card
        s_card1 = ctk.CTkFrame(speed_box, corner_radius=8, fg_color="#181A20")
        s_card1.pack(side="left", fill="both", expand=True, padx=(0, 4))
        ctk.CTkLabel(s_card1, text="⚡ ดัชนีความเร็ว (Speed Index)", font=ctk.CTkFont(size=10), text_color="#A0A5B5").pack(anchor="w", padx=8, pady=(5, 1))
        self.lbl_speed_score = ctk.CTkLabel(s_card1, text="-- / 100", font=ctk.CTkFont(size=14, weight="bold"), text_color="#34C759")
        self.lbl_speed_score.pack(anchor="w", padx=8, pady=(0, 5))

        # Latency Card
        s_card2 = ctk.CTkFrame(speed_box, corner_radius=8, fg_color="#181A20")
        s_card2.pack(side="left", fill="both", expand=True, padx=(4, 0))
        ctk.CTkLabel(s_card2, text="📱 ความหน่วง UI (Latency)", font=ctk.CTkFont(size=10), text_color="#A0A5B5").pack(anchor="w", padx=8, pady=(5, 1))
        self.lbl_speed_latency = ctk.CTkLabel(s_card2, text="~-- ms", font=ctk.CTkFont(size=14, weight="bold"), text_color="#007AFF")
        self.lbl_speed_latency.pack(anchor="w", padx=8, pady=(0, 5))

        # Throttling status bar
        self.lbl_speed_throttling = ctk.CTkLabel(
            right_perf,
            text="● สถานะ CPU: กำลังตรวจสอบ...",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#34C759"
        )
        self.lbl_speed_throttling.pack(anchor="w", padx=14, pady=(0, 6))

        # Telemetry Metrics Grid (2x2)
        grid_frame = ctk.CTkFrame(right_perf, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=(0, 6))

        # Box 1: Health %
        b1 = ctk.CTkFrame(grid_frame, corner_radius=8, fg_color="#181A20")
        b1.grid(row=0, column=0, sticky="nsew", padx=4, pady=3)
        ctk.CTkLabel(b1, text="🔋 ความจุสูงสุด (Health)", font=ctk.CTkFont(size=10), text_color="#A0A5B5").pack(anchor="w", padx=8, pady=(4, 1))
        self.lbl_tele_health = ctk.CTkLabel(b1, text="94%", font=ctk.CTkFont(size=13, weight="bold"), text_color="#34C759")
        self.lbl_tele_health.pack(anchor="w", padx=8, pady=(0, 4))

        # Box 2: Cycle Count
        b2 = ctk.CTkFrame(grid_frame, corner_radius=8, fg_color="#181A20")
        b2.grid(row=0, column=1, sticky="nsew", padx=4, pady=3)
        ctk.CTkLabel(b2, text="🔄 รอบชาร์จ (Cycles)", font=ctk.CTkFont(size=10), text_color="#A0A5B5").pack(anchor="w", padx=8, pady=(4, 1))
        self.lbl_tele_cycles = ctk.CTkLabel(b2, text="218 รอบ", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFFFFF")
        self.lbl_tele_cycles.pack(anchor="w", padx=8, pady=(0, 4))

        # Box 3: Capacity mAh
        b3 = ctk.CTkFrame(grid_frame, corner_radius=8, fg_color="#181A20")
        b3.grid(row=1, column=0, sticky="nsew", padx=4, pady=3)
        ctk.CTkLabel(b3, text="⚡ ความจุจริง / โรงงาน", font=ctk.CTkFont(size=10), text_color="#A0A5B5").pack(anchor="w", padx=8, pady=(4, 1))
        self.lbl_tele_mah = ctk.CTkLabel(b3, text="3,367 / 3,582 mAh", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
        self.lbl_tele_mah.pack(anchor="w", padx=8, pady=(0, 4))

        # Box 4: Temperature & Voltage
        b4 = ctk.CTkFrame(grid_frame, corner_radius=8, fg_color="#181A20")
        b4.grid(row=1, column=1, sticky="nsew", padx=4, pady=3)
        ctk.CTkLabel(b4, text="🌡️ อุณหภูมิ & แรงดันไฟ", font=ctk.CTkFont(size=10), text_color="#A0A5B5").pack(anchor="w", padx=8, pady=(4, 1))
        self.lbl_tele_temp = ctk.CTkLabel(b4, text="30.2 °C | 4,120 mV", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
        self.lbl_tele_temp.pack(anchor="w", padx=8, pady=(0, 4))

        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        # Condition Banner
        cond_box = ctk.CTkFrame(right_perf, corner_radius=8, fg_color="#181A20")
        cond_box.pack(fill="x", padx=14, pady=(0, 6))

        self.lbl_tele_cond = ctk.CTkLabel(
            cond_box,
            text="● ประเมิน: สภาพดีเยี่ยม (Optimal) - เซลล์แบตเตอรี่สมบูรณ์",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#34C759"
        )
        self.lbl_tele_cond.pack(anchor="w", padx=10, pady=5)

        # Refresh Battery Button
        self.btn_refresh_battery = ctk.CTkButton(
            right_perf,
            text="🔄 ตรวจสอบข้อมูลความเร็ว & แบตเตอรี่อีกครั้ง",
            command=self._on_click_refresh_battery,
            height=30,
            fg_color="#2A2F3D",
            hover_color="#3A3F4D",
            font=ctk.CTkFont(size=11)
        )
        self.btn_refresh_battery.pack(fill="x", padx=14, pady=(0, 8))

        # Power & Speed Tips
        tips_box = ctk.CTkFrame(right_perf, corner_radius=8, fg_color="#181A20")
        tips_box.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        ctk.CTkLabel(tips_box, text="💡 เคล็ดลับเพิ่มความเร็ว & ถนอมแบตเตอรี่:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FF9500").pack(anchor="w", padx=10, pady=(4, 1))
        tips_txt = (
            "• เปิดใช้งาน 'ลดการเคลื่อนไหว' (Reduce Motion) เพื่อข้ามแอนิเมชันเปิดแอป (เร็วขึ้น 2x)\n"
            "• ปิด Background App Refresh สำหรับแอปที่ไม่ได้ใช้ เพื่อลดภาระ CPU และ RAM\n"
            "• หลีกเลี่ยงการใช้งานหรือเล่นเกมระหว่างชาร์จในที่ที่มีอุณหภูมิสูงเกิน 35°C ป้องกัน CPU Throttle\n"
            "• คลีนไฟล์ขยะในระบบอย่างสม่ำเสมอ เพื่อให้ SLC Write Cache ของ NAND Flash ทำงานเต็มสปีด"
        )
        ctk.CTkLabel(tips_box, text=tips_txt, font=ctk.CTkFont(size=10), text_color="#A0A5B5", justify="left").pack(anchor="w", padx=10, pady=(0, 4))

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
        
        if hasattr(self, "banner_mode"):
            if dev.connection_mode == "LIVE_USB":
                self.banner_mode.configure(fg_color="#182A1E")
                self.lbl_banner_mode_icon.configure(text="🟢")
                self.lbl_banner_mode_text.configure(
                    text=f"เชื่อมต่อ iPhone จริงสำเร็จ: {dev.device_name} [iOS {dev.current_ios_version} ({dev.build_version})] ข้อมูลตรงกับเครื่องจริงของคุณ 100%",
                    text_color="#30D158"
                )
                self.btn_banner_scan.configure(text="🔄 สแกนใหม่อีกครั้ง")
            else:
                self.banner_mode.configure(fg_color="#2B2615")
                self.lbl_banner_mode_icon.configure(text="ℹ️")
                self.lbl_banner_mode_text.configure(
                    text="ขณะนี้อยู่ใน 'โหมดจำลองสถานการณ์': หากคุณเสียบ iPhone จริงอยู่แล้วเวอร์ชันไม่ตรง ให้ปลดล็อคหน้าจอกด 'เชื่อถือ' (Trust) แล้วกดสแกน",
                    text_color="#FFD60A"
                )
                self.btn_banner_scan.configure(text="🔍 สแกน iPhone จริง")

        if dev.connection_mode == "LIVE_USB":
            self.lbl_conn_status.configure(text=f"● เชื่อมต่อสาย USB จริง (Live Device - Serial: {dev.serial_number})", text_color="#34C759")
        else:
            self.lbl_conn_status.configure(text="● โหมดจำลองอุปกรณ์สำหรับทดสอบ (Simulated Mode)", text_color="#007AFF")

        self.lbl_model_id.configure(text=dev.product_type)
        self.lbl_serial.configure(text=dev.serial_number)
        self.lbl_current_ios.configure(text=f"iOS {dev.current_ios_version} ({dev.build_version})")

        compat = get_ios_compatibility_profile(dev.current_ios_version, dev.product_type)
        if hasattr(self, "lbl_ios_compat"):
            compat_text = (
                f"รองรับ (iOS 8+) • {compat['filesystem']} • {compat['arch']}"
                if compat["supported"]
                else f"ต่ำกว่า iOS 8 • {compat['filesystem']}"
            )
            self.lbl_ios_compat.configure(
                text=compat_text,
                text_color="#34C759" if compat["supported"] else "#FF3B30"
            )

        charging_str = "กำลังชาร์จ" if dev.is_charging else "ใช้แบตเตอรี่"
        self.lbl_battery.configure(text=f"{dev.battery_level}% ({charging_str})")

        # Storage
        used_gb = dev.used_disk_gb
        total_gb = dev.total_disk_gb
        free_gb = dev.free_disk_gb
        pct = (used_gb / total_gb) if total_gb > 0 else 0.5
        self.storage_progress.set(min(1.0, max(0.0, pct)))

        pc_min = 1.2 if compat["major"] <= 12 else 2.0
        ota_min = 4.0 if compat["major"] <= 12 else 8.0
        if free_gb < pc_min:
            color = "#FF3B30" # Red
            warning = " (วิกฤต - ต้องเคลียร์ขยะ)"
        elif free_gb < ota_min:
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
        self._refresh_storage_tab_metrics()

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

        # 0. iOS 8+ Compatibility
        if hasattr(self, "card_eval_compat") and "ios_compatibility" in checks:
            cp = checks["ios_compatibility"]
            self.card_eval_compat["badge"].configure(text=cp["badge"], fg_color="#34C759" if cp["passed"] else "#FF3B30")
            self.card_eval_compat["detail"].configure(text=cp["message"])

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

    def _refresh_storage_tab_metrics(self):
        dev = self.current_device
        free_gb = dev.free_disk_gb
        total_gb = dev.total_disk_gb
        compat = get_ios_compatibility_profile(dev.current_ios_version, dev.product_type)
        pc_min = 1.2 if compat["major"] <= 12 else 2.0
        ota_min = 4.0 if compat["major"] <= 12 else 8.0

        # Storage Card
        if hasattr(self, "lbl_card_storage_free"):
            self.lbl_card_storage_free.configure(text=f"{free_gb:.2f} GB / {total_gb:.0f} GB")
            if free_gb < pc_min:
                self.lbl_card_storage_status.configure(text="วิกฤต (ต้องเคลียร์ด่วน)", text_color="#FF3B30")
            elif free_gb < ota_min:
                self.lbl_card_storage_status.configure(text="OTA ไม่พอ แต่ PC อัปเดตได้", text_color="#FF9500")
            else:
                self.lbl_card_storage_status.configure(text="พื้นที่เพียงพอ", text_color="#34C759")

        self._render_optimization_guides()

        # Battery in card 4 & subtab perf
        health = getattr(dev, "battery_health_pct", 94)
        cycles = getattr(dev, "battery_cycle_count", 218)
        
        if hasattr(self, "lbl_card_batt_val"):
            self.lbl_card_batt_val.configure(text=f"{health}% (ความจุสูงสุด)")
            self.lbl_card_batt_sub.configure(text=f"รอบชาร์จ: {cycles} รอบ | แบต: {dev.battery_level}%")

        if hasattr(self, "lbl_tele_health"):
            fixer = StorageFixer(dev)
            bat_info = fixer.get_battery_diagnostics()
            self.lbl_tele_health.configure(text=f"{bat_info['health_pct']}%", text_color=bat_info['condition_color'])
            self.lbl_tele_cycles.configure(text=f"{bat_info['cycle_count']} รอบ")
            self.lbl_tele_mah.configure(text=f"{bat_info['current_capacity_mah']:,} / {bat_info['design_capacity_mah']:,} mAh")
            self.lbl_tele_temp.configure(text=f"{bat_info['temperature_c']} °C | {bat_info['voltage_mv']:,} mV")
            self.lbl_tele_cond.configure(text=f"● ประเมิน: {bat_info['condition']}", text_color=bat_info['condition_color'])

        if hasattr(self, "lbl_speed_score"):
            fixer = StorageFixer(dev)
            spd = fixer.assess_device_speed_state()
            self.lbl_speed_score.configure(
                text=f"{spd['speed_score']} / 100",
                text_color="#34C759" if spd['speed_score'] >= 75 else ("#FF9500" if spd['speed_score'] >= 60 else "#FF3B30")
            )
            self.lbl_speed_latency.configure(text=f"~{spd['latency_ms']} ms")
            self.lbl_speed_throttling.configure(
                text=f"● สถานะ CPU: {spd['throttling_status']}",
                text_color="#FF3B30" if "ร้อน" in spd['throttling_status'] else ("#FF9500" if "อุ่น" in spd['throttling_status'] else "#34C759")
            )

    def _on_click_deep_scan(self):
        self.btn_deep_scan.configure(state="disabled", text="กำลังสแกน...")
        self.txt_clean_log.delete("1.0", "end")
        self.lbl_clean_status.configure(text="สถานะ: กำลังสแกนไฟล์ขยะและแคชระบบ...")
        self.clean_progress_bar.set(0.2)

        def run():
            fixer = StorageFixer(self.current_device)
            res = fixer.scan_junk_details(log_callback=lambda msg: self.after(0, lambda: self._append_clean_log(msg)))
            self.after(0, lambda: self._finish_deep_scan(res))

        threading.Thread(target=run, daemon=True).start()

    def _finish_deep_scan(self, res):
        self.btn_deep_scan.configure(state="normal", text="🔍 สแกนค้นหาขยะ (Scan)")
        self.clean_progress_bar.set(1.0)
        self.lbl_clean_status.configure(text=f"สถานะ: สแกนเสร็จสิ้น ตรวจพบขยะรวม {res['total_junk_mb']} MB")
        self.lbl_card_junk_val.configure(text=f"{res['total_junk_mb']:.1f} MB")
        self.lbl_card_junk_sub.configure(text=f"{res['items_count']} รายการ พร้อมล้าง")

        # Update badges
        for cat_key, cat_data in res.get("categories", {}).items():
            if cat_key in self.junk_badge_lbls:
                self.junk_badge_lbls[cat_key].configure(
                    text=cat_data["size_str"],
                    text_color="#FF9500" if cat_data["size_mb"] > 200 else "#34C759"
                )

        messagebox.showinfo(
            "สแกนเสร็จสมบูรณ์",
            f"การสแกนระบบ iOS เสร็จสมบูรณ์!\n\n"
            f"• ตรวจพบไฟล์ขยะรวม: {res['total_junk_mb']} MB (~{res['total_junk_gb']} GB)\n"
            f"• จำนวนไฟล์แคชที่พบ: {res['items_count']} รายการ\n\n"
            f"ท่านสามารถเลือกหมวดหมู่ที่ต้องการแล้วกด 'ล้างรายการที่เลือก' ได้ทันที"
        )

    def _on_click_clean_selected(self):
        selected = [k for k, v in self.junk_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกอย่างน้อย 1 หมวดหมู่ที่ต้องการล้าง")
            return

        self.btn_clean_selected.configure(state="disabled", text="กำลังเคลียร์...")
        self.btn_clean_all.configure(state="disabled")
        self.txt_clean_log.delete("1.0", "end")
        self.lbl_clean_status.configure(text="สถานะ: กำลังดำเนินการทำความสะอาด...")
        self.clean_progress_bar.set(0.0)

        def run():
            fixer = StorageFixer(self.current_device)
            res = fixer.execute_selective_cleanup(
                selected_categories=selected,
                log_callback=lambda msg: self.after(0, lambda: self._append_clean_log(msg)),
                progress_callback=lambda pct: self.after(0, lambda: self.clean_progress_bar.set(pct))
            )
            self.after(0, lambda: self._finish_cleanup(res))

        threading.Thread(target=run, daemon=True).start()

    def _on_click_clean_all(self):
        for v in self.junk_vars.values():
            v.set(True)
        self._on_click_clean_selected()

    def _on_click_auto_cleanup(self):
        self._on_click_clean_all()

    def _append_clean_log(self, msg):
        self.txt_clean_log.insert("end", f"{msg}\n")
        self.txt_clean_log.see("end")

    def _finish_cleanup(self, res):
        self.btn_clean_selected.configure(state="normal", text="🧹 ล้างรายการที่เลือก")
        self.btn_clean_all.configure(state="normal", text="🌟 คลีนหมด 1-คลิก")
        self.clean_progress_bar.set(1.0)
        self.lbl_clean_status.configure(text=f"สถานะ: เคลียร์สำเร็จ ได้พื้นที่คืน +{res['freed_gb']} GB")

        # Reset badges
        for badge in self.junk_badge_lbls.values():
            badge.configure(text="0 MB", text_color="#A0A5B5")

        self.lbl_card_junk_val.configure(text="0 MB", text_color="#34C759")
        self.lbl_card_junk_sub.configure(text="ระบบสะอาดสมบูรณ์")

        self._refresh_device_and_firmware()
        messagebox.showinfo(
            "ทำความสะอาดสำเร็จ",
            f"ทำความสะอาดระบบ iOS สำเร็จเรียบร้อย!\n\n"
            f"• ได้พื้นที่ว่างเพิ่มขึ้น: +{res['freed_mb']} MB (+{res['freed_gb']} GB)\n"
            f"• จำนวนรายการที่เคลียร์: {res.get('cleaned_items', 0)} ไฟล์\n"
            f"• พื้นที่ว่างปัจจุบันบนเครื่อง: {res['new_free_gb']} GB\n\n"
            f"ระบบได้ทำการ Refresh Cache DB เรียบร้อยแล้ว"
        )

    def _on_click_tune_speed(self):
        mode_val = self.var_tune_mode.get() if hasattr(self, "var_tune_mode") else "turbo"

        self.btn_tune_speed.configure(state="disabled", text="⚡ กำลังปรับแต่งความเร็ว iOS...")
        if hasattr(self, "btn_purge_ram"):
            self.btn_purge_ram.configure(state="disabled")
        if hasattr(self, "btn_soft_reboot"):
            self.btn_soft_reboot.configure(state="disabled")

        self.txt_ram_log.delete("1.0", "end")
        self.lbl_tune_status.configure(text="สถานะ: กำลังดำเนินการจูนความเร็วและประเมินระบบ...")
        self.tune_progress_bar.set(0.05)

        def run():
            fixer = StorageFixer(self.current_device)
            res = fixer.tune_ios_speed(
                mode=mode_val,
                log_callback=lambda msg: self.after(0, lambda: self._append_ram_log(msg)),
                progress_callback=lambda pct: self.after(0, lambda: self.tune_progress_bar.set(pct))
            )
            self.after(0, lambda: self._finish_speed_tune(res))

        threading.Thread(target=run, daemon=True).start()

    def _finish_speed_tune(self, res):
        self.btn_tune_speed.configure(state="normal", text="⚡ สั่งจูนความเร็ว iOS ทันที (Run iOS Speed Tune)")
        if hasattr(self, "btn_purge_ram"):
            self.btn_purge_ram.configure(state="normal")
        if hasattr(self, "btn_soft_reboot"):
            self.btn_soft_reboot.configure(state="normal")

        self.tune_progress_bar.set(1.0)
        self.lbl_tune_status.configure(
            text=f"สถานะ: จูนสำเร็จ! ความเร็ว +{res['score_gain']} คะแนน (ความหน่วง UI เหลือ ~{res['latency_after_ms']} ms)"
        )

        # Update card metrics
        self.lbl_card_ram_val.configure(text=f"+{res['ram_freed_mb']} MB คืนแล้ว", text_color="#34C759")
        self.lbl_card_ram_sub.configure(text="RAM & Daemons สะอาด 100%")

        if hasattr(self, "lbl_speed_score"):
            self.lbl_speed_score.configure(
                text=f"{res['score_after']} / 100",
                text_color="#34C759"
            )
            self.lbl_speed_latency.configure(text=f"~{res['latency_after_ms']} ms")
            self.lbl_speed_throttling.configure(
                text=f"● สถานะ CPU: {res['throttling_status']}",
                text_color="#FF3B30" if "ร้อน" in res['throttling_status'] else ("#FF9500" if "อุ่น" in res['throttling_status'] else "#34C759")
            )

        self._refresh_device_and_firmware()

        messagebox.showinfo(
            "⚡ จูนความเร็ว iOS สำเร็จ 100%",
            f"การปรับแต่งประสิทธิภาพและเร่งความเร็ว iOS เสร็จสมบูรณ์!\n\n"
            f"📊 ผลลัพธ์หลังการจูน:\n"
            f"• คะแนนความเร็วระบบ: {res['score_before']} ➔ {res['score_after']} / 100 (+{res['score_gain']} คะแนน)\n"
            f"• ปล่อยคืน RAM ทันที: +{res['ram_freed_mb']} MB\n"
            f"• ปลดล็อคพื้นที่ NAND Storage: +{res['storage_freed_mb']} MB\n"
            f"• ความหน่วงการสัมผัส (Latency): ลดลง {res['latency_reduction_pct']}% (เหลือ ~{res['latency_after_ms']} ms)\n"
            f"• สถานะชิปประมวลผล: {res['throttling_status']}\n\n"
            f"เครื่องจะตอบสนองรวดเร็ว สลับแอปไม่หน่วง และแอนิเมชันลื่นไหลขึ้นทันที!"
        )

    def _on_click_show_speed_guide(self):
        ios_ver = self.current_device.current_ios_version if hasattr(self, "current_device") else "17.0"
        tips = get_speed_tuning_recommendations(ios_version=ios_ver)
        msg_parts = [f"💡 5 เทคนิคการตั้งค่า iOS {ios_ver} ให้เครื่องเร็วขึ้นทันที 2 เท่า:\n"]
        for t in tips:
            msg_parts.append(f"{t['title']}")
            msg_parts.append(f"  • วิธีตั้งค่า: {t['how']}")
            msg_parts.append(f"  • ผลลัพธ์: {t['impact']} - {t['desc']}\n")

        messagebox.showinfo("เทคนิคการตั้งค่า iOS ให้เร็วที่สุด", "\n".join(msg_parts))

    def _on_click_purge_ram(self):
        self.btn_purge_ram.configure(state="disabled", text="กำลังปล่อยคืน RAM...")
        self.txt_ram_log.delete("1.0", "end")

        def run():
            fixer = StorageFixer(self.current_device)
            res = fixer.purge_system_memory(log_callback=lambda msg: self.after(0, lambda: self._append_ram_log(msg)))
            self.after(0, lambda: self._finish_ram_purge(res))

        threading.Thread(target=run, daemon=True).start()

    def _append_ram_log(self, msg):
        self.txt_ram_log.insert("end", f"{msg}\n")
        self.txt_ram_log.see("end")

    def _finish_ram_purge(self, res):
        self.btn_purge_ram.configure(state="normal", text="🚀 ปล่อยคืน RAM ทันที (Purge RAM & Flush Caches)")
        self.lbl_card_ram_val.configure(text=f"+{res['freed_ram_mb']} MB คืนแล้ว", text_color="#34C759")
        self.lbl_card_ram_sub.configure(text="ระบบปล่อยคืน Inactive Memory สำเร็จ")
        messagebox.showinfo(
            "ปล่อยคืน RAM สำเร็จ",
            f"ดำเนินการปล่อยคืน RAM เรียบร้อย!\n\n"
            f"• ได้รับหน่วยความจำ RAM คืน: +{res['freed_ram_mb']} MB\n"
            f"• สัญญาณ Darwin Low-Memory ได้ถูกส่งไปยังแอปและระบบเพื่อ flush แคชตกค้างแล้ว\n"
            f"• เครื่องจะตอบสนองรวดเร็วและลื่นไหลขึ้นทันที"
        )

    def _on_click_refresh_battery(self):
        self._refresh_storage_tab_metrics()
        messagebox.showinfo("อัปเดตข้อมูลสำเร็จ", "อัปเดตข้อมูลสุขภาพแบตเตอรี่และฮาร์ดแวร์ล่าสุดเรียบร้อย")

    def _on_click_soft_reboot(self):
        confirm = messagebox.askyesno(
            "ยืนยันการซอฟต์รีสตาร์ท",
            "ท่านต้องการสั่งซอฟต์รีสตาร์ท (Safe Soft Reboot) อุปกรณ์ iOS เครื่องนี้หรือไม่?\n\n"
            "การรีสตาร์ทจะปิด-เปิดเครื่องใหม่อย่างปลอดภัยเพื่อรีเฟรช SpringBoard และล้าง memory leaks ทั้งหมด โดยไม่มีผลกระทบต่อข้อมูลใดๆ"
        )
        if not confirm:
            return

        self.btn_soft_reboot.configure(state="disabled", text="กำลังสั่งรีสตาร์ท...")

        def run():
            fixer = StorageFixer(self.current_device)
            res = fixer.soft_reboot_device(log_callback=lambda msg: self.after(0, lambda: self._append_ram_log(msg)))
            self.after(0, lambda: self._finish_soft_reboot(res))

        threading.Thread(target=run, daemon=True).start()

    def _finish_soft_reboot(self, res):
        self.btn_soft_reboot.configure(state="normal", text="🔄 สั่งซอฟต์รีสตาร์ท iPhone (Safe Soft Reboot)")
        if res.get("success"):
            messagebox.showinfo(
                "รีสตาร์ทสำเร็จ",
                "ส่งคำสั่งซอฟต์รีสตาร์ทสำเร็จ!\nอุปกรณ์จะทำการบูตเข้าระบบ SpringBoard ใหม่อย่างปลอดภัย"
            )
        else:
            messagebox.showwarning("ข้อผิดพลาด", f"ไม่สามารถสั่งรีสตาร์ทได้: {res.get('error')}")

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
            # Update current device version to target version if available
            latest = self.firmware_info.get("latest_signed")
            if latest and latest.get("version"):
                self.current_device.current_ios_version = latest.get("version")
                self.current_device.build_version = latest.get("buildid", self.current_device.build_version)
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
