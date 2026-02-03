from __future__ import annotations

import os
import re
from typing import Optional, Tuple

from core.extractor import extraer_audio
from core.transcriber import transcribir, transcribir_srt
from core.utils import output_base_dir, output_subtitulados_dir

MAX_TRANSCRIPTION_CHARS = 9000
DEFAULT_SRT_MODEL = "base"


def obtener_transcripcion_para_video(
    video_path: str,
    idioma: str = "es",
    logs=None,
    max_chars: int = MAX_TRANSCRIPTION_CHARS,
) -> str:
    if logs:
        logs("Transcribiendo video para IA...")
    texto = transcribir(video_path, idioma=idioma, model_size="small")
    if not texto:
        raise RuntimeError("La transcripción no devolvió texto válido.")
    if len(texto) > max_chars:
        if logs:
            logs(f"Transcripción truncada a {max_chars} caracteres.")
        texto = texto[:max_chars]
    return texto


def extraer_audio_y_subtitulos(
    video_path: str,
    idioma: str,
    logs=None,
    model_size: str = DEFAULT_SRT_MODEL,
) -> Tuple[str, Optional[str]]:
    base_dir = output_base_dir(video_path)
    audio_dir = os.path.join(base_dir, "audios")
    os.makedirs(audio_dir, exist_ok=True)
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    safe_name = re.sub(r"[<>:\"/\\|?*]", "_", video_name)
    audio_name = f"{safe_name}_whatsapp_audio.mp3"
    audio_path = os.path.join(audio_dir, audio_name)
    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
        if logs:
            logs(f"Usando audio existente para subtítulos: {audio_path}")
    else:
        extraer_audio(video_path, audio_path, log_fn=logs)

    subs_dir = output_subtitulados_dir(video_path)
    os.makedirs(subs_dir, exist_ok=True)
    srt_path = None
    try:
        srt_path = transcribir_srt(
            audio_path,
            subs_dir,
            idioma=idioma,
            model_size=model_size,
        )
        if logs:
            logs(f"SRT generado: {srt_path}")
    except Exception as exc:
        if logs:
            logs(f"Advertencia: no se pudo generar el SRT ({exc})")
    return audio_path, srt_path
