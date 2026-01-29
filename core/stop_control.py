import subprocess
import threading

_stop_event = threading.Event()
_busy_event = threading.Event()


def clear_stop():
    _stop_event.clear()


def set_busy(state: bool):
    if state:
        _busy_event.set()
    else:
        _busy_event.clear()


def is_busy() -> bool:
    return _busy_event.is_set()


def should_stop() -> bool:
    return _stop_event.is_set()


def request_stop(log_fn=None, clear_busy: bool = True):
    _stop_event.set()
    if clear_busy:
        _busy_event.clear()
    if log_fn:
        log_fn("🛑 Stop solicitado. Deteniendo procesos...")
    _kill_process("ffmpeg.exe", log_fn)
    _kill_process("ffprobe.exe", log_fn)
    _kill_process("yt-dlp.exe", log_fn)


def _kill_process(name: str, log_fn=None):
    try:
        subprocess.run(
            ["taskkill", "/F", "/IM", name],
            capture_output=True,
            text=True
        )
        if log_fn:
            log_fn(f"🧯 Finalizando {name}...")
    except Exception:
        pass
