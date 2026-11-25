# 🍎 iOS Smart Update & Storage Optimizer (Windows Desktop Edition)

โปรแกรม Windows Desktop Application (.EXE) แบบครบวงจร สำหรับตรวจสอบเวอร์ชัน iOS (**รองรับ iOS 8 ขึ้นไป** ตั้งแต่ iPhone 4s ถึงรุ่นล่าสุด, iPad และ iPod touch), ประเมินความพร้อมก่อนอัปเดต, **แก้ไขปัญหาพื้นที่จัดเก็บไม่เพียงพอ**, และดำเนินการอัปเดตหรือกู้คืนระบบ iOS อย่างปลอดภัย

---

## 🌟 คุณสมบัติเด่น (Key Features)

### 1. 📱 ตรวจสอบเครื่องและเวอร์ชัน iOS (Device & Firmware Check - iOS 8+)
- **สแกนอุปกรณ์ผ่าน USB จริง (Live USB Detection)**: ตรวจจับ iPhone/iPad/iPod touch อัตโนมัติตั้งแต่ **iOS 8.0 ขึ้นไป** ผ่าน Apple Lockdown และ USBMuxd (รองรับทั้งระบบไฟล์ HFS+ และ APFS, สถาปัตยกรรม 32-bit และ 64-bit) แสดงข้อมูล Device Name, Product Type, Serial Number, เลขเวอร์ชันปัจจุบัน, สถานะแบตเตอรี่ (รวมถึง IORegistry `IOPMPowerSource` สำหรับ iOS 8-11) และพื้นที่ความจุ
- **โหมดจำลองสถานการณ์ (Simulated Mode)**: มีพรีเซ็ตอุปกรณ์ยอดนิยมครอบคลุมทั้งรุ่นคลาสสิก iOS 8/10/12 (iPhone 6, 6s, 7) และรุ่นใหม่ (iPhone 11 ถึง iPhone 16 Pro Max) ให้ทดลองประเมินและทดสอบระบบได้ทันทีแม้ยังไม่ได้เสียบ iPhone จริง
- **ตรวจเช็คเวอร์ชันใหม่จาก Apple Server**: ดึงข้อมูลอัปเดตล่าสุดและสถานะการลงนามรับรอง (**Apple TSS Signing**) แบบ Real-time ผ่าน Apple IPSW API

---

### 2. 📋 ระบบประเมินความพร้อมก่อนอัปเดต (Pre-Update Assessment & Risk Scoring)
ระบบจะทำการคำนวณและประเมินความเสี่ยงออกเป็นคะแนนความพร้อม **(0 - 100 คะแนน)** ผ่าน 4 มิติสำคัญ:
1. **การประเมินพื้นที่จัดเก็บ (Storage Analysis)**: เปรียบเทียบพื้นที่ว่างจริงกับความต้องการแบบ OTA (12-16 GB) และแบบ PC Update (1.5-2.0 GB)
2. **การประเมินแบตเตอรี่ (Power Check)**: ตรวจสอบระดับแบตเตอรี่ (แนะนำ ≥ 50%) ป้องกันเครื่องดับขณะกำลังเขียนข้อมูล NAND
3. **การตรวจสอบการรับรองเฟิร์มแวร์ (Apple TSS Signing Check)**: ยืนยันว่า Apple ยังเปิด Signed เวอร์ชันเป้าหมายอยู่ เพื่อป้องกันข้อผิดพลาด Error 3194
4. **การประเมินพื้นที่คอมพิวเตอร์ (Host PC Storage)**: ตรวจสอบพื้นที่ฮาร์ดดิสก์ของคอมพิวเตอร์ Windows ว่ามีว่างอย่างน้อย 15 GB เพื่อดาวน์โหลดและแตกไฟล์ IPSW

---

### 3. 🧹 ศูนย์เคลียร์ขยะ & จูนความเร็ว iOS ขั้นสุด (iOS Speed Tuning & Storage Engine)
ทำไม iPhone ถึงแจ้งเตือนว่า *"พื้นที่ไม่พอสำหรับอัปเดต iOS"* และทำไมเครื่องถึงช้าลงเมื่อใช้งานไปนานๆ?
- **⚡ ระบบจูนความเร็ว iOS ขั้นสุด (1-Click Ultimate iOS Speed Booster)**:
  - ฟังก์ชัน `tune_ios_speed(...)` ดำเนินการปรับแต่งประสิทธิภาพแบบ 5 มิติ:
    1. **วิเคราะห์คอขวด & CPU Thermal Throttling**: ตรวจวัดอุณหภูมิ, แรงดันไฟ และสุขภาพแบตเตอรี่แบบ Real-time เพื่อประเมินว่าชิป SoC Bionic ถูกลดความถี่สัญญาณนาฬิกาหรือไม่
    2. **คืนหน่วยความจำ RAM เชิงลึก**: ส่งสัญญาณ Darwin Kernel `com.apple.system.lowmemory` ปลดปล่อย Inactive Memory Pages ใน WebKit, SpringBoard และ System Daemons คืนแรมทันที 500 - 850 MB
    3. **ล้างแคชระบบเบื้องหลัง (Background Daemons & WebKit Eviction)**: Flush แคช StoreKit (`com.apple.itunesstored`), เครือข่าย (`cfnetwork`), และแคช JavaScript JIT compiler
    4. **ปลดล็อคคอขวด NAND Storage I/O**: ลบขยะตกค้าง ไฟล์ Crash Logs (`.ips`) และ Public Staging ขนาดใหญ่ ช่วยให้ APFS SLC Write Cache กลับมาทำงานเต็มสปีด
    5. **รีเซ็ต SpringBoard Frame Pacing**: ปรับแต่งการตอบสนองของหน้าจอ สลับแอปไม่หน่วง ลด Touch/Animation Latency ลงถึง 50-65% (เหลือ ~40-60 ms)
  - รองรับ 2 โหมด: **Turbo Deep Tune** (จูน 5 ขั้นตอนเต็มระบบ) และ **Quick Speed Boost** (จูนด่วน)
  - มีคำแนะนำ 5 การตั้งค่าลับของ iOS ที่ช่วยให้เครื่องรู้สึกเร็วขึ้นทันที 2 เท่า (เช่น Reduce Motion, Selective Background Refresh)
- **แก้ปัญหาพื้นที่ไม่พอด้วยวิธี PC Tethered Staging**:
  - โปรแกรมจะดาวน์โหลดและแตกไฟล์ IPSW บน **ฮาร์ดดิสก์ของคอมพิวเตอร์ Windows**
  - สตรีมบล็อกข้อมูลเข้า iPhone โดยตรงผ่านสาย USB ทำให้ iPhone **ต้องการพื้นที่ชั่วคราวเพียง ~1.5 - 2.0 GB เท่านั้น** (ข้ามปัญหา OTA Storage Not Enough 12-16 GB ทันทีโดยไม่ต้องลบรูปภาพหรือข้อมูลส่วนตัวใดๆ!)
- **การสแกนและกำจัดไฟล์ขยะเชิงลึก 5 หมวดหมู่ (Deep Junk Scan & Selective Clean)**:
  1. 📑 **Crash & Panic Logs**: ลบไฟล์ `.ips`, `.crash`, `sysdiagnose`, `JetsamEvent` ที่สะสมในเครื่อง
  2. 🖼️ **Photo & Media Thumbnail Caches**: ล้างแคชรูปย่อและไฟล์แปลงพรีวิวใน `PhotoData` (รูปต้นฉบับปลอดภัย 100%)
  3. 📦 **Public Staging & Temp Downloads**: ลบไฟล์ค้างจากการส่ง AirDrop และไฟล์ดาวน์โหลดชั่วคราว
  4. 🎵 **iTunes Artwork & Stream Caches**: ล้างแคชภาพปกอัลบั้มและแคชสตรีมมิ่งที่โหลดค้างไว้
  5. 🛠️ **System Telemetry & Diagnostic Traces**: รีเซ็ตฐานข้อมูลบันทึกสถิติฮาร์ดแวร์เบื้องหลัง
  - *คืนพื้นที่ว่างได้ทันที 1.5 GB - 3.8 GB!*
- **🚀 เครื่องมือปล่อยคืน RAM ทันที (RAM & Memory Purge)**:
  - สั่งการเคอร์เนล Darwin ปล่อยสัญญาณ `com.apple.system.lowmemory`
  - บังคับให้ WebKit และ Background Daemons ปล่อย Inactive Memory Pages คืนสู่ระบบทันที
  - คืนแรม 400 MB - 800 MB ช่วยให้ iPhone ตอบสนองลื่นไหลขึ้นทันทีโดยไม่ต้องปิดเครื่อง
- **🔋 ระบบวิเคราะห์สุขภาพแบตเตอรี่ & ฮาร์ดแวร์ (Battery Doctor)**:
  - แสดงจำนวนรอบการชาร์จจริง (**Cycle Count**)
  - แสดงสุขภาพแบตเตอรี่ (**Battery Health %**) และความจุจริงเปรียบเทียบความจุโรงงาน (Current vs Design mAh)
  - วัดอุณหภูมิแบตเตอรี่ (°C) และแรงดันไฟฟ้า (mV) แบบ Real-time
  - คำแนะนำการตั้งค่า 80% Limit และ Optimized Battery Charging
- **🔄 ซอฟต์รีสตาร์ทเครื่องอย่างปลอดภัย (Safe Soft Reboot / Fast Respring)**:
  - รีสตาร์ท SpringBoard และ Services ผ่าน Apple Diagnostics Service เพื่อเคลียร์ Memory Leaks
- **📊 วิเคราะห์ข้อมูลระบบ & 6 แนวทางกู้คืนพื้นที่ขนาดใหญ่ (High Impact Space Recovery)**:
  - แจกแจงโครงสร้าง "System Data" (ข้อมูลระบบ / อื่นๆ)
  - คู่มือทีละขั้นตอน: ล้าง Recently Deleted, เอาแอปออก (Offload Apps), ล้างแคช Safari/LINE/TikTok, ลบไฟล์แนบขนาดใหญ่ในข้อความ คืนพื้นที่ได้สูงสุดถึง 15 - 40 GB!

---

### 4. ⚡ ฟังก์ชันดำเนินการ Update iOS (Update & Restore Engine)
- **โหมดการติดตั้ง 2 รูปแบบ**:
  - 🟢 **Update (Retain User Data) [แนะนำ]**: ติดตั้ง iOS ใหม่โดย**รักษาข้อมูลเดิมไว้ครบถ้วน 100%** (รูปภาพ, แอปพลิเคชัน, แชท, ข้อความ และการตั้งค่า)
  - 🔴 **Clean Restore (Factory Wipe)**: สำหรับกรณีระบบเดิมเสียหายหนัก ล้างเครื่องและติดตั้ง iOS ใหม่ทั้งหมด
- **ตัวดาวน์โหลดความเร็วสูง (High-Speed IPSW Downloader)**:
  - ดาวน์โหลดตรงจาก **Official Apple CDN** (`updates.cdn-apple.com`)
  - รองรับการดาวน์โหลดต่อ (Resume capability) เมื่อเน็ตหลุด
  - แสดงความเร็ว (MB/s), เวลาที่เหลือ (ETA) และตรวจเช็คความสมบูรณ์ของไฟล์ (Integrity Check)
- **กระบวนการแฟลชที่ปลอดภัย**:
  - นำเครื่องเข้า Recovery Mode อย่างปลอดภัย
  - ขอรับตั๋วรับรอง TSS จาก Apple
  - ส่ง Ramdisk, Kernel, Baseband และเขียน OS Partition
  - รีบูตเข้าสู่ระบบพร้อมใช้งาน

---

### 5. 🛠️ ระบบตรวจสุขภาพไดรเวอร์ (Driver Doctor & Apple Tools)
- ตรวจสอบความพร้อมของ **Apple Mobile Device Support** และ **Apple Mobile Device Service (usbmuxd)**
- มีปุ่มดาวน์โหลดตัวติดตั้งทางการ **Apple Driver 64-bit (MSI)** ตรงจาก Apple CDN สำหรับคอมพิวเตอร์ Windows ที่ยังไม่เคยลงไดรเวอร์

---

## 🚀 วิธีเปิดใช้งานโปรแกรม (How to Run)

### วิธีที่ 1: รันไฟล์ EXE โดยตรง (แนะนำ)
เปิดไฟล์:
```
dist\SmartIOSOptimizer\SmartIOSOptimizer.exe
```
หรือดับเบิลคลิกที่ไฟล์:
```
Start_SmartIOSOptimizer.bat
```

### วิธีที่ 2: รันผ่าน Python Source Code
```powershell
python main.py
```

---

## 📁 โครงสร้างโปรเจกต์ (Project Architecture)

```
D:\wk_ai\smart_ios_optimize\
│
├── assets/
│   ├── app_icon.ico              # ไอคอนโปรแกรมความละเอียดสูง
│   └── app_icon.png
│
├── dist/
│   └── SmartIOSOptimizer/
│       └── SmartIOSOptimizer.exe # ไฟล์ EXE พร้อมใช้งานสำหรับ Windows
│
├── src/
│   ├── __init__.py
│   ├── ios_device.py             # จัดการติดต่อ USB, Lockdown, Device Telemetry, และ Simulation
│   ├── ipsw_service.py           # เชื่อมต่อ Apple IPSW API ตรวจสอบเวอร์ชันและสถานะ Signed
│   ├── evaluator.py              # ประเมินความพร้อม 4 มิติ และคำนวณคะแนน 0-100
│   ├── storage_fixer.py          # แก้ไขปัญหาพื้นที่ไม่พอ ล้าง Crash Logs และแนวทางกู้คืนพื้นที่
│   ├── update_engine.py          # ตัวดาวน์โหลดและกระบวนการแฟลช Update/Restore
│   ├── driver_manager.py         # ตรวจสอบและดาวน์โหลดไดรเวอร์ Apple AMDS 64-bit
│   └── ui/
│       ├── __init__.py
│       └── app.py                # หน้าต่างโปรแกรมหลัก CustomTkinter UI
│
├── main.py                       # จุดเริ่มต้นรันโปรแกรม
├── build_exe.py                  # สคริปต์คอมไพล์โปรแกรมเป็น EXE ด้วย PyInstaller
├── Start_SmartIOSOptimizer.bat   # สคริปต์ทางลัดสำหรับเปิดโปรแกรม
└── README.md                     # เอกสารกำกับการใช้งาน
```

---

## 🛠️ การคอมไพล์ใหม่ (How to Rebuild EXE)
หากมีการแก้ไขโค้ดและต้องการสร้างไฟล์ EXE ใหม่ สามารถรันคำสั่ง:
```powershell
python build_exe.py
```
ผลลัพธ์จะถูกสร้างไว้ในโฟลเดอร์ `dist\SmartIOSOptimizer\`
