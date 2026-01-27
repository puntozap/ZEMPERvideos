import os
import tempfile
import subprocess

def extraer_audio(video_path: str, audio_path: str | None = None) -> str:
    """
    Extrae el audio de un video usando ffmpeg.
    Devuelve la ruta del archivo MP3 generado.
    """
    # Archivo temporal por defecto
    if audio_path is None:
        tmpdir = tempfile.gettempdir()
        audio_path = os.path.join(tmpdir, "temp_audio.mp3")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-b:a", "192k",
        audio_path
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if not os.path.exists(audio_path):
        raise RuntimeError("No se pudo generar el archivo de audio.")

    return audio_path
