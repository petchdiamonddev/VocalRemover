from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


def sanitize_filename(name: str) -> str:
    """ตัดอักขระพิเศษที่ไม่รองรับในระบบปฏิบัติการ และป้องกัน Path Traversal"""
    clean = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "", name)
    clean = re.sub(r"\s+", " ", clean).strip().strip(".")
    reserved = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
        "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
        "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    if clean.upper() in reserved:
        clean = f"Track_{clean}"
    return clean or "Track"


def get_python_exe() -> str:
    """เลือกใช้ python จาก .venv ก่อนเพื่อความถูกต้องของสภาพแวดล้อม"""
    venv_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def download_audio(url: str, work_dir: Path) -> tuple[Path, str]:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise RuntimeError("ยังไม่ได้ติดตั้ง yt-dlp: pip install -r requirements.txt") from exc

    work_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(work_dir / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "") if info else ""
        downloaded = Path(ydl.prepare_filename(info))

    if not title:
        title = "Track"

    if downloaded.exists():
        return downloaded, title
    matches = list(work_dir.glob("source.*"))
    if not matches:
        raise RuntimeError("ดาวน์โหลดไฟล์เสียงไม่สำเร็จ")
    return matches[0], title


def run_demucs(source: Path, output_dir: Path, model: str, device: str) -> tuple[Path, Path]:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ไม่พบ ffmpeg ใน PATH กรุณาติดตั้ง ffmpeg ก่อน")

    command = [
        get_python_exe(), "-m", "demucs.separate", "-n", model,
        "-o", str(output_dir), "--two-stems=vocals",
    ]
    if device:
        command.extend(["-d", device])
    command.append(str(source))
    print("กำลังแยกเสียงด้วย Demucs...")
    subprocess.run(command, check=True)

    stem_dir = output_dir / model / source.stem
    vocals = stem_dir / "vocals.wav"
    instrumental = stem_dir / "no_vocals.wav"
    if not vocals.exists() or not instrumental.exists():
        raise RuntimeError(f"Demucs ทำงานเสร็จแต่ไม่พบไฟล์ผลลัพธ์ใน {stem_dir}")
    return vocals, instrumental


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ดาวน์โหลดเสียงจาก YouTube แล้วแยกเสียงร้อง/ดนตรีด้วย Demucs"
    )
    parser.add_argument("url", nargs="?", help="ลิงก์ YouTube (ถ้าไม่ใส่ โปรแกรมจะถามให้)")
    parser.add_argument("-o", "--output", default="outputs", help="โฟลเดอร์ผลลัพธ์ (default: outputs)")
    parser.add_argument("-m", "--model", default="htdemucs", help="Demucs model (default: htdemucs)")
    parser.add_argument("-d", "--device", default="cpu", help="cpu หรือ cuda (default: cpu)")
    parser.add_argument("--keep-source", action="store_true", help="เก็บไฟล์เสียงต้นฉบับไว้ด้วย")
    args = parser.parse_args()
    args.url = get_valid_url(args.url)
    return args


def get_valid_url(url: str | None) -> str:
    """รับและตรวจลิงก์ YouTube ก่อนเริ่มงาน ป้องกันการส่ง URL แปลกปลอม"""
    while True:
        if not url:
            try:
                url = input("วางลิงก์เพลงจาก YouTube: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nยกเลิกการทำงาน")
                sys.exit(130)
        parsed = urlparse(url)
        host = parsed.netloc.lower().split(":", 1)[0]
        valid_host = host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
        has_video = bool(parsed.path.strip("/") or parsed.query)
        if parsed.scheme in {"http", "https"} and valid_host and has_video:
            return url
        print("ลิงก์ไม่ถูกต้อง กรุณาใช้ลิงก์เพลงจาก YouTube เช่น https://www.youtube.com/watch?v=...")
        url = None


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_dir = (Path(__file__).resolve().parent / output_path).resolve()
    else:
        output_dir = output_path.resolve()
    job_dir = output_dir / "_download"
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        source, track_title = download_audio(args.url, job_dir)
        print(f"ชื่อคลิป: {track_title}")

        vocals, instrumental = run_demucs(source, output_dir, args.model, args.device)

        # ตั้งชื่อโฟลเดอร์เป็นชื่อเพลงอย่างปลอดภัย ป้องกัน Path Traversal
        clean_name = sanitize_filename(track_title)
        final_dir = (output_dir / clean_name).resolve()
        if final_dir.parent != output_dir:
            final_dir = output_dir / "Track"

        final_dir.mkdir(parents=True, exist_ok=True)
        final_vocals = final_dir / "vocals.wav"
        final_instrumental = final_dir / "instrumental.wav"

        shutil.copy2(vocals, final_vocals)
        shutil.copy2(instrumental, final_instrumental)
        if args.keep_source:
            shutil.copy2(source, final_dir / source.name)

        # ลบโฟลเดอร์ชั่วคราว _download
        shutil.rmtree(job_dir, ignore_errors=True)

        # ลบโฟลเดอร์ชั่วคราว htdemucs/ ออกหลังย้ายไฟล์เสร็จ
        intermediate_model_dir = (output_dir / args.model).resolve()
        if intermediate_model_dir.exists() and intermediate_model_dir.parent == output_dir:
            shutil.rmtree(intermediate_model_dir, ignore_errors=True)

        print("\nแยกเสียงเสร็จแล้ว")
        print(f"ชื่อเพลง: {track_title}")
        print(f"โฟลเดอร์: {final_dir}")
        print(f"เสียงร้อง: {final_vocals}")
        print(f"เสียงดนตรี: {final_instrumental}")
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"เกิดข้อผิดพลาดจากโปรแกรมภายนอก (รหัส {exc.returncode})", file=sys.stderr)
        return exc.returncode or 1
    except Exception as exc:
        print(f"ผิดพลาด: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nยกเลิกการทำงาน")
        sys.exit(130)
