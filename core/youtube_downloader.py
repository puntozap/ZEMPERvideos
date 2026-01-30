import os
import sys
import subprocess
import time
import shutil
import yt_dlp
from yt_dlp.utils import DownloadError
from core import stop_control
from core.utils import output_base_dir

def _actualizar_yt_dlp(log_fn=None):
    if log_fn:
        log_fn("Actualizando yt-dlp...")
    cmd = [sys.executable, "-m", "yt_dlp", "-U"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _descargar_youtube(
    url: str,
    opciones: dict,
    output_dir: str,
    retry_update: bool,
    retry_android: bool,
    player_client: str | None,
    cookies_from_browser: str | None,
    log_fn=None
):
    if log_fn:
        state = {"last_percent": -1, "last_log_ts": 0.0}

        def _format_bytes(num):
            try:
                num = float(num)
            except Exception:
                return "?"
            for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
                if num < 1024.0:
                    return f"{num:.2f}{unit}"
                num /= 1024.0
            return f"{num:.2f}PiB"

        def _progress_hook(d):
            if stop_control.should_stop():
                raise DownloadError("Stop requested")
            status = d.get("status")
            if status == "finished":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                total_txt = _format_bytes(total) if total else "?"
                log_fn(f"[download] 100% of {total_txt} in 00:00:00")
                return
            if status != "downloading":
                return
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes") or 0
            if not total:
                return
            percent = int((downloaded / total) * 100)
            now = time.time()
            if percent == state["last_percent"] and (now - state["last_log_ts"]) < 1.0:
                return
            state["last_percent"] = percent
            state["last_log_ts"] = now
            speed = d.get("speed")
            eta = d.get("eta")
            total_txt = _format_bytes(total)
            speed_txt = _format_bytes(speed) + "/s" if speed else "?"
            eta_txt = time.strftime("%H:%M:%S", time.gmtime(eta)) if isinstance(eta, (int, float)) else "?"
            log_fn(f"[download] {percent}% of {total_txt} at {speed_txt}, ETA {eta_txt}")

        opciones["progress_hooks"] = [_progress_hook]

    if player_client:
        opciones["extractor_args"] = {"youtube": {"player_client": [player_client]}}
    if cookies_from_browser:
        opciones["cookiesfrombrowser"] = cookies_from_browser

    try:
        if stop_control.should_stop():
            raise DownloadError("Stop requested")
        with yt_dlp.YoutubeDL(opciones) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except DownloadError as e:
        msg = str(e)
        if retry_update and ("403" in msg or "HTTP Error 403" in msg):
            _actualizar_yt_dlp(log_fn=log_fn)
            return _descargar_youtube(
                url,
                opciones,
                output_dir=output_dir,
                retry_update=False,
                retry_android=retry_android,
                player_client=player_client,
                cookies_from_browser=cookies_from_browser,
                log_fn=log_fn
            )
        if retry_android and ("403" in msg or "HTTP Error 403" in msg):
            if log_fn:
                log_fn("Reintentando con cliente Android...")
            return _descargar_youtube(
                url,
                opciones,
                output_dir=output_dir,
                retry_update=False,
                retry_android=False,
                player_client="android",
                cookies_from_browser=cookies_from_browser,
                log_fn=log_fn
            )
        raise

def descargar_audio_youtube(
    url: str,
    output_dir: str = os.path.join("output", "_downloads_tmp"),
    retry_update: bool = True,
    retry_android: bool = True,
    player_client: str | None = None,
    cookies_from_browser: str | None = None,
    log_fn=None
) -> str:
    """
    Descarga el audio de un video de YouTube en formato MP3.
    Devuelve la ruta al archivo descargado.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Plantilla de salida (sin espacios raros en el nombre del archivo)
    output_path = os.path.join(output_dir, "%(title).20s", "%(title).20s.%(ext)s")

    opciones = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    archivo_salida = _descargar_youtube(
        url,
        opciones,
        output_dir=output_dir,
        retry_update=retry_update,
        retry_android=retry_android,
        player_client=player_client,
        cookies_from_browser=cookies_from_browser,
        log_fn=log_fn
    )
    archivo_mp3 = os.path.splitext(archivo_salida)[0] + ".mp3"
    base_dir = output_base_dir(archivo_mp3)
    final_dir = os.path.join(base_dir, "download")
    os.makedirs(final_dir, exist_ok=True)
    final_path = os.path.join(final_dir, os.path.basename(archivo_mp3))
    try:
        shutil.move(archivo_mp3, final_path)
    except Exception:
        final_path = archivo_mp3
    return final_path

def descargar_video_youtube_mp4(
    url: str,
    output_dir: str = os.path.join("output", "_downloads_tmp"),
    retry_update: bool = True,
    retry_android: bool = True,
    player_client: str | None = None,
    cookies_from_browser: str | None = None,
    log_fn=None
) -> str:
    """
    Descarga un video de YouTube en MP4.
    Devuelve la ruta al archivo descargado.
    """
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "%(title).20s", "%(title).20s.%(ext)s")

    opciones = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_path,
        "noplaylist": True,
    }

    archivo_salida = _descargar_youtube(
        url,
        opciones,
        output_dir=output_dir,
        retry_update=retry_update,
        retry_android=retry_android,
        player_client=player_client,
        cookies_from_browser=cookies_from_browser,
        log_fn=log_fn
    )
    base, _ext = os.path.splitext(archivo_salida)
    archivo_mp4 = base + ".mp4"
    base_dir = output_base_dir(archivo_mp4)
    final_dir = os.path.join(base_dir, "download")
    os.makedirs(final_dir, exist_ok=True)
    final_path = os.path.join(final_dir, os.path.basename(archivo_mp4))
    try:
        shutil.move(archivo_mp4, final_path)
    except Exception:
        final_path = archivo_mp4
    return final_path

