import os
import subprocess
import re
import math
import tempfile
import threading
import time
import uuid
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from core import stop_control

def asegurar_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def nombre_salida_por_video(video_path: str, base_dir=None, parte=None) -> str:
    """
    Genera un nombre de archivo vÃ¡lido en Windows a partir de un path o URL de video.
    Si es un enlace de YouTube, se usa el ID del video.
    """
    # Extraer solo el nombre base
    base_name = os.path.basename(video_path)

    # Si parece un link de YouTube â†’ usar ID
    if "youtube.com" in video_path or "youtu.be" in video_path:
        match = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", video_path)
        if match:
            base_name = match.group(1)  # ID de YouTube

    # Limpiar caracteres invÃ¡lidos para Windows
    base_name = re.sub(r'[<>:"/\\|?*]', "_", base_name)

    if base_dir is None:
        base_dir = os.path.join(output_base_dir(video_path), "transcripciones")

    # Agregar extensiÃ³n .txt
    if parte:
        file_name = f"{base_name}_parte{parte}.txt"
    else:
        file_name = f"{base_name}.txt"

    return os.path.join(base_dir, file_name)

def nombre_base_fuente(video_path: str) -> str:
    """
    Obtiene un nombre base (sin extensiÃ³n) seguro para carpetas/archivos.
    Si es YouTube, usa el ID.
    """
    base_name = os.path.basename(video_path)
    if "youtube.com" in video_path or "youtu.be" in video_path:
        match = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", video_path)
        if match:
            base_name = match.group(1)
    base_name = os.path.splitext(base_name)[0]
    base_name = re.sub(r'[<>:"/\\|?*]', "_", base_name)
    return base_name

def nombre_base_principal(video_path: str) -> str:
    """
    Obtiene un nombre base principal (sin extensiÃ³n, sin sufijos de partes/vertical).
    """
    base_name = os.path.basename(video_path)
    if "youtube.com" in video_path or "youtu.be" in video_path:
        match = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", video_path)
        if match:
            base_name = match.group(1)
    base_name = os.path.splitext(base_name)[0]
    base_name = re.sub(r'[<>:"/\\|?*]', "_", base_name)
    base_name = base_name.strip()

    def _strip_suffixes(name: str) -> str:
        prev = None
        while prev != name:
            prev = name
            name = re.sub(r"([ _-]*(parte|part)[ _-]*\d+)$", "", name, flags=re.IGNORECASE).strip()
            name = re.sub(r"([ _-]*(srt[_-]*source|srt|subt|sub|tmp|vertical|vert|completo|original))$", "", name, flags=re.IGNORECASE).strip()
        return name

    base_name = _strip_suffixes(base_name)
    return base_name or "video"

def output_base_dir(video_path: str) -> str:
    """
    Carpeta base para todos los outputs de un video.
    """
    return os.path.join("output", nombre_base_principal(video_path))

def output_subdir(video_path: str, subdir: str) -> str:
    return os.path.join(output_base_dir(video_path), subdir)

def next_correlative_dir(base_dir: str, subdir: str, prefix: str) -> str:
    """
    Devuelve un subdirectorio correlativo dentro de base_dir/subdir con prefijo.
    Ej: output/<base>/verticales/corte_001
    """
    root = os.path.join(base_dir, subdir)
    os.makedirs(root, exist_ok=True)
    max_idx = 0
    for name in os.listdir(root):
        if not os.path.isdir(os.path.join(root, name)):
            continue
        m = re.match(rf"^{re.escape(prefix)}_(\d+)$", name)
        if m:
            try:
                max_idx = max(max_idx, int(m.group(1)))
            except Exception:
                pass
    next_idx = max_idx + 1
    folder = os.path.join(root, f"{prefix}_{next_idx:03d}")
    os.makedirs(folder, exist_ok=True)
    return folder

def output_subtitulados_dir(video_path: str) -> str:
    """
    Si el video viene de verticales, se guarda en el mismo folder.
    Si no, se guarda en output/<base>/subtitulados.
    """
    norm = os.path.normpath(video_path)
    if f"{os.sep}verticales{os.sep}" in norm:
        return os.path.dirname(video_path)
    return output_subdir(video_path, "subtitulados")

def obtener_duracion_segundos(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())

def obtener_tamano_video(path: str) -> tuple[int, int]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    parts = result.stdout.strip().split("x")
    if len(parts) != 2:
        return (1920, 1080)
    return (int(parts[0]), int(parts[1]))

def obtener_fps(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    val = result.stdout.strip()
    if not val:
        return 30.0
    if "/" in val:
        num, den = val.split("/", 1)
        try:
            num_f = float(num)
            den_f = float(den)
            if den_f > 0:
                return num_f / den_f
        except Exception:
            return 30.0
    try:
        return float(val)
    except Exception:
        return 30.0


def _pil_color(value: str, fallback: str) -> str:
    val = (value or "").strip()
    if not val:
        val = fallback
    if val.lower().startswith("0x"):
        hexval = val[2:]
        return "#" + hexval.upper()
    if not val.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in val) and len(val) in (3, 6):
        return "#" + val.upper()
    return val


def _render_mensajes_on_background(
    imagen_path: str,
    target_w: int,
    target_h: int,
    mensajes: list[dict],
    transparent: bool = False,
) -> str | None:
    try:
        if transparent:
            bg = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        else:
            bg = Image.open(imagen_path).convert("RGBA")
            bg = bg.resize((target_w, target_h), Image.LANCZOS)
    except Exception:
        return None
    draw = ImageDraw.Draw(bg, "RGBA")

    for m in mensajes:
        try:
            left = float(m.get("left_pct", 0)) / 100.0
            top = float(m.get("top_pct", 0)) / 100.0
            width = float(m.get("width_pct", 0)) / 100.0
            height = float(m.get("height_pct", 0)) / 100.0
        except Exception:
            continue
        left_px = int(target_w * left)
        top_px = int(target_h * top)
        width_px = max(2, int(target_w * width))
        height_px = max(2, int(target_h * height))

        bg_color = _pil_color(m.get("bg_color"), "#D91E18")
        text_color = _pil_color(m.get("text_color"), "#FFFFFF")
        border_color = _pil_color(m.get("border_color"), "#FFC400")
        radius_pct = float(m.get("radius_pct", 0.5) or 0.5)
        border_w = int(float(m.get("border_width", 2) or 2))
        radius = max(2, int(height_px * radius_pct))

        rect = [left_px, top_px, left_px + width_px, top_px + height_px]
        draw.rounded_rectangle(rect, radius=radius, fill=bg_color)
        if border_w > 0 and border_color:
            draw.rounded_rectangle(rect, radius=radius, outline=border_color, width=border_w)

        text = str(m.get("text", "") or "")
        fontfile = (m.get("fontfile") or "").strip()
        font_size = max(14, int(height_px * 0.55))
        try:
            if fontfile and os.path.exists(fontfile):
                font = ImageFont.truetype(fontfile, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except Exception:
            text_w = len(text) * font_size * 0.5
            text_h = font_size
        text_x = left_px + (width_px - text_w) / 2
        text_y = top_px + (height_px - text_h) / 2
        draw.text((text_x, text_y), text, font=font, fill=text_color)

    tmp_path = os.path.join(tempfile.gettempdir(), f"msg_{uuid.uuid4().hex}.png")
    try:
        bg.save(tmp_path, "PNG")
    except Exception:
        return None
    return tmp_path


def _render_cintas_on_background(
    imagen_path: str,
    target_w: int,
    target_h: int,
    cintas: list[dict],
    transparent: bool = False,
) -> str | None:
    try:
        if transparent:
            bg = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        else:
            bg = Image.open(imagen_path).convert("RGBA")
            bg = bg.resize((target_w, target_h), Image.LANCZOS)
    except Exception:
        return None
    draw = ImageDraw.Draw(bg, "RGBA")

    for c in cintas:
        try:
            left = float(c.get("left_pct", 0)) / 100.0
            top = float(c.get("top_pct", 0)) / 100.0
            width = float(c.get("width_pct", 0)) / 100.0
            height = float(c.get("height_pct", 0)) / 100.0
        except Exception:
            continue
        left_px = int(target_w * left)
        top_px = int(target_h * top)
        width_px = max(2, int(target_w * width))
        height_px = max(2, int(target_h * height))
        border_w = max(4, int(height_px * 0.08))

        bg_color = _pil_color(c.get("bg_color"), "#000000")
        border_color = _pil_color(c.get("border_color"), "#FFC400")
        text_color = _pil_color(c.get("text_color"), "#FFFFFF")

        rect = [left_px, top_px, left_px + width_px, top_px + height_px]
        draw.rectangle(rect, fill=bg_color)
        draw.rectangle(
            [left_px, top_px, left_px + border_w, top_px + height_px],
            fill=border_color,
        )

        name = str(c.get("nombre", "") or "")
        role = str(c.get("rol", "") or "")
        name_fontfile = (c.get("fontfile_name") or "").strip()
        role_fontfile = (c.get("fontfile_role") or "").strip()
        name_size = max(14, int(height_px * 0.45))
        role_size = max(12, int(height_px * 0.30))
        try:
            if name_fontfile and os.path.exists(name_fontfile):
                name_font = ImageFont.truetype(name_fontfile, name_size)
            else:
                name_font = ImageFont.load_default()
        except Exception:
            name_font = ImageFont.load_default()
        try:
            if role_fontfile and os.path.exists(role_fontfile):
                role_font = ImageFont.truetype(role_fontfile, role_size)
            else:
                role_font = ImageFont.load_default()
        except Exception:
            role_font = ImageFont.load_default()

        pad_x = max(6, int(height_px * 0.12))
        pad_y = max(4, int(height_px * 0.12))
        draw.text((left_px + border_w + pad_x, top_px + pad_y), name, font=name_font, fill=text_color)
        draw.text((left_px + border_w + pad_x, top_px + pad_y + name_size + 2), role, font=role_font, fill=text_color)

    tmp_path = os.path.join(tempfile.gettempdir(), f"cintas_{uuid.uuid4().hex}.png")
    try:
        bg.save(tmp_path, "PNG")
    except Exception:
        return None
    return tmp_path

def tiene_audio(path: str) -> bool:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip() == "audio"

def aplicar_musica_fondo(
    video_path: str,
    music_path: str,
    volumen: float = 0.25,
    music_start: float = 0.0,
    music_end: float | None = None,
    video_start: float = 0.0,
    output_path: str | None = None,
    log_fn=None,
):
    """
    Mezcla una pista de música de fondo con el audio del video.
    - music_start / music_end: tramo de la música (segundos)
    - video_start: segundo del video en que debe iniciar la música
    - Si la música es más corta que el video, no se fuerza loop.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"No se encontró el video: {video_path}")
    if not music_path or not os.path.exists(music_path):
        if log_fn:
            log_fn("⚠️ Música de fondo no válida. Se omite.")
        return video_path

    try:
        video_dur = float(obtener_duracion_segundos(video_path))
    except Exception:
        video_dur = 0.0
    if video_dur <= 0:
        if log_fn:
            log_fn("⚠️ Duración del video inválida. Se omite música.")
        return video_path

    try:
        music_dur = float(obtener_duracion_segundos(music_path))
    except Exception:
        music_dur = 0.0
    if music_dur <= 0:
        if log_fn:
            log_fn("⚠️ Duración de la música inválida. Se omite.")
        return video_path

    try:
        music_start = max(0.0, float(music_start or 0.0))
    except Exception:
        music_start = 0.0
    try:
        video_start = max(0.0, float(video_start or 0.0))
    except Exception:
        video_start = 0.0

    if music_start >= music_dur:
        if log_fn:
            log_fn("⚠️ Inicio de música supera la duración. Se omite.")
        return video_path
    if video_start >= video_dur:
        if log_fn:
            log_fn("⚠️ Inicio de música en video fuera de rango. Se omite.")
        return video_path

    if music_end is not None:
        try:
            music_end = float(music_end)
        except Exception:
            music_end = None
    if music_end is not None and music_end > music_start:
        segment = music_end - music_start
    else:
        segment = max(0.0, music_dur - music_start)

    remaining = max(0.0, video_dur - video_start)
    effective = min(segment, remaining)
    if effective <= 0:
        if log_fn:
            log_fn("⚠️ No hay duración efectiva para la música. Se omite.")
        return video_path

    try:
        volumen = float(volumen)
    except Exception:
        volumen = 0.25
    volumen = max(0.0, min(volumen, 2.0))

    delay_ms = int(video_start * 1000)
    has_audio = tiene_audio(video_path)

    if has_audio:
        filtro = (
            f"[1:a]volume={volumen:.3f},adelay={delay_ms}|{delay_ms}[bg];"
            f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=0,"
            f"apad,atrim=0:{video_dur:.3f}[mix]"
        )
    else:
        filtro = (
            f"[1:a]volume={volumen:.3f},adelay={delay_ms}|{delay_ms},apad,"
            f"atrim=0:{video_dur:.3f}[mix]"
        )

    final_path = output_path or video_path
    temp_path = final_path
    if final_path == video_path:
        temp_path = os.path.splitext(video_path)[0] + "_bgm_tmp.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", f"{music_start:.3f}",
        "-t", f"{effective:.3f}",
        "-i", music_path,
        "-filter_complex", filtro,
        "-map", "0:v:0",
        "-map", "[mix]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-t", f"{video_dur:.3f}",
        "-movflags", "+faststart",
        temp_path
    ]

    if log_fn:
        log_fn("🎵 Mezclando música de fondo...")

    result = subprocess.run(cmd, capture_output=True, text=False)
    if result.returncode != 0:
        err = ""
        out = ""
        try:
            if result.stderr:
                err = result.stderr.decode("utf-8", errors="ignore").strip()
        except Exception:
            err = ""
        try:
            if result.stdout:
                out = result.stdout.decode("utf-8", errors="ignore").strip()
        except Exception:
            out = ""
        if log_fn:
            log_fn(f"❌ Error mezclando música (code {result.returncode}).")
            if err:
                log_fn(f"stderr: {err[-1000:]}")
            if out:
                log_fn(f"stdout: {out[-1000:]}")
        try:
            if temp_path != final_path and os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        return video_path

    if final_path == video_path:
        try:
            if os.path.exists(temp_path):
                os.replace(temp_path, video_path)
        except Exception:
            pass
        return video_path

    return final_path

def crear_outro_tiktok(
    image_path: str,
    output_path: str,
    duration: float = 3.0,
    text: str = "",
    font_size: int = 54,
    color: str = "#FFFFFF",
    log_fn=None
):
    """
    Crea un clip vertical 1080x1920 a partir de una imagen, con texto centrado.
    """
    duration = max(1.0, float(duration))
    color = (color or "#FFFFFF").strip()
    if not color.startswith("#"):
        color = "#" + color
    safe_text = (text or "").replace(":", "\\:").replace("'", "\\'")
    draw = ""
    if safe_text:
        draw = (
            f",drawtext=text='{safe_text}':"
            f"fontcolor={color}:fontsize={font_size}:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
        )
    filtro = (
        "scale=720:1280:force_original_aspect_ratio=increase,"
        "crop=720:1280"
        f"{draw}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", str(duration),
        "-vf", filtro,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]
    if log_fn:
        log_fn(f"🖼️ Creando tarjeta final: {os.path.basename(output_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if log_fn:
            err = (result.stderr or "").strip()
            log_fn(f"❌ Tarjeta final falló: {err[-300:]}")
        raise RuntimeError("No se pudo crear la tarjeta final.")

def dividir_video_ffmpeg(
    video_path: str,
    segundos_por_parte: float,
    out_dir: str,
    total_partes: int | None = None,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    crop_bars: bool = False,
    crop_top: float = 0.0,
    crop_bottom: float = 0.0,
    crop_scale_back: bool = True,
    log_fn=None
):
    """
    Divide un video en partes de N segundos. Guarda MP4s en out_dir.
    """
    asegurar_dir(out_dir)
    base_name = nombre_base_principal(video_path)
    duracion = obtener_duracion_segundos(video_path)
    start_sec = max(0.0, float(start_sec))
    if end_sec is None:
        end_sec = duracion
    else:
        end_sec = min(duracion, float(end_sec))
    if end_sec <= start_sec:
        return []
    rango = end_sec - start_sec
    if total_partes is None:
        total_partes = max(1, math.ceil(rango / segundos_por_parte))
    else:
        total_partes = max(1, int(total_partes))
    paths = []
    crop_filter = None
    manual_crop = None
    try:
        crop_top = float(crop_top)
        crop_bottom = float(crop_bottom)
    except Exception:
        crop_top = 0.0
        crop_bottom = 0.0
    crop_top = max(0.0, min(crop_top, 0.45))
    crop_bottom = max(0.0, min(crop_bottom, 0.45))
    if crop_top + crop_bottom >= 0.9:
        crop_top = 0.1
        crop_bottom = 0.1
    if crop_top > 0 or crop_bottom > 0:
        try:
            w, h = obtener_tamano_video(video_path)
            if crop_scale_back:
                manual_crop = f"crop=iw:ih*(1-{crop_top+crop_bottom:.4f}):0:ih*{crop_top:.4f},scale={w}:{h}"
            else:
                manual_crop = f"crop=iw:ih*(1-{crop_top+crop_bottom:.4f}):0:ih*{crop_top:.4f}"
        except Exception:
            manual_crop = f"crop=iw:ih*(1-{crop_top+crop_bottom:.4f}):0:ih*{crop_top:.4f}"
    if crop_bars:
        crop_params = detectar_crop_barras(video_path)
        if crop_params:
            try:
                w, h = obtener_tamano_video(video_path)
                if crop_scale_back:
                    crop_filter = f"crop={crop_params},scale={w}:{h}"
                else:
                    crop_filter = f"crop={crop_params}"
            except Exception:
                crop_filter = f"crop={crop_params}"
    if manual_crop:
        crop_filter = manual_crop

    for i in range(total_partes):
        if stop_control.should_stop():
            if log_fn:
                log_fn("Proceso detenido por el usuario.")
            break
        inicio = start_sec + i * segundos_por_parte
        if inicio >= end_sec:
            break
        duracion_parte = min(segundos_por_parte, max(0.1, end_sec - inicio))
        out_path = os.path.join(out_dir, f"{base_name}_parte_{i+1:03d}.mp4")

        if log_fn:
            log_fn(f"âœ‚ï¸ Generando video parte {i+1}/{total_partes}...")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", str(inicio),
            "-t", str(duracion_parte),
        ]
        if crop_filter:
            cmd += ["-vf", crop_filter]
        cmd += [
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            out_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        paths.append(out_path)

        if log_fn:
            log_fn(f"âœ” Video parte {i+1}/{total_partes} listo: {out_path}")

    return paths

def dividir_video_vertical_individual(
    video_path: str,
    segundos_por_parte: float,
    out_dir: str,
    posicion: str = "C",
    zoom: float = 1.0,
    bg_color: str = "black",
    motion: bool = False,
    motion_amount: float = 0.08,
    motion_period: float = 30.0,
    outro_enabled: bool = False,
    outro_image: str | None = None,
    outro_text: str = "",
    outro_seconds: float = 3.0,
    outro_font_size: int = 54,
    outro_color: str = "#FFFFFF",
    total_partes: int | None = None,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    log_fn=None
):
    """
    Divide un video en partes y genera versiones verticales 9:16 recortadas.
    posicion: C (centro), L (izquierda), R (derecha)
    """
    asegurar_dir(out_dir)
    base_name = nombre_base_principal(video_path)
    duracion = obtener_duracion_segundos(video_path)
    start_sec = max(0.0, float(start_sec))
    if end_sec is None:
        end_sec = duracion
    else:
        end_sec = min(duracion, float(end_sec))
    if end_sec <= start_sec:
        return []
    rango = end_sec - start_sec
    if total_partes is None:
        total_partes = max(1, math.ceil(rango / segundos_por_parte))
    else:
        total_partes = max(1, int(total_partes))

    pos = (posicion or "C").upper()
    if pos not in ("C", "L", "R"):
        pos = "C"
    if pos == "L":
        x_expr = "0"
    elif pos == "R":
        x_expr = "iw-720"
    else:
        x_expr = "(iw-1080)/2"

    try:
        zoom = float(zoom)
    except Exception:
        zoom = 1.0
    if zoom <= 0:
        zoom = 1.0

    color = (bg_color or "black").strip()
    if color.startswith("#") and len(color) == 7:
        color = "0x" + color[1:]

    target_w = 720
    target_h = 1280
    scaled_h = max(2, int(target_h * zoom))
    if scaled_h % 2 != 0:
        scaled_h += 1
    filtro = (
        f"scale=-2:{scaled_h},"
        f"crop=w='if(gte(iw,{target_w}),{target_w},iw)':"
        f"h='if(gte(ih,{target_h}),{target_h},ih)':"
        f"x='if(gte(iw,{target_w}),{x_expr},0)':"
        f"y='if(gte(ih,{target_h}),(ih-{target_h})/2,0)',"
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color={color}"
    )
    if motion:
        try:
            motion_amount = float(motion_amount)
        except Exception:
            motion_amount = 0.08
        try:
            motion_period = float(motion_period)
        except Exception:
            motion_period = 30.0
        motion_amount = max(0.0, min(motion_amount, 0.35))
        motion_period = max(2.0, motion_period)
        fps = obtener_fps(video_path)
        if fps <= 0:
            fps = 30.0
        period_frames = max(1, int(fps * motion_period))
        zoom_expr = f"1+{motion_amount}*(1-cos(2*PI*on/{period_frames}))/2"
        filtro += (
            f",zoompan=z='{zoom_expr}':"
            "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d=1:s={target_w}x{target_h}:fps={int(round(fps))}"
        )

    paths = []
    for i in range(total_partes):
        if stop_control.should_stop():
            if log_fn:
                log_fn("Proceso detenido por el usuario.")
            break
        inicio = start_sec + i * segundos_por_parte
        if inicio >= end_sec:
            break
        duracion_parte = min(segundos_por_parte, max(0.1, end_sec - inicio))
        out_path = os.path.join(out_dir, f"{base_name}_parte_{i+1:03d}.mp4")

        if log_fn:
            log_fn(f"Generando vertical parte {i+1}/{total_partes}...")

        temp_path = out_path
        if outro_enabled and outro_image and os.path.exists(outro_image):
            temp_path = os.path.join(out_dir, f"{base_name}_parte_{i+1:03d}_tmp.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", str(inicio),
            "-t", str(duracion_parte),
            "-vf", filtro,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-movflags", "+faststart",
            "-progress", "pipe:1",
            "-stats_period", "5",
            temp_path
        ]
        progress = {"sec": 0.0}

        def _read_stdout():
            if not proc.stdout:
                return
            for raw in proc.stdout:
                line = raw.strip()
                if line.startswith("out_time_ms="):
                    try:
                        ms = int(line.split("=", 1)[1].strip())
                        progress["sec"] = ms / 1_000_000.0
                    except Exception:
                        continue

        def _read_stderr():
            if not proc.stderr:
                return
            for raw in proc.stderr:
                line = raw.strip()
                if "time=" in line:
                    import re as _re
                    m = _re.search(r"time=([0-9:.]+)", line)
                    if not m:
                        continue
                    t = m.group(1)
                    try:
                        parts = t.split(":")
                        if len(parts) == 3:
                            h, m_, s = parts
                            sec = float(s) + int(m_) * 60 + int(h) * 3600
                        elif len(parts) == 2:
                            m_, s = parts
                            sec = float(s) + int(m_) * 60
                        else:
                            sec = float(parts[0])
                        progress["sec"] = sec
                    except Exception:
                        continue

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        t_out = threading.Thread(target=_read_stdout, daemon=True)
        t_err = threading.Thread(target=_read_stderr, daemon=True)
        t_out.start()
        t_err.start()

        last_log_time = 0.0
        last_percent = -1
        while proc.poll() is None:
            now = time.time()
            if log_fn and progress["sec"] > 0 and (now - last_log_time >= 5):
                pct = int(min(100.0, (progress["sec"] / duracion_parte) * 100.0))
                if pct != last_percent:
                    log_fn(f"Progreso parte {i+1}/{total_partes}: {pct}%")
                    last_percent = pct
                    last_log_time = now
            time.sleep(0.2)

        result_code = proc.wait()
        try:
            t_out.join(timeout=2)
            t_err.join(timeout=2)
        except Exception:
            pass
        try:
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()
        except Exception:
            pass
        if stop_control.should_stop():
            if log_fn:
                log_fn("Proceso detenido por el usuario.")
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            break
        if result_code != 0:
            if log_fn:
                err = ""
                try:
                    if proc.stderr:
                        err = (proc.stderr.read() or "").strip()
                except Exception:
                    err = ""
                log_fn(f"Error ffmpeg en parte {i+1}: {err[-400:]}")
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except Exception:
                pass
            continue

        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            if log_fn:
                log_fn(f"Error: salida vacia en parte {i+1}")
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            continue

        if outro_enabled and outro_image and os.path.exists(outro_image):
            try:
                if log_fn:
                    log_fn(f"🧾 Outro: img={outro_image}, dur={outro_seconds}s, text='{outro_text[:40]}'")
                has_audio = tiene_audio(temp_path)
                if log_fn:
                    log_fn(f"🔊 Audio en clip: {'si' if has_audio else 'no'}")
                    log_fn("🖼️ Preparando imagen final...")
                safe_text = (outro_text or "").replace(":", "\\:").replace("'", "\\'")
                draw = ""
                if safe_text:
                    if log_fn:
                        log_fn("✍️ Aplicando texto centrado...")
                    draw = (
                        f",drawtext=text='{safe_text}':"
                        f"fontcolor={outro_color}:fontsize={outro_font_size}:"
                        "x=(w-text_w)/2:y=(h-text_h)/2"
                    )
                if log_fn:
                    log_fn("🎬 Generando video final con tarjeta...")
                outro_filter = (
                    "scale=720:1280:force_original_aspect_ratio=increase,"
                    "crop=720:1280"
                    f"{draw}"
                )
                total_dur = float(duracion_parte) + float(outro_seconds)
                vf = (
                    f"[1:v]{outro_filter}[outro];"
                    f"[0:v]tpad=stop_mode=clone:stop_duration={outro_seconds}[v0];"
                    f"[v0][outro]overlay=enable='gte(t,{duracion_parte:.3f})'[v]"
                )
                cmd_outro = [
                    "ffmpeg", "-y",
                    "-i", temp_path,
                    "-loop", "1", "-i", outro_image,
                    "-filter_complex", vf,
                    "-map", "[v]",
                    "-c:v", "libx264",
                    "-movflags", "+faststart",
                    "-t", f"{total_dur:.3f}",
                    out_path
                ]
                video_res = subprocess.run(cmd_outro, capture_output=True, text=True)
                if video_res.returncode != 0:
                    if log_fn:
                        err = (video_res.stderr or "").strip()
                        log_fn(f"❌ Error creando outro: {err[-300:]}")
                    raise RuntimeError("No se pudo crear la tarjeta final.")
                if log_fn:
                    log_fn("✅ Video final generado.")

                if has_audio:
                    if log_fn:
                        log_fn("🎵 Separando audio original...")
                    audio_path = os.path.join(out_dir, f"{base_name}_parte_{i+1:03d}_audio.aac")
                    extra_cmd = [
                        "ffmpeg", "-y",
                        "-i", temp_path,
                        "-vn", "-acodec", "aac",
                        audio_path
                    ]
                    extra_res = subprocess.run(extra_cmd, capture_output=True, text=True)
                    if extra_res.returncode != 0:
                        if log_fn:
                            err = (extra_res.stderr or "").strip()
                            log_fn(f"❌ Error extrayendo audio: {err[-300:]}")
                        raise RuntimeError("No se pudo extraer audio.")

                    if log_fn:
                        log_fn("🔗 Uniendo audio con el video final...")
                    mux_cmd = [
                        "ffmpeg", "-y",
                        "-i", out_path,
                        "-i", audio_path,
                        "-map", "0:v:0",
                        "-map", "1:a:0",
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-af", f"apad=pad_dur={outro_seconds}",
                        "-t", f"{total_dur:.3f}",
                        out_path + ".tmp.mp4"
                    ]
                    mux_res = subprocess.run(mux_cmd, capture_output=True, text=True)
                    if mux_res.returncode != 0:
                        if log_fn:
                            err = (mux_res.stderr or "").strip()
                            log_fn(f"❌ Error reinsertando audio: {err[-300:]}")
                        raise RuntimeError("No se pudo reinsertar audio.")
                    try:
                        if os.path.exists(out_path + ".tmp.mp4"):
                            os.replace(out_path + ".tmp.mp4", out_path)
                    except Exception:
                        pass
                    try:
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                    except Exception:
                        pass
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception:
                    pass
            except Exception:
                # si falla el outro, dejar el clip original
                try:
                    if os.path.exists(temp_path) and temp_path != out_path:
                        os.replace(temp_path, out_path)
                except Exception:
                    pass
        elif outro_enabled:
            if log_fn:
                log_fn("⚠️ Outro activado pero sin imagen valida.")
        elif temp_path != out_path:
            try:
                os.replace(temp_path, out_path)
            except Exception:
                pass

        paths.append(out_path)
        if log_fn:
            log_fn(f"Vertical parte {i+1}/{total_partes} lista: {out_path}")

    return paths

def dividir_audio_ffmpeg(
    audio_path: str,
    segundos_por_parte: float,
    out_dir: str,
    total_partes: int | None = None,
    start_sec: float = 0.0,
    end_sec: float | None = None,
    log_fn=None
):
    """
    Divide un audio en partes de N segundos. Guarda MP3s en out_dir.
    """
    asegurar_dir(out_dir)
    duracion = obtener_duracion_segundos(audio_path)
    start_sec = max(0.0, float(start_sec))
    if end_sec is None:
        end_sec = duracion
    else:
        end_sec = min(duracion, float(end_sec))
    if end_sec <= start_sec:
        return []
    rango = end_sec - start_sec
    if total_partes is None:
        total_partes = max(1, math.ceil(rango / segundos_por_parte))
    else:
        total_partes = max(1, int(total_partes))
    paths = []

    for i in range(total_partes):
        if stop_control.should_stop():
            if log_fn:
                log_fn("Proceso detenido por el usuario.")
            break
        inicio = start_sec + i * segundos_por_parte
        if inicio >= end_sec:
            break
        duracion_parte = min(segundos_por_parte, max(0.1, end_sec - inicio))
        out_path = os.path.join(out_dir, f"parte_{i+1:03d}.mp3")

        if log_fn:
            log_fn(f"âœ‚ï¸ Generando audio parte {i+1}/{total_partes}...")

        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(inicio),
            "-t", str(duracion_parte),
            "-vn",
            "-acodec", "libmp3lame",
            "-b:a", "192k",
            out_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        paths.append(out_path)

        if log_fn:
            log_fn(f"âœ” Audio parte {i+1}/{total_partes} listo: {out_path}")

    return paths

def dividir_audio_ffmpeg_partes(audio_path: str, partes: int = 5, log_fn=None):
    """
    Divide un audio en N partes iguales usando ffmpeg.
    Devuelve una lista con las rutas de los archivos resultantes.
    log_fn: funciÃ³n opcional para escribir logs en la interfaz.
    """
    # Obtener duraciÃ³n del audio con ffprobe
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
        if stop_control.should_stop():
            if log_fn:
                log_fn("Proceso detenido por el usuario.")
            break
        inicio = i * duracion_segmento
        out_path = f"{base}_parte{i+1}.mp3"

        if log_fn:
            log_fn(f"âœ‚ï¸ Generando fragmento {i+1}/{partes}...")

        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-ss", str(inicio),
            "-t", str(duracion_segmento),
            "-vn",
            "-acodec", "libmp3lame",
            "-b:a", "192k",
            out_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        paths.append(out_path)

        if log_fn:
            log_fn(f"âœ” Fragmento {i+1}/{partes} listo: {out_path}")

    return paths

def _parse_srt_time(ts: str) -> float:
    # HH:MM:SS,mmm -> seconds
    try:
        hh, mm, rest = ts.split(":")
        ss, ms = rest.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0
    except Exception:
        return 0.0

def _format_srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hh = int(seconds // 3600)
    mm = int((seconds % 3600) // 60)
    ss = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 0
        ss += 1
        if ss >= 60:
            ss = 0
            mm += 1
            if mm >= 60:
                mm = 0
                hh += 1
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"

def combinar_srt_partes(srt_paths: list[str], offsets: list[float], out_path: str, log_fn=None) -> str:
    """
    Une varios SRT aplicando offsets de tiempo (en segundos).
    """
    if len(srt_paths) != len(offsets):
        raise RuntimeError("Cantidad de SRT y offsets no coincide.")
    combined = []
    idx = 1
    time_re = re.compile(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)")
    for path, offset in zip(srt_paths, offsets):
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = f.read().replace("\r\n", "\n")
        blocks = data.split("\n\n")
        for block in blocks:
            lines = [l for l in block.splitlines() if l.strip() != ""]
            if len(lines) < 2:
                continue
            m = time_re.search(lines[1])
            if not m:
                continue
            start = _parse_srt_time(m.group(1)) + offset
            end = _parse_srt_time(m.group(2)) + offset
            lines[0] = str(idx)
            lines[1] = f"{_format_srt_time(start)} --> {_format_srt_time(end)}"
            combined.append("\n".join(lines))
            idx += 1
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(combined))
    if log_fn:
        log_fn(f"SRT unido: {out_path}")
    return out_path

def limpiar_temp(path: str):
    """
    Borra un archivo temporal si existe.
    """
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"No se pudo borrar {path}: {e}")

def guardar_resumen_rango(
    video_path: str,
    base_name: str,
    minutos_por_parte: float,
    inicio_min: float | None,
    fin_min: float | None,
    partes_generadas: int,
    out_dir: str | None = None
) -> str:
    if out_dir is None:
        out_dir = os.path.join(output_base_dir(video_path), "resumenes")
    asegurar_dir(out_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    inicio_txt = "0.0" if inicio_min is None else str(inicio_min)
    fin_txt = "fin" if fin_min is None else str(fin_min)
    file_name = f"{base_name}_resumen_{ts}.txt"
    path = os.path.join(out_dir, file_name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("Resumen de corte\n")
        f.write(f"Fuente: {video_path}\n")
        f.write(f"Minutos por parte: {minutos_por_parte}\n")
        f.write(f"Rango usado (min): {inicio_txt} -> {fin_txt}\n")
        f.write(f"Partes generadas: {partes_generadas}\n")
    return path

def generar_vertical_tiktok(
    input_path: str,
    output_path: str,
    orden: str = "LR",
    recorte_top: float = 0.12,
    recorte_bottom: float = 0.12,
    log_fn=None
):
    """
    Crea un video vertical 9:16 (1080x1920) apilando izquierda/ derecha del original.
    """
    top_expr = "left" if orden.upper() == "LR" else "right"
    bottom_expr = "right" if orden.upper() == "LR" else "left"
    recorte_top = max(0.0, min(float(recorte_top), 0.4))
    recorte_bottom = max(0.0, min(float(recorte_bottom), 0.4))
    recorte_total = recorte_top + recorte_bottom
    if recorte_total >= 0.9:
        recorte_top = 0.05
        recorte_bottom = 0.05
    crop_params = detectar_crop_barras(input_path)
    if crop_params:
        base_filter = f"[0:v]crop={crop_params}[base];"
    else:
        base_filter = f"[0:v]crop=iw:ih*(1-{recorte_total}):0:ih*{recorte_top}[base];"

    recorte_total = recorte_top + recorte_bottom
    if recorte_total >= 0.9:
        recorte_top = 0.05
        recorte_bottom = 0.05
        recorte_total = recorte_top + recorte_bottom

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex",
        # Quitar barras negras arriba/abajo si existen
        base_filter +
        # Mitades izquierda/derecha + recorte extra para quitar barras en cada mitad
        f"[base]crop=iw/2:ih:0:0[left];"
        f"[base]crop=iw/2:ih:iw/2:0[right];"
        f"[left]crop=iw:ih*(1-{recorte_total}):0:ih*{recorte_top}[leftb];"
        f"[right]crop=iw:ih*(1-{recorte_total}):0:ih*{recorte_top}[rightb];"
        # Escalar a 1080x960 llenando (cover) y recortar excedente
        "[leftb]scale=1080:960:force_original_aspect_ratio=increase,"
        "crop=1080:960[leftc];"
        "[rightb]scale=1080:960:force_original_aspect_ratio=increase,"
        "crop=1080:960[rightc];"
        f"[{top_expr}c][{bottom_expr}c]vstack=inputs=2,setsar=1[v]",
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]
    if log_fn:
        log_fn(f"🎞️ Generando vertical: {os.path.basename(output_path)}")
        if orden.upper() == "LR":
            log_fn("🔀 Orden: izquierda arriba / derecha abajo")
        elif orden.upper() == "RL":
            log_fn("🔀 Orden: derecha arriba / izquierda abajo")
        else:
            log_fn("🔀 Orden: personalizado")
        log_fn("✂️ Recortando mitades y ajustando barras...")
        log_fn("🧩 Apilando en formato 9:16...")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def obtener_expresion_overlay(posicion: str, margen: int = 10) -> str:
    """
    Genera la expresión de overlay para FFmpeg según la posición indicada.
    """
    pos = (posicion or "centro").strip().lower()
    margen = max(0, int(margen))
    if pos in ("arriba", "top"):
        return f"(W-w)/2:{margen}"
    if pos in ("abajo", "bottom"):
        return f"(W-w)/2:H-h-{margen}"
    return f"(W-w)/2:(H-h)/2"


def generar_visualizador_audio(
    audio_path: str,
    output_path: str,
    width: int,
    height: int,
    estilo: str = "showwaves",
    color: str = "#FFFFFF",
    fps: int = 30,
    margen_horizontal: int = 0,
    exposicion: float = 0.0,
    contraste: float = 1.0,
    saturacion: float = 1.0,
    temperatura: float = 0.0,
    log_fn=None
):
    """
    Genera un video de visualizador con fondo transparente a partir de un audio.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"No se encontró el audio del visualizador: {audio_path}")
    width = max(32, int(width or 640))
    height = max(32, int(height or 160))
    width -= width % 2
    height -= height % 2
    width = max(2, width)
    height = max(2, height)
    fps = max(12, min(60, int(fps or 30)))
    estilo = (estilo or "showwaves").lower()
    if estilo not in ("showwaves", "showspectrum", "avectorscope"):
        estilo = "showwaves"
    color = (color or "#FFFFFF").strip()
    if not color.startswith("#"):
        color = "#" + color
    duration = obtener_duracion_segundos(audio_path)
    if duration <= 0:
        duration = 0.1
    exposicion = max(-1.0, min(1.0, float(exposicion)))
    contraste = max(0.2, min(2.5, float(contraste)))
    saturacion = max(0.0, min(3.0, float(saturacion)))
    temperatura = max(-1.0, min(1.0, float(temperatura)))

    temp_filter = ""
    if abs(temperatura) > 1e-3:
        gs = temperatura / 2.0
        temp_filter = f",colorbalance=rs={temperatura:.3f}:gs={gs:.3f}:bs={-temperatura:.3f}"

    waves_adjust = (
        f"[waves]eq=brightness={exposicion:.3f}:contrast={contraste:.3f}:saturation={saturacion:.3f}"
        f"{temp_filter}[waves_rgba];"
    )

    margen = max(0, int(margen_horizontal))
    pad_filter = (
        f"[over]pad=iw+{margen*2}:ih:{margen}:0:color=0x00000000[pad];[pad]format=rgba"
        if margen > 0 else
        "[over]format=rgba"
    )
    filter_complex = (
        f"[0:a]aformat=channel_layouts=mono,{estilo}=s={width}x{height}:mode=line:colors={color}[waves];"
        f"{waves_adjust}"
        f"color=color=0x00000000:s={width}x{height}:d={duration:.3f}[base];"
        "[base]format=rgba[bg];"
        "[bg][waves_rgba]overlay=format=auto:shortest=1[over];"
        f"{pad_filter}"
    )
    salida_dir = os.path.dirname(output_path)
    if salida_dir:
        asegurar_dir(salida_dir)
    cmd = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-pix_fmt", "yuva420p",
        "-c:v", "libx264",
        "-r", str(fps),
        "-an",
        "-shortest",
        output_path
    ]
    if log_fn:
        log_fn(f"🎚 Generando visualizador ({os.path.basename(output_path)})")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if log_fn:
            err = (result.stderr or "").strip()
            log_fn(f"❌ Visualizador falló: {err[-300:]}")
        raise RuntimeError("No se pudo generar el visualizador de audio.")
    return output_path


def overlay_visualizador(
    video_path: str,
    visual_path: str,
    output_path: str,
    posicion: str = "centro",
    margen: int = 10,
    opacidad: float = 0.75,
    modo_combinacion: str = "lighten",
    log_fn=None
):
    """
    Superpone el visualizador generado sobre el video original.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"No se encontró el video base: {video_path}")
    if not os.path.exists(visual_path):
        raise FileNotFoundError(f"No se encontró el visualizador generado: {visual_path}")
    salida_dir = os.path.dirname(output_path)
    if salida_dir:
        asegurar_dir(salida_dir)
    overlay_expr = obtener_expresion_overlay(posicion, margen)
    opacidad = max(0.0, min(1.0, float(opacidad)))
    blend = (modo_combinacion or "lighten").strip().lower()
    blend_map = {
        "normal": "normal",
        "darken": "darken",
        "multiply": "multiply",
        "lighten": "lighten",
        "screen": "screen",
        "overlay": "overlay",
    }
    blend_mode = blend_map.get(blend, "lighten")
    filtro = (
        f"[1:v]format=rgba,colorchannelmixer=aa={opacidad}[vis];"
        f"[0:v][vis]overlay={overlay_expr}:format=auto:shortest=1[over];"
        f"[over]format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", visual_path,
        "-filter_complex", filtro,
        "-map", "0:a?",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]
    if log_fn:
        log_fn(f"🧩 Aplicando overlay del visualizador ({posicion})")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if log_fn:
            err = (result.stderr or "").strip()
            log_fn(f"❌ Overlay falló: {err[-300:]}")
        raise RuntimeError("No se pudo superponer el visualizador al video.")
    return output_path


def overlay_image_temporizada(
    video_path: str,
    image_path: str,
    output_path: str,
    start_sec: float,
    duration: float,
    zoom: float = 1.0,
    log_fn=None
):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"No se encontró el video para overlay de imagen: {video_path}")
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"No se encontró la imagen overlay: {image_path}")
    if duration <= 0:
        raise ValueError("La duración del overlay debe ser mayor que cero.")
    zoom = max(0.1, min(float(zoom or 1.0), 3.0))
    enable_expr = f"between(t,{max(0, start_sec):.3f},{start_sec+duration:.3f})"
    filtro = (
        f"[1:v]format=rgba[imgsrc];"
        f"[imgsrc][0:v]scale2ref=w=iw*{zoom:.3f}:h=ih*{zoom:.3f}:force_original_aspect_ratio=decrease[img][base];"
        f"[base][img]overlay=x=(W-w)/2:y=(H-h)/2:enable='{enable_expr}'[v]"
    )
    salida_dir = os.path.dirname(output_path)
    if salida_dir:
        asegurar_dir(salida_dir)
    output_path = os.path.abspath(output_path)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-loop", "1", "-i", image_path,
        "-filter_complex", filtro,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-shortest",
        output_path
    ]
    if log_fn:
        log_fn(f"🖼️ Agregando imagen en {start_sec:.2f}s por {duration:.2f}s")
        log_fn(f"Filtro overlay: {filtro}")
        log_fn(f"Salida: {output_path}")
    if log_fn:
        log_fn("▶️ Ejecutando ffmpeg para overlay de imagen...")
    result = subprocess.run(cmd, capture_output=True, text=False)
    if result.returncode != 0:
        err = ""
        out = ""
        try:
            if result.stderr:
                err = result.stderr.decode("utf-8", errors="ignore").strip()
        except Exception:
            err = ""
        try:
            if result.stdout:
                out = result.stdout.decode("utf-8", errors="ignore").strip()
        except Exception:
            out = ""
        if log_fn:
            log_fn(f"❌ Overlay imagen fallo (code {result.returncode}).")
            if err:
                log_fn(f"stderr: {err[-1000:]}")
            if out:
                log_fn(f"stdout: {out[-1000:]}")
        raise RuntimeError(f"No se pudo aplicar la imagen overlay: {err[-500:]}")
    return output_path

def append_image_outro(
    video_path: str,
    image_path: str,
    output_path: str,
    duration: float = 3.0,
    log_fn=None
):
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"No se encontró el video base: {video_path}")
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"No se encontró la imagen final: {image_path}")
    duration = max(0.5, float(duration))
    vdur = obtener_duracion_segundos(video_path)
    if vdur <= 0:
        raise RuntimeError("Duración de video inválida.")
    w, h = obtener_tamano_video(video_path)
    total = vdur + duration
    filtro = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={duration:.3f}[v0];"
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[img];"
        f"[v0][img]overlay=enable='gte(t,{vdur:.3f})'[v]"
    )
    salida_dir = os.path.dirname(output_path)
    if salida_dir:
        asegurar_dir(salida_dir)
    output_path = os.path.abspath(output_path)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-loop", "1", "-i", image_path,
        "-filter_complex", filtro,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-t", f"{total:.3f}",
        "-movflags", "+faststart",
        output_path
    ]
    if log_fn:
        log_fn(f"🧩 Agregando imagen final por {duration:.2f}s")
    result = subprocess.run(cmd, capture_output=True, text=False)
    if result.returncode != 0:
        err = ""
        try:
            if result.stderr:
                err = result.stderr.decode("utf-8", errors="ignore").strip()
        except Exception:
            err = ""
        if log_fn:
            log_fn(f"❌ Imagen final fallo (code {result.returncode}).")
            if err:
                log_fn(f"stderr: {err[-1000:]}")
        raise RuntimeError(f"No se pudo agregar la imagen final: {err[-500:]}")
    return output_path

def _sanitize_color(color: str, default: str = "0x000000") -> str:
    if not color:
        return default
    c = color.strip()
    if c.startswith("#"):
        c = "0x" + c[1:]
    elif not c.startswith("0x"):
        if re.match(r"^[0-9a-fA-F]{6}$", c):
            c = "0x" + c
    if c.startswith("0x"):
        return "0x" + c[2:].upper()
    return c

def _escape_filter_path(path: str) -> str:
    p = path.replace("\\", "/")
    p = p.replace(":", "\\:")
    return p

def _create_temp_text_file(text: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".txt", prefix="fftxt_")
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(text)
    return _escape_filter_path(path)

def aplicar_fondo_imagen(
    input_path: str,
    output_path: str,
    imagen_path: str,
    estilo: str = "fill",
    target_size: tuple[int, int] | None = None,
    fg_scale: float = 0.92,
    inset_pct: tuple[float, float, float, float] | None = None,
    fg_zoom: float = 1.0,
    cintas: list[dict] | None = None,
    mensajes: list[dict] | None = None,
    bg_crop_top: float = 0.0,
    bg_crop_bottom: float = 0.0,
    log_fn=None
):
    """
    Aplica una imagen de fondo a un video.
    estilos: fill | fit | blur
    """
    estilo = (estilo or "fill").lower()
    if estilo not in ("fill", "fit", "blur"):
        estilo = "fill"

    if target_size is None:
        target_size = obtener_tamano_video(input_path)
    w, h = target_size
    # ffmpeg/libx264 requiere dimensiones pares
    if w % 2 != 0:
        w += 1
    if h % 2 != 0:
        h += 1

    fg_scale = max(0.5, min(float(fg_scale), 1.0))
    try:
        fg_zoom = float(fg_zoom)
    except Exception:
        fg_zoom = 1.0
    fg_zoom = max(0.5, min(fg_zoom, 2.0))
    fg_w = max(2, int(w * fg_scale))
    fg_h = max(2, int(h * fg_scale))
    if fg_w % 2 != 0:
        fg_w += 1
    if fg_h % 2 != 0:
        fg_h += 1
    if inset_pct:
        l, r, t, b = inset_pct
        l = max(0.0, min(float(l), 0.45))
        r = max(0.0, min(float(r), 0.45))
        t = max(0.0, min(float(t), 0.45))
        b = max(0.0, min(float(b), 0.45))
        content_w = max(2, int(w * (1 - l - r)))
        content_h = max(2, int(h * (1 - t - b)))
        fg_w = content_w
        fg_h = content_h

    if fg_zoom != 1.0:
        fg_w = max(2, int(fg_w * fg_zoom))
        fg_h = max(2, int(fg_h * fg_zoom))

    offset_x = "(W-w)/2"
    offset_y = "(H-h)/2"
    if inset_pct:
        l, r, t, b = inset_pct
        offset_x = f"{int(w * l)}"
        offset_y = f"{int(h * t)}"

    overlay_path = None
    if mensajes or cintas:
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        overlay_path = os.path.join(tempfile.gettempdir(), f"overlay_{uuid.uuid4().hex}.png")
        if mensajes:
            tmp_msg = _render_mensajes_on_background(imagen_path, w, h, mensajes, transparent=True)
            if not tmp_msg:
                raise RuntimeError("No se pudo renderizar mensaje con Pillow.")
            msg_img = Image.open(tmp_msg).convert("RGBA")
            overlay.alpha_composite(msg_img)
        if cintas:
            tmp_c = _render_cintas_on_background(imagen_path, w, h, cintas, transparent=True)
            if not tmp_c:
                raise RuntimeError("No se pudo renderizar cintas con Pillow.")
            c_img = Image.open(tmp_c).convert("RGBA")
            overlay.alpha_composite(c_img)
        overlay.save(overlay_path, "PNG")

    bg_filter_part = f"[0:v]scale={w}:{h}"
    try:
        bg_crop_top = float(bg_crop_top)
        bg_crop_bottom = float(bg_crop_bottom)
    except Exception:
        bg_crop_top = 0.0
        bg_crop_bottom = 0.0
    bg_crop_top = max(0.0, min(bg_crop_top, 0.45))
    bg_crop_bottom = max(0.0, min(bg_crop_bottom, 0.45))
    bg_crop_total = bg_crop_top + bg_crop_bottom
    if bg_crop_total > 0:
        crop_h_expr = f"trunc(ih*(1-{bg_crop_total:.4f})/2)*2"
        crop_y_expr = f"trunc(ih*{bg_crop_top:.4f}/2)*2"
        bg_filter_part += f",crop=iw:{crop_h_expr}:0:{crop_y_expr},scale={w}:{h}"

    if estilo == "blur":
        filtro = (
            f"{bg_filter_part},boxblur=20:1[bg];"
            f"[1:v]scale={fg_w}:{fg_h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay={offset_x}:{offset_y},setsar=1[v]"
        )
    elif estilo == "fit":
        filtro = (
            f"{bg_filter_part}[bg];"
            f"[1:v]scale={fg_w}:{fg_h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay={offset_x}:{offset_y},setsar=1[v]"
        )
    else:  # fill
        filtro = (
            f"{bg_filter_part}[bg];"
            f"[1:v]scale={fg_w}:{fg_h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay={offset_x}:{offset_y},setsar=1[v]"
        )

    # Cintas y mensajes renderizados en overlay PNG (frente).

    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", imagen_path, "-i", input_path]
    if overlay_path:
        cmd += ["-loop", "1", "-i", overlay_path]
        filtro = filtro.replace("[v]", "[base]")
        filtro = filtro.replace("[bg][fg]overlay=", "[bg][fg]overlay=")
        filtro += ";[base][2:v]overlay=0:0:format=auto[v]"
    cmd += [
        "-filter_complex", filtro,
        "-map", "[v]",
        "-map", "1:a?",
        "-shortest",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]
    if log_fn:
        log_fn(f"🖼️ Aplicando fondo ({estilo}): {os.path.basename(output_path)}")
        log_fn(f"Filtro fondo: {filtro}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and log_fn:
        err = (result.stderr or "").strip()
        log_fn(f"❌ Fondo falló: {err[-1000:]}")

def detectar_crop_barras(path: str) -> str | None:
    """
    Usa cropdetect de ffmpeg para detectar barras negras y devolver w:h:x:y.
    """
    try:
        w0, h0 = obtener_tamano_video(path)
    except Exception:
        w0, h0 = 0, 0

    try:
        dur = obtener_duracion_segundos(path)
    except Exception:
        dur = 0.0

    posiciones = [0.0]
    if dur > 0:
        posiciones.append(max(0.0, dur / 2.0))
        posiciones.append(max(0.0, dur - 5.0))

    best = None
    best_area = None

    for pos in posiciones:
        cmd = [
            "ffmpeg", "-hide_banner",
            "-ss", f"{pos:.3f}",
            "-i", path,
            "-t", "5",
            "-vf", "cropdetect=12:16:0",
            "-f", "null", "NUL"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        salida = result.stderr or ""
        matches = re.findall(r"crop=\\d+:\\d+:\\d+:\\d+", salida)
        if not matches:
            continue
        crop = matches[-1].replace("crop=", "")
        try:
            w, h, _x, _y = [int(x) for x in crop.split(":")]
        except Exception:
            continue
        if w0 > 0 and h0 > 0:
            if w < int(w0 * 0.6) or h < int(h0 * 0.6):
                continue
        area = w * h
        if best_area is None or area < best_area:
            best_area = area
            best = crop

    return best

def quemar_srt_en_video(
    video_path: str,
    srt_path: str,
    output_path: str,
    posicion: str = "bottom",
    font_size: int = 46,
    outline: int = 2,
    shadow: int = 1,
    force_position: bool = True,
    max_chars: int = 32,
    max_lines: int = 2,
    use_ass: bool = True,
    log_fn=None
) -> str:
    """
    Quema subtitulos .srt en un video usando ffmpeg.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if not os.path.exists(srt_path):
        raise RuntimeError("No se encontro el archivo SRT.")
    if os.path.getsize(srt_path) == 0 and log_fn:
        log_fn("Advertencia: el SRT esta vacio.")

    srt_use_path = srt_path
    if force_position:
        # Limpiar tags de alineacion embebidos en el SRT (anulan Alignment)
        try:
            with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
                srt_data = f.read()
            srt_data = re.sub(r"\{\\an\d+\}", "", srt_data)
            srt_data = re.sub(r"\{\\a\d+\}", "", srt_data)
            srt_data = re.sub(r"\{\\pos\([^)]+\)\}", "", srt_data)
            srt_data = re.sub(r"\{\\move\([^)]+\)\}", "", srt_data)
            srt_data = re.sub(r"\{\\org\([^)]+\)\}", "", srt_data)
            tmp_srt = os.path.join(tempfile.gettempdir(), f"srt_pos_{os.getpid()}.srt")
            with open(tmp_srt, "w", encoding="utf-8") as f:
                f.write(srt_data)
            srt_use_path = tmp_srt
            if log_fn:
                log_fn(f"Forzar posicion: SRT limpio -> {srt_use_path}")
        except Exception as e:
            if log_fn:
                log_fn(f"No se pudo limpiar SRT: {e}")
            srt_use_path = srt_path
    if log_fn:
        log_fn(f"SRT usado: {srt_use_path}")

    # ffmpeg subtitles filter needs escaped path on Windows
    srt_filter_path = srt_use_path
    if os.name == "nt":
        srt_filter_path = srt_filter_path.replace("\\", "/")
        srt_filter_path = srt_filter_path.replace(":", "\\:")
        srt_filter_path = srt_filter_path.replace(",", "\\,")
        srt_filter_path = srt_filter_path.replace("'", "\\'")
    _pos = (posicion or "bottom").lower()
    w, h = obtener_tamano_video(video_path)
    is_vertical = h > w
    # Zona segura: mas grande en vertical
    safe_area = int(h * (0.22 if is_vertical else 0.10))
    # Estimar altura del bloque para posicionamiento (match preview)
    try:
        max_lines = int(max_lines)
    except Exception:
        max_lines = 2
    if max_lines < 1:
        max_lines = 1
    line_height = font_size * 1.25
    subtitle_height = line_height * max_lines

    center_offset = int(h * (0.00 if is_vertical else 0.00))
    def _y_top_for_pos():
        if _pos == "top":
            return safe_area
        if _pos == "top-center":
            return (safe_area + (h - subtitle_height) / 2) / 2
        if _pos == "center":
            return (h - subtitle_height) / 2 + center_offset
        # bottom / bottom-center
        bottom_y = h - safe_area - subtitle_height
        if _pos == "bottom-center":
            center_y = (h - subtitle_height) / 2
            return (center_y + bottom_y) / 2
        return bottom_y

    y_top = _y_top_for_pos()
    margin_v_top = max(0, int(y_top))
    margin_v_bottom = max(0, int(h - y_top - subtitle_height))
    if _pos in ("top", "top-center"):
        alignment = 8
        margin_v = margin_v_top
    elif _pos == "center":
        alignment = 5
        margin_v = 0
    else:
        alignment = 2
        margin_v = margin_v_bottom

    try:
        font_size = int(font_size)
    except Exception:
        font_size = 46
    # No auto-scale: respetar el tamaño del usuario
    try:
        outline = int(outline)
    except Exception:
        outline = 2
    try:
        shadow = int(shadow)
    except Exception:
        shadow = 1

    # Preparar estilo
    if log_fn:
        log_fn(f"Estilo SRT: font={font_size}, outline={outline}, shadow={shadow}, pos={posicion}, marginV={margin_v}, vertical={is_vertical}")
    # Pre-calc position for \pos override (ASS)
    if alignment == 8:  # top
        y_anchor = y_top
    elif alignment == 5:  # center
        y_anchor = y_top + (subtitle_height / 2)
    else:  # bottom
        y_anchor = y_top + subtitle_height
    x_anchor = w / 2

    if use_ass:
        try:
            tmp_ass = os.path.join(tempfile.gettempdir(), f"srt_style_{os.getpid()}.ass")
            conv_cmd = [
                "ffmpeg", "-y",
                "-i", srt_use_path,
                tmp_ass
            ]
            conv_res = subprocess.run(conv_cmd, capture_output=True, text=True)
            if log_fn and conv_res.returncode != 0:
                log_fn(f"ASS convert error: {(conv_res.stderr or '')[-300:]}")
            ass_lines = []
            if not os.path.exists(tmp_ass):
                raise RuntimeError("No se genero el ASS temporal.")
            with open(tmp_ass, "r", encoding="utf-8", errors="ignore") as f:
                ass_lines = f.read().splitlines()
            new_lines = []
            in_styles = False
            in_script = False
            for line in ass_lines:
                low = line.strip().lower()
                if low.startswith("[script info]"):
                    in_script = True
                    new_lines.append(line)
                    continue
                if in_script and low.startswith("[v4+ styles]"):
                    in_script = False
                    in_styles = True
                    new_lines.append(line)
                    continue
                if in_script and low.startswith("playresx:"):
                    new_lines.append(f"PlayResX: {w}")
                    continue
                if in_script and low.startswith("playresy:"):
                    new_lines.append(f"PlayResY: {h}")
                    continue
                if line.strip().lower().startswith("[v4+ styles]"):
                    in_styles = True
                    new_lines.append(line)
                    continue
                if in_styles and line.strip().lower().startswith("format:"):
                    new_lines.append(line)
                    continue
                if in_styles and line.strip().lower().startswith("style:"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        fmt = parts[0] + ":"
                        vals = parts[1].split(",")
                        if len(vals) >= 23:
                            vals[1] = "Arial"
                            vals[2] = str(font_size)
                            vals[3] = "&H00FFFFFF"
                            vals[4] = "&H00000000"
                            vals[5] = "&H00000000"
                            vals[15] = "1"
                            vals[16] = str(outline)
                            vals[17] = str(shadow)
                            vals[18] = str(alignment)
                            vals[19] = "20"
                            vals[20] = "20"
                            vals[21] = str(margin_v)
                            line = fmt + ",".join(vals)
                    new_lines.append(line)
            with open(tmp_ass, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
            srt_use_path = tmp_ass
        except Exception as e:
            if log_fn:
                log_fn(f"No se pudo ajustar ASS: {e}")

    srt_filter_path = srt_use_path
    if os.name == "nt":
        srt_filter_path = srt_filter_path.replace("\\", "/")
        srt_filter_path = srt_filter_path.replace(":", "\\:")
        srt_filter_path = srt_filter_path.replace(",", "\\,")
        srt_filter_path = srt_filter_path.replace("'", "\\'")

    if use_ass and srt_use_path.lower().endswith(".ass"):
        vf = f"ass='{srt_filter_path}'"
    else:
        style = (
            f"Fontname=Arial,Fontsize={font_size},"
            f"Outline={outline},Shadow={shadow},"
            f"Alignment={alignment},MarginV={margin_v}"
        )
        vf = f"subtitles='{srt_filter_path}':force_style='{style}'"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]
    if log_fn:
        log_fn(f"Quemando SRT: {os.path.basename(output_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or "").strip()
        if log_fn:
            log_fn(f"❌ Error quemando SRT: {err[-500:]}")
        raise RuntimeError("No se pudo quemar el SRT en el video.")
    return output_path
