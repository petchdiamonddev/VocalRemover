from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path


def sanitize_filename(name: str) -> str:
    """ตัดอักขระพิเศษที่ไม่รองรับในชื่อโฟลเดอร์หรือไฟล์ และป้องกัน Path Traversal"""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r"\s+", " ", clean).strip().strip(".")
    # ป้องกันชื่อสงวนในระบบปฏิบัติการ Windows
    reserved = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
        "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
        "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    if clean.upper() in reserved:
        clean = f"Track_{clean}"
    return clean or "Track"


def _launch_browser_context(playwright, user_data_dir: Path):
    """เปิดเบราว์เซอร์ persistent context (ลอง Chrome -> Edge -> Chromium)"""
    browser_args = [
        "--disable-blink-features=AutomationControlled",
        "--autoplay-policy=no-user-gesture-required",
        "--use-fake-ui-for-media-stream",
        "--start-maximized",
    ]
    base_kwargs = {
        "user_data_dir": str(user_data_dir),
        "headless": False,
        "args": browser_args,
        "no_viewport": True,
    }

    try:
        return playwright.chromium.launch_persistent_context(channel="chrome", **base_kwargs)
    except Exception:
        pass

    try:
        return playwright.chromium.launch_persistent_context(channel="msedge", **base_kwargs)
    except Exception:
        pass

    return playwright.chromium.launch_persistent_context(**base_kwargs)


def _get_browser_context(playwright, user_data_dir: Path):
    """เชื่อมต่อ Chrome เดิมผ่าน Remote Debugging (port 9222) ถ้าเปิดไว้ หรือเปิดหน้าต่างใหม่"""
    try:
        browser = playwright.chromium.connect_over_cdp("http://localhost:9222", timeout=2000)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        print("เชื่อมต่อกับหน้าต่าง Chrome เดิมที่เปิดอยู่เรียบร้อย")
        return context, True
    except Exception:
        pass

    context = _launch_browser_context(playwright, user_data_dir)
    return context, False


def dismiss_overlays(page):
    """ปิด modal Restore session หรือ Microphone popup ที่อาจขวางการทำงาน"""
    try:
        cancel = page.locator("button:has-text('Cancel')").first
        if cancel.is_visible(timeout=1500):
            cancel.click()
            time.sleep(1)
    except Exception:
        pass

    for sel in [".ds-modal-close-button", "button[aria-label='Close']", ".modal-close", "button:has-text('✕')"]:
        try:
            close_btn = page.locator(sel).first
            if close_btn.is_visible(timeout=1000):
                close_btn.click()
                time.sleep(1)
        except Exception:
            pass


def open_bandlab_login(user_data_dir: Path | None = None) -> bool:
    """เปิดเบราว์เซอร์เพื่อให้ผู้ใช้เข้าสู่ระบบ BandLab เตรียมไว้"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ยังไม่ได้ติดตั้ง Playwright: pip install playwright", file=sys.stderr)
        return False

    if user_data_dir is None:
        user_data_dir = Path(__file__).resolve().parent / ".bandlab_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print("กำลังเปิดเบราว์เซอร์ BandLab...")
    with sync_playwright() as p:
        context, is_cdp = _get_browser_context(p, user_data_dir)
        page = context.new_page() if is_cdp else (context.pages[0] if context.pages else context.new_page())
        page.goto("https://www.bandlab.com/login", wait_until="domcontentloaded", timeout=60000)
        print("\nกรุณาเข้าสู่ระบบ BandLab ในเบราว์เซอร์")
        print("เมื่อเข้าสู่ระบบเรียบร้อยแล้ว ให้กด Enter ในหน้าจอนี้เพื่อเสร็จสิ้น...")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass
        try:
            if not is_cdp:
                context.close()
            else:
                page.close()
        except Exception:
            pass
    return True


def trigger_audio_import(page, upload_files: list[str]) -> bool:
    """นำเข้าไฟล์เสียงเข้าสู่ BandLab Studio โดยรองรับทั้งหน้าต่าง New Track และหน้าไทม์ไลน์"""
    dismiss_overlays(page)

    # ทางเลือก 1: มีปุ่ม Import Audio/MIDI ปรากฏอยู่บนหน้าจอแล้ว (เช่น ในกล่อง New Track)
    try:
        import_btn = page.locator("button:has-text('Import Audio/MIDI')").first
        if import_btn.is_visible(timeout=2000):
            print("กำลังเลือกไฟล์ผ่านปุ่ม Import Audio/MIDI...")
            with page.expect_file_chooser(timeout=8000) as fc_info:
                import_btn.click()
            fc_info.value.set_files(upload_files)
            return True
    except Exception:
        pass

    # ทางเลือก 2: มีกล่อง 'Drop a loop or an audio/MIDI/video file' กลางไทม์ไลน์
    try:
        drop_zone = page.locator(":has-text('Drop a loop')").last
        if drop_zone.is_visible(timeout=2000):
            print("กำลังเลือกไฟล์ผ่านกล่อง Drop zone บนไทม์ไลน์...")
            with page.expect_file_chooser(timeout=8000) as fc_info:
                drop_zone.click(force=True)
            fc_info.value.set_files(upload_files)
            return True
    except Exception:
        pass

    # ทางเลือก 3: กดปุ่ม + Add Track ด้านซ้ายบน แล้วเลือก Import Audio/MIDI
    try:
        print("กำลังกดปุ่ม + Add Track เพื่อเปิดเมนูนำเข้า...")
        add_btn = page.locator("#mix-editor-add-track-button, button:has-text('Add Track')").first
        if add_btn.is_visible(timeout=3000):
            add_btn.click(force=True)
            time.sleep(1.5)

        import_option = page.locator("button:has-text('Import Audio/MIDI'), div:has-text('Import Audio/MIDI'), :has-text('Import Audio/MIDI')").last
        if import_option.is_visible(timeout=4000):
            with page.expect_file_chooser(timeout=8000) as fc_info:
                import_option.click(force=True)
            fc_info.value.set_files(upload_files)
            return True
    except Exception as exc:
        print(f"นำเข้าผ่านเมนู Add Track ไม่สำเร็จ: {exc}")

    return False


def _set_project_title(page, title: str):
    try:
        title_input = page.locator("header input[type='text'], input[placeholder='New Project'], input[placeholder='Untitled']").first
        if title_input.is_visible(timeout=2000):
            title_input.click()
            title_input.fill("")
            title_input.fill(title)
            title_input.press("Enter")
            return

        title_label = page.locator("header :has-text('New Project'), header :has-text('Untitled'), [data-test='project-title']").first
        if title_label.is_visible(timeout=2000):
            title_label.click()
            time.sleep(0.5)
            active_input = page.locator("input:focus").first
            if active_input.is_visible(timeout=2000):
                active_input.fill("")
                active_input.fill(title)
                active_input.press("Enter")
                return
    except Exception as exc:
        print(f"ตั้งชื่อโปรเจกต์ไม่สำเร็จ: {exc}")


def _save_project(page):
    try:
        save_btn = page.locator("#studio-header-save-button, button:has-text('Save'), button[aria-label='Save']").first
        if save_btn.is_visible(timeout=2000):
            if save_btn.is_enabled():
                save_btn.click()
                time.sleep(2)
                print("บันทึกโปรเจกต์เรียบร้อย")
            else:
                print("โปรเจกต์ถูกบันทึกล่าสุดแล้ว (Auto-saved)")
    except Exception as exc:
        print(f"บันทึกโปรเจกต์อัตโนมัติไม่สำเร็จ: {exc}")


def upload_to_bandlab(
    project_title: str,
    instrumental_path: Path,
    vocals_path: Path | None = None,
    user_data_dir: Path | None = None,
    auto_close: bool = False,
) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ยังไม่ได้ติดตั้ง Playwright: pip install playwright", file=sys.stderr)
        return False

    instrumental_path = instrumental_path.resolve()
    if not instrumental_path.exists():
        print(f"ไม่พบไฟล์ดนตรี: {instrumental_path}", file=sys.stderr)
        return False

    if vocals_path:
        vocals_path = vocals_path.resolve()
        if not vocals_path.exists():
            vocals_path = None

    if user_data_dir is None:
        user_data_dir = Path(__file__).resolve().parent / ".bandlab_profile"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print("\nกำลังเปิดเบราว์เซอร์เพื่อนำเข้า BandLab...")

    with sync_playwright() as p:
        context, is_cdp = _get_browser_context(p, user_data_dir)
        page = context.new_page() if is_cdp else (context.pages[0] if context.pages else context.new_page())

        print("กำลังตรวจสอบสถานะการเข้าสู่ระบบ...")
        try:
            page.goto("https://www.bandlab.com/studio", wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
        except Exception:
            pass

        current_url = page.url.lower()
        if "login" in current_url or "sign-up" in current_url or "start" in current_url:
            print("\nกรุณาเข้าสู่ระบบ BandLab ในหน้าต่างเบราว์เซอร์...")
            print("เมื่อเข้าสู่ระบบเรียบร้อยแล้ว ให้กดปุ่ม Enter ในหน้าจอนี้เพื่อดำเนินการต่อทันที...")
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass
            print("กำลังเปิดหน้า BandLab Studio...")
            page.goto("https://www.bandlab.com/studio", wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)
        else:
            print("เข้าสู่ระบบเรียบร้อยแล้ว")

        print(f"กำลังเตรียมโปรเจกต์: {project_title}")
        dismiss_overlays(page)

        # นำเข้าไฟล์เสียง (ดนตรี + เสียงร้อง)
        upload_files = [str(instrumental_path)]
        if vocals_path and vocals_path.exists():
            upload_files.append(str(vocals_path))

        print(f"กำลังอัปโหลดไฟล์เพลงเข้าสู่ไทม์ไลน์ ({', '.join(Path(f).name for f in upload_files)})...")
        success_import = trigger_audio_import(page, upload_files)
        if success_import:
            print("อัปโหลดไฟล์เรียบร้อยแล้ว กำลังรอระบบ BandLab ประมวลผลคลื่นเสียง...")
            time.sleep(10)
        else:
            print("คำเตือน: ไม่สามารถนำเข้าไฟล์เสียงแบบอัตโนมัติได้ คุณสามารถลากไฟล์จากโฟลเดอร์ผลลัพธ์ลงไทม์ไลน์ได้โดยตรง")

        dismiss_overlays(page)

        # ตั้งชื่อโปรเจกต์ตามชื่อคลิป
        print(f"ตั้งชื่อโปรเจกต์: {project_title}")
        _set_project_title(page, project_title)
        time.sleep(1)

        # บันทึกโปรเจกต์
        print("กำลังบันทึกโปรเจกต์...")
        _save_project(page)

        print("\nนำเข้า BandLab เรียบร้อยแล้ว")
        print(f"- แทร็กดนตรี: {instrumental_path.name}")
        if vocals_path:
            print(f"- แทร็กเสียงร้อง: {vocals_path.name}")

        if auto_close:
            if not is_cdp:
                context.close()
            else:
                page.close()
        else:
            print("\nหน้าต่าง BandLab Studio เปิดพร้อมให้ใช้งานต่อได้ทันที")
            print("กด Enter ในหน้าจอนี้เพื่อปิดโปรแกรม (หรือปิดหน้าต่างเบราว์เซอร์โดยตรงได้ทุกเมื่อ)")
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                pass
            try:
                if not is_cdp:
                    context.close()
                else:
                    page.close()
            except Exception:
                pass

    return True


def _find_latest_output(outputs_dir: Path) -> tuple[str, Path, Path | None] | None:
    """ค้นหาโฟลเดอร์เพลงล่าสุดใน outputs ที่มีไฟล์ instrumental.wav"""
    if not outputs_dir.exists():
        return None

    candidates = []
    for item in outputs_dir.iterdir():
        if item.is_dir() and item.name not in ("_download", "htdemucs"):
            inst = item / "instrumental.wav"
            if inst.exists():
                candidates.append((item.stat().st_mtime, item.name, inst, item / "vocals.wav"))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, name, inst, voc = candidates[0]
    return name, inst, voc if voc.exists() else None


def _cleanup_folder(folder: Path):
    """ลบโฟลเดอร์ผลลัพธ์พร้อมรับมือ file handle ของระบบปฏิบัติการ"""
    import shutil
    if not folder.exists():
        return
    for _ in range(3):
        try:
            shutil.rmtree(folder, ignore_errors=True)
            if not folder.exists():
                break
        except Exception:
            pass
        time.sleep(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="นำเข้าไฟล์เสียงขึ้น BandLab Studio")
    parser.add_argument("title", nargs="?", help="ชื่อเพลง/โปรเจกต์")
    parser.add_argument("-i", "--instrumental", help="พาธไฟล์ instrumental.wav")
    parser.add_argument("-v", "--vocals", help="พาธไฟล์ vocals.wav")
    parser.add_argument("--login", action="store_true", help="เปิดเบราว์เซอร์เพื่อเข้าสู่ระบบ BandLab เตรียมไว้")
    args = parser.parse_args()

    if args.login:
        open_bandlab_login()
        return 0

    if args.title and args.instrumental:
        success = upload_to_bandlab(
            project_title=args.title,
            instrumental_path=Path(args.instrumental),
            vocals_path=Path(args.vocals) if args.vocals else None,
        )
        if success:
            song_folder = Path(args.instrumental).resolve().parent
            _cleanup_folder(song_folder)
        return 0 if success else 1

    outputs_dir = Path(__file__).resolve().parent / "outputs"
    latest = _find_latest_output(outputs_dir)

    if latest:
        song_title, inst_path, voc_path = latest
        print(f"พบเพลงล่าสุดใน outputs: '{song_title}'")
        choice = input("ต้องการนำเข้าเพลงนี้เข้าสู่ BandLab หรือไม่? (y/n) [default: y]: ").strip().lower()
        if choice in ("", "y", "yes"):
            success = upload_to_bandlab(
                project_title=song_title,
                instrumental_path=inst_path,
                vocals_path=voc_path,
            )
            if success:
                song_folder = inst_path.parent
                print(f"กำลังลบไฟล์ใน {song_folder.name} ออกจาก outputs...")
                _cleanup_folder(song_folder)
                print("ลบไฟล์ใน outputs เรียบร้อยแล้ว")
            return 0 if success else 1
        return 0

    print("ยังไม่พบเพลงที่แยกไว้ในโฟลเดอร์ outputs/")
    print("ตัวเลือก:")
    print("1. เข้าสู่ระบบ BandLab เตรียมไว้")
    print("2. ออกจากโปรแกรม")
    choice = input("เลือก (1/2): ").strip()
    if choice == "1":
        open_bandlab_login()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
