import os
import tempfile
import subprocess
import hashlib
from core.utils import tiene_audio

def _safe_audio_path(path: str) -> str:
    # Evitar rutas demasiado largas en Windows
    if len(path) <= 240:
        return path
    base_dir = os.path.dirname(path)
    name = os.path.basename(path)
    stem, ext = os.path.splitext(name)
    digest = hashlib.md5(path.encode("utf-8", errors="ignore")).hexdigest()[:6]
    stem = stem[:60].rstrip("_- ")
    safe_name = f"{stem}_{digest}{ext}"
    return os.path.join(base_dir, safe_name)


def extraer_audio(video_path: str, audio_path: str | None = None, log_fn=None) -> str:
    """
    Extrae el audio de un video usando ffmpeg.
    Devuelve la ruta del archivo MP3 generado.
    """
    # Archivo temporal por defecto
    if audio_path is None:
        tmpdir = tempfile.gettempdir()
        audio_path = os.path.join(tmpdir, "temp_audio.mp3")

    if not tiene_audio(video_path):
        raise RuntimeError("El video no tiene pista de audio.")

    audio_path = _safe_audio_path(audio_path)
    os.makedirs(os.path.dirname(audio_path), exist_ok=True) if os.path.dirname(audio_path) else None
    if log_fn and audio_path:
        log_fn(f"Audio destino: {audio_path}")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-b:a", "192k",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        err = (result.stderr or "").strip()
        if log_fn and err:
            log_fn(f"ffmpeg audio error: {err[-400:]}")
        if log_fn:
            log_fn(f"Audio generado: exists={os.path.exists(audio_path)} size={(os.path.getsize(audio_path) if os.path.exists(audio_path) else 0)}")
        raise RuntimeError("No se pudo generar el archivo de audio.")

    return audio_path
