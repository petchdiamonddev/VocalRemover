# VocalRemover

โปรแกรมบรรทัดคำสั่งสำหรับดาวน์โหลดเสียงจาก YouTube แยกเสียงร้อง/ดนตรีด้วย Demucs และนำเข้า BandLab Studio ให้อัตโนมัติ

- `instrumental.wav` — เสียงดนตรีที่ตัดเสียงร้องออกแล้ว
- `vocals.wav` — เสียงร้องต้นฉบับ
- นำชื่อคลิปจาก YouTube มาตั้งเป็นชื่อโฟลเดอร์ผลลัพธ์ และตั้งเป็นชื่อเพลงบน BandLab
- นำเข้าทั้งไฟล์ดนตรีและเสียงร้องเข้าสู่ไทม์ไลน์ BandLab พร้อมบันทึกโปรเจกต์อัตโนมัติ

## สิ่งที่ต้องมี

- Windows 10 หรือใหม่กว่า
- Python 3.10 ขึ้นไป
- ffmpeg
- บัญชี BandLab (เข้าสู่ระบบครั้งแรกครั้งเดียว ระบบจะจำไว้สำหรับครั้งถัดไป)

## วิธีใช้งาน

เปิด PowerShell แล้วพิมพ์:

```powershell
cd D:\work\VocalRemover
.\run.ps1
```

หรือระบุลิงก์เพลง:

```powershell
.\run.ps1 "https://www.youtube.com/watch?v=..."
```

เมื่อทำงานเสร็จ โปรแกรมจะ:
1. แยกไฟล์เสียงเก็บไว้ในโฟลเดอร์ `outputs/<ชื่อคลิป>/`
2. เคลียร์โฟลเดอร์ชั่วคราวออกทั้งหมด
3. เปิดเบราว์เซอร์ BandLab Studio สร้างโปรเจกต์ใหม่ตามชื่อเพลง
4. นำเข้าแทร็กดนตรีและแทร็กเสียงร้องเข้าสู่ไทม์ไลน์ และบันทึกให้อัตโนมัติ

## ตัวเลือกเพิ่มเติม

หากต้องการแยกเสียงอย่างเดียว โดยไม่ต้องนำเข้า BandLab:

```powershell
.\run.ps1 "ลิงก์เพลง" --no-bandlab
```

หรือใช้ python โดยตรง:

```powershell
python vocal_remover.py "ลิงก์เพลง" --no-bandlab
```

กำหนดโฟลเดอร์ผลลัพธ์เอง:

```powershell
python vocal_remover.py "ลิงก์เพลง" --output results
```

เก็บไฟล์เสียงต้นฉบับไว้ด้วย:

```powershell
python vocal_remover.py "ลิงก์เพลง" --keep-source
```

ใช้การ์ดจอ NVIDIA (CUDA):

```powershell
python vocal_remover.py "ลิงก์เพลง" --device cuda
```
