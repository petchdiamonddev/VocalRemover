# VocalRemover

โปรแกรมบรรทัดคำสั่งสำหรับดาวน์โหลดเสียงจาก YouTube แล้วแยกออกเป็น 2 ไฟล์:

- `vocals.wav` — เสียงร้อง
- `instrumental.wav` — เสียงดนตรีที่ตัดเสียงร้องออกแล้ว

เหมาะสำหรับทำไฟล์คาราโอเกะหรือฝึกฟังเสียงดนตรี โดยใช้ Demucs ช่วยแยกเสียง

## สิ่งที่ต้องมี

- Windows 10 หรือใหม่กว่า
- Python 3.10 ขึ้นไป
- ffmpeg
- อินเทอร์เน็ตสำหรับดาวน์โหลดเพลงและโมเดลครั้งแรก

ถ้าใช้ชุดที่ติดตั้งไว้ในโปรเจกต์นี้ ไม่ต้องตั้งค่าอะไรเพิ่ม เพราะมี `.venv` และ ffmpeg ติดตั้งไว้แล้ว

## วิธีใช้งานแบบง่าย

เปิด PowerShell แล้วพิมพ์:

```powershell
cd D:\work\VocalRemover
.\run.ps1
```

โปรแกรมจะถามว่า:

```text
วางลิงก์เพลงจาก YouTube:
```

นำลิงก์เพลงจาก YouTube มาวาง แล้วกด Enter ได้เลย

เมื่อทำเสร็จแล้ว ให้เปิดโฟลเดอร์ `outputs` จะพบโฟลเดอร์ของเพลงนั้น ภายในมีไฟล์เสียงร้องและเสียงดนตรีแยกกัน

## ใช้คำสั่ง Python โดยตรง

```powershell
cd D:\work\VocalRemover
.\.venv\Scripts\Activate.ps1
python vocal_remover.py
```

หรือใส่ลิงก์ไปพร้อมคำสั่งก็ได้:

```powershell
python vocal_remover.py "https://www.youtube.com/watch?v=..."
```

ถ้าใส่ลิงก์ผิด โปรแกรมจะบอกให้ลองใหม่ และจะยังไม่เริ่มดาวน์โหลดจนกว่าจะได้ลิงก์ YouTube ที่ถูกต้อง

## ตัวเลือกเพิ่มเติม

กำหนดโฟลเดอร์เก็บผลลัพธ์เอง:

```powershell
python vocal_remover.py "ลิงก์เพลง" --output results
```

เก็บไฟล์เสียงต้นฉบับไว้ด้วย:

```powershell
python vocal_remover.py "ลิงก์เพลง" --keep-source
```

ถ้ามีการ์ดจอ NVIDIA และติดตั้ง PyTorch รุ่น CUDA แล้ว สามารถใช้การ์ดจอช่วยประมวลผลได้:

```powershell
python vocal_remover.py "ลิงก์เพลง" --device cuda
```

ถ้าไม่แน่ใจ ให้ใช้ค่าเริ่มต้น `cpu` ได้เลย เพียงแต่อาจใช้เวลานานกว่า

## ติดตั้งใหม่ด้วยตัวเอง

ถ้ายังไม่มี virtual environment ให้เปิด PowerShell ในโฟลเดอร์โปรเจกต์แล้วใช้คำสั่งนี้:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## หมายเหตุ

ใช้กับเพลงและวิดีโอที่คุณมีสิทธิ์ดาวน์โหลดและใช้งานเท่านั้น รวมถึงปฏิบัติตามกฎของ YouTube และกฎหมายลิขสิทธิ์ในพื้นที่ของคุณ
