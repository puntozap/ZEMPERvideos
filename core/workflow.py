from core.extractor import extraer_audio
from core.utils import limpiar_temp, dividir_audio_ffmpeg
from core.youtube_downloader import descargar_audio_youtube


def procesar_video(video_path: str, es_youtube: bool, es_audio: bool = False, barra=None, logs=None):
    """
    Procesa un archivo (video, YouTube o audio):
    - Extrae/descarga audio
    - Divide en 5 partes (sin transcripcion)
    """

    try:
        if logs: logs("🚀 Iniciando procesamiento...")

        # 1. Obtener audio (local, YouTube o archivo ya existente)
        if es_youtube:
            if logs: logs(f"📥 Descargando audio desde YouTube: {video_path}")
            audio_path = descargar_audio_youtube(video_path)
            if logs: logs(f"✔ Audio descargado: {audio_path}")
        elif es_audio:
            audio_path = video_path
            if logs: logs(f"Audio seleccionado: {video_path}")
        else:
            if logs: logs(f"📁 Video seleccionado: {video_path}")
            if logs: logs("🎧 Extrayendo audio...")
            audio_path = extraer_audio(video_path)
            if logs: logs(f"✔ Audio temporal: {audio_path}")

        # 2. Dividir audio
        if logs: logs("✂️ Dividiendo audio en 5 partes...")
        partes = dividir_audio_ffmpeg(audio_path, partes=5, log_fn=logs if logs else None)
        if logs: logs(f"✔ Audio dividido en {len(partes)} fragmentos")

        # 3. (Temporal) no transcribir ni generar textos
        for idx, _parte in enumerate(partes, start=1):
            if logs: logs(f"Parte {idx}/{len(partes)} lista (sin transcripcion).")
            if barra: barra.set(idx / len(partes))

    except Exception as e:
        if logs: logs(f"ƒ?O Error: {e}")
        raise e
    finally:
        try:
            limpiar_temp("temp_audio.wav")
        except Exception:
            pass
        if barra: barra.set(0)
