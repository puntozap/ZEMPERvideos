from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core.transcriber import transcribir_srt
from core.utils import dividir_audio_ffmpeg, obtener_duracion_segundos
from core.youtube_downloader import descargar_audio_youtube


def _format_mm_ss(seconds_value: float) -> str:
    seconds_value = max(0.0, float(seconds_value))
    minutes = int(seconds_value // 60)
    seconds = int(seconds_value % 60)
    return f"{minutes:02d}:{seconds:02d}"


def _extract_video_id(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    try:
        parsed = urlparse(text)
        host = (parsed.netloc or "").lower()
        if "youtu.be" in host:
            return (parsed.path or "").lstrip("/").split("/")[0].strip()
        qs = parse_qs(parsed.query or "")
        vid = (qs.get("v") or [""])[0].strip()
        return vid
    except Exception:
        return ""


def _extract_text_from_srt(path: str) -> str:
    """
    Extract plain text from an SRT file (drop indices/timestamps).
    """
    try:
        data = Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    data = data.replace("\r\n", "\n")
    lines: list[str] = []
    for raw in data.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        # Drop common formatting escapes.
        line = re.sub(r"\{\\.*?\}", "", line).strip()
        if line:
            lines.append(line)
    text = "\n".join(lines).strip()
    return text


def generar_subtitulos_por_minuto_desde_youtube(
    youtube_url: str,
    *,
    segundos_por_parte: int = 60,
    idioma: str = "es",
    model_size: str = "base",
    log_fn=None,
    max_doc_chars: int = 800_000,
) -> str:
    """
    Descarga el audio (mp3) desde YouTube, lo divide en partes de 1 minuto,
    transcribe cada parte a SRT y devuelve un texto listo para pegar en Google Docs.

    Limpieza:
    - Los cortes de audio y los .srt temporales se eliminan a medida que se procesan.
    - El mp3 original descargado se mantiene (se usa una copia temporal).
    """
    url = (youtube_url or "").strip()
    if not url:
        raise ValueError("Falta el link del video.")

    video_id = _extract_video_id(url) or "video"
    tmp_root = Path(tempfile.gettempdir()) / f"transcriptor_ytdoc_{os.getpid()}_{video_id}"
    parts_dir = tmp_root / "parts"
    srt_dir = tmp_root / "srt"
    tmp_root.mkdir(parents=True, exist_ok=True)
    parts_dir.mkdir(parents=True, exist_ok=True)
    srt_dir.mkdir(parents=True, exist_ok=True)

    if log_fn:
        log_fn("Descargando MP3 desde YouTube (puede tardar)...")
    audio_path = descargar_audio_youtube(url, log_fn=log_fn)

    # Work on a local temp copy so we can cleanup safely.
    tmp_audio_path = tmp_root / "audio.mp3"
    try:
        shutil.copy2(audio_path, tmp_audio_path)
    except Exception:
        # Fallback to using the downloaded file directly if copy fails.
        tmp_audio_path = Path(audio_path)

    if log_fn:
        log_fn("Dividiendo audio en partes de 1 minuto...")
    part_paths = dividir_audio_ffmpeg(
        str(tmp_audio_path),
        float(segundos_por_parte),
        str(parts_dir),
        log_fn=log_fn,
    )
    if not part_paths:
        raise RuntimeError("No se pudieron generar partes de audio.")

    total_seconds = 0.0
    try:
        total_seconds = float(obtener_duracion_segundos(str(tmp_audio_path)))
    except Exception:
        total_seconds = float(len(part_paths) * segundos_por_parte)

    out_lines: list[str] = []
    out_lines.append("Subtitulos (transcripcion por minutos)")
    out_lines.append(f"Video: {url}")
    out_lines.append("")

    for idx, part_path in enumerate(part_paths, start=1):
        start_sec = (idx - 1) * segundos_por_parte
        end_sec = min(idx * segundos_por_parte, int(total_seconds + 0.999))
        start_txt = _format_mm_ss(start_sec)
        end_txt = _format_mm_ss(end_sec)

        if log_fn:
            log_fn(f"Transcribiendo {idx}/{len(part_paths)}: {start_txt} a {end_txt} ...")

        srt_path = ""
        try:
            srt_path = transcribir_srt(part_path, str(srt_dir), idioma=idioma, model_size=model_size)
            text = _extract_text_from_srt(srt_path)
        finally:
            # Delete the temp SRT and audio cut regardless of read errors.
            if srt_path:
                try:
                    Path(srt_path).unlink(missing_ok=True)
                except Exception:
                    pass
            try:
                Path(part_path).unlink(missing_ok=True)
            except Exception:
                pass

        out_lines.append(f"Del minuto {start_txt} al {end_txt}:")
        out_lines.append(text if text else "(sin texto)")
        out_lines.append("")

        if sum(len(x) + 1 for x in out_lines) > max_doc_chars:
            if log_fn:
                log_fn(f"Limite de texto alcanzado ({max_doc_chars} chars). Cortando transcripcion.")
            out_lines.append("[CORTADO POR LIMITE DE TAMANO]")
            out_lines.append("")
            break

    # Cleanup temp dirs and temp audio copy (original download remains).
    try:
        if tmp_audio_path.exists() and tmp_audio_path.is_file() and tmp_audio_path.parent == tmp_root:
            tmp_audio_path.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        shutil.rmtree(tmp_root, ignore_errors=True)
    except Exception:
        pass

    if log_fn:
        log_fn("Subtitulos listos para Google Docs.")
    return "\n".join(out_lines).strip() + "\n"

