# 🍎 iOS Smart Update & Storage Optimizer (Windows Desktop Edition)

โปรแกรม Windows Desktop Application (.EXE) แบบครบวงจร สำหรับตรวจสอบเวอร์ชัน iOS, ประเมินความพร้อมก่อนอัปเดต, **แก้ไขปัญหาพื้นที่จัดเก็บไม่เพียงพอ**, และดำเนินการอัปเดตหรือกู้คืนระบบ iOS อย่างปลอดภัย

---

## 🌟 คุณสมบัติเด่น (Key Features)

### 1. 📱 ตรวจสอบเครื่องและเวอร์ชัน iOS (Device & Firmware Check)
- **สแกนอุปกรณ์ผ่าน USB จริง (Live USB Detection)**: ตรวจจับ iPhone/iPad อัตโนมัติผ่าน Apple Lockdown และ USBMuxd service แสดงข้อมูล Device Name, Product Type, Serial Number, เลขเวอร์ชันปัจจุบัน, สถานะแบตเตอรี่ และพื้นที่ความจุ
- **โหมดจำลองสถานการณ์ (Simulated Mode)**: มีพรีเซ็ตอุปกรณ์ยอดนิยม (iPhone 11 ถึง iPhone 16 Pro Max, iPad) ให้ทดลองประเมินและทดสอบระบบได้ทันทีแม้ยังไม่ได้เสียบ iPhone จริง
- **ตรวจเช็คเวอร์ชันใหม่จาก Apple Server**: ดึงข้อมูลอัปเดตล่าสุดและสถานะการลงนามรับรอง (**Apple TSS Signing**) แบบ Real-time ผ่าน Apple IPSW API

---

### 2. 📋 ระบบประเมินความพร้อมก่อนอัปเดต (Pre-Update Assessment & Risk Scoring)
ระบบจะทำการคำนวณและประเมินความเสี่ยงออกเป็นคะแนนความพร้อม **(0 - 100 คะแนน)** ผ่าน 4 มิติสำคัญ:
1. **การประเมินพื้นที่จัดเก็บ (Storage Analysis)**: เปรียบเทียบพื้นที่ว่างจริงกับความต้องการแบบ OTA (12-16 GB) และแบบ PC Update (1.5-2.0 GB)
2. **การประเมินแบตเตอรี่ (Power Check)**: ตรวจสอบระดับแบตเตอรี่ (แนะนำ ≥ 50%) ป้องกันเครื่องดับขณะกำลังเขียนข้อมูล NAND
3. **การตรวจสอบการรับรองเฟิร์มแวร์ (Apple TSS Signing Check)**: ยืนยันว่า Apple ยังเปิด Signed เวอร์ชันเป้าหมายอยู่ เพื่อป้องกันข้อผิดพลาด Error 3194
4. **การประเมินพื้นที่คอมพิวเตอร์ (Host PC Storage)**: ตรวจสอบพื้นที่ฮาร์ดดิสก์ของคอมพิวเตอร์ Windows ว่ามีว่างอย่างน้อย 15 GB เพื่อดาวน์โหลดและแตกไฟล์ IPSW

---

### 3. 🧹 นวัตกรรมการแก้ไขปัญหา "พื้นที่ไม่พอ" แล้วจึงอัปเดต (Storage Optimization Engine)
ทำไม iPhone ถึงแจ้งเตือนว่า *"พื้นที่ไม่พอสำหรับอัปเดต iOS"*?
- เมื่ออัปเดตผ่านเมนู Settings ในเครื่อง (OTA): ตัวเครื่องต้องดาวน์โหลดไฟล์ระบบและแตกไฟล์บนความจุของ iPhone ทำให้ต้องการพื้นที่ว่างมหาศาล (12 - 16 GB)
- **วิธีแก้ปัญหาของโปรแกรมนี้ (PC Tethered Staging)**:
  - โปรแกรมจะดาวน์โหลดและแตกไฟล์ IPSW บน **ฮาร์ดดิสก์ของคอมพิวเตอร์ Windows**
  - จากนั้นสตรีมบล็อกข้อมูลเข้า iPhone โดยตรงผ่านสาย USB
  - ทำให้ iPhone **ต้องการพื้นที่ชั่วคราวเพียง ~1.5 - 2.0 GB เท่านั้น** แก้ปัญหาพื้นที่ไม่พอได้ 90% ทันที **โดยไม่ต้องลบรูปภาพหรือข้อมูลส่วนตัวใดๆ!**
- **เครื่องมือล้างขยะระบบอัตโนมัติ (Automated System Cleanup)**:
  - สั่งลบไฟล์ Crash Reports (`.ips`), Sysdiagnose, และแคชข้อผิดพลาดของระบบที่ค้างอยู่ในตัวเครื่อง
  - คืนพื้นที่ว่างทันที 350 MB - 1.5 GB
- **คู่มือแนะนำการกู้คืนพื้นที่ขนาดใหญ่ (High Impact Space Recovery)**:
  - ล้างอัลบั้ม *"ที่เพิ่งลบล่าสุด"* (Recently Deleted) คืนพื้นที่ 2 - 15 GB
  - แนะนำการ *"เอาแอปที่ไม่ได้ใช้ออก"* (Offload Unused Apps) โดยข้อมูลเซฟและเอกสารยังอยู่ครบ คืนพื้นที่ 5 - 20 GB

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
