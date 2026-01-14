import os
import yt_dlp

def descargar_audio_youtube(url: str, output_dir: str = "downloads") -> str:
    """
    Descarga el audio de un video de YouTube en formato WAV.
    Devuelve la ruta al archivo descargado.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Plantilla de salida (sin espacios raros en el nombre del archivo)
    output_path = os.path.join(output_dir, "%(title).80s.%(ext)s")

    opciones = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
    }

    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(url, download=True)
        archivo_salida = ydl.prepare_filename(info)
        archivo_wav = os.path.splitext(archivo_salida)[0] + ".wav"
        return archivo_wav
