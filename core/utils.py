import os
import subprocess
import re

def asegurar_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def nombre_salida_por_video(video_path: str, base_dir="output/transcripciones", parte=None) -> str:
    """
    Genera un nombre de archivo válido en Windows a partir de un path o URL de video.
    Si es un enlace de YouTube, se usa el ID del video.
    """
    # Extraer solo el nombre base
    base_name = os.path.basename(video_path)

    # Si parece un link de YouTube → usar ID
    if "youtube.com" in video_path or "youtu.be" in video_path:
        match = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", video_path)
        if match:
            base_name = match.group(1)  # ID de YouTube

    # Limpiar caracteres inválidos para Windows
    base_name = re.sub(r'[<>:"/\\|?*]', "_", base_name)

    # Agregar extensión .txt
    if parte:
        file_name = f"{base_name}_parte{parte}.txt"
    else:
        file_name = f"{base_name}.txt"

    return os.path.join(base_dir, file_name)

def dividir_audio_ffmpeg(audio_path: str, partes: int = 5, log_fn=None):
    """
    Divide un audio en N partes iguales usando ffmpeg.
    Devuelve una lista con las rutas de los archivos resultantes.
    log_fn: función opcional para escribir logs en la interfaz.
    """
    # Obtener duración del audio con ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duracion = float(result.stdout.strip())
    duracion_segmento = duracion / partes

    base, _ = os.path.splitext(audio_path)
    paths = []

    for i in range(partes):
        inicio = i * duracion_segmento
        out_path = f"{base}_parte{i+1}.wav"

        if log_fn:
            log_fn(f"✂️ Generando fragmento {i+1}/{partes}...")

        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(inicio),
            "-t", str(duracion_segmento),
            out_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        paths.append(out_path)

        if log_fn:
            log_fn(f"✔ Fragmento {i+1}/{partes} listo: {out_path}")

    return paths

def limpiar_temp(path: str):
    """
    Borra un archivo temporal si existe.
    """
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"No se pudo borrar {path}: {e}")
