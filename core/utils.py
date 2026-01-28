import os
import subprocess
import re
import math
import tempfile
from datetime import datetime

def asegurar_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def nombre_salida_por_video(video_path: str, base_dir="output/transcripciones", parte=None) -> str:
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
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920"
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
    log_fn=None
):
    """
    Divide un video en partes de N segundos. Guarda MP4s en out_dir.
    """
    asegurar_dir(out_dir)
    base_name = nombre_base_fuente(video_path)
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

    for i in range(total_partes):
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
    base_name = nombre_base_fuente(video_path)
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
        x_expr = "iw-1080"
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

    target_w = 1080
    target_h = 1920
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
            temp_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            if log_fn:
                err = (result.stderr or "").strip()
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
                    "scale=1080:1920:force_original_aspect_ratio=increase,"
                    "crop=1080:1920"
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
    out_dir: str = "output/resumenes"
) -> str:
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
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def aplicar_fondo_imagen(
    input_path: str,
    output_path: str,
    imagen_path: str,
    estilo: str = "fill",
    target_size: tuple[int, int] | None = None,
    fg_scale: float = 0.92,
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

    fg_scale = max(0.5, min(float(fg_scale), 1.0))
    fg_w = max(2, int(w * fg_scale))
    fg_h = max(2, int(h * fg_scale))

    if estilo == "blur":
        filtro = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},boxblur=20:1[bg];"
            f"[1:v]scale={fg_w}:{fg_h}:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
        )
    elif estilo == "fit":
        filtro = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}[bg];"
            f"[1:v]scale={fg_w}:{fg_h}:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
        )
    else:  # fill
        filtro = (
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h}[bg];"
            f"[1:v]scale={fg_w}:{fg_h}:force_original_aspect_ratio=decrease[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", imagen_path,
        "-i", input_path,
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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and log_fn:
        err = (result.stderr or "").strip()
        log_fn(f"❌ Fondo falló: {err[-300:]}")

def detectar_crop_barras(path: str) -> str | None:
    """
    Usa cropdetect de ffmpeg para detectar barras negras y devolver w:h:x:y.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-i", path,
        "-t", "5",
        "-vf", "cropdetect=24:16:0",
        "-f", "null", "NUL"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    salida = result.stderr or ""
    matches = re.findall(r"crop=\\d+:\\d+:\\d+:\\d+", salida)
    if not matches:
        return None
    return matches[-1].replace("crop=", "")

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
                    in_styles = False
                    continue
                if line.strip().lower().startswith("dialogue:"):
                    parts = line.split(",", 9)
                    if len(parts) == 10:
                        text = parts[9]
                        text = re.sub(r"\{\\pos\([^)]+\)\}", "", text)
                        text = re.sub(r"\{\\move\([^)]+\)\}", "", text)
                        text = re.sub(r"\{\\org\([^)]+\)\}", "", text)
                        text = re.sub(r"\{\\an\d+\}", "", text)
                        text = re.sub(r"\{\\a\d+\}", "", text)
                        pos_tag = f"{{\\pos({int(x_anchor)},{int(y_anchor)})}}"
                        parts[9] = pos_tag + text
                        line = ",".join(parts)
                new_lines.append(line)
            with open(tmp_ass, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
            srt_use_path = tmp_ass
            if log_fn:
                log_fn(f"ASS usado: {srt_use_path}")
        except Exception as e:
            if log_fn:
                log_fn(f"No se pudo preparar ASS: {e}")

    # ffmpeg subtitles filter needs escaped path on Windows
    srt_filter_path = srt_use_path
    if os.name == "nt":
        srt_filter_path = srt_filter_path.replace("\\", "/")
        srt_filter_path = srt_filter_path.replace(":", "\\:")
        srt_filter_path = srt_filter_path.replace(",", "\\,")
        srt_filter_path = srt_filter_path.replace("'", "\\'")
    if use_ass:
        vf = f"ass='{srt_filter_path}'"
    else:
        style_alignment = alignment
        style_margin_v = margin_v
        if _pos == "center":
            # Con subtitles/force_style el center ignora marginV, por eso usamos bottom-center
            style_alignment = 2
            style_margin_v = margin_v_bottom
        style = (
            f"Alignment={style_alignment},MarginV={style_margin_v},MarginL=20,MarginR=20,"
            f"Fontsize={font_size},Outline={outline},Shadow={shadow},"
            "BorderStyle=1,"
            "PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&"
        )
        style_escaped = style.replace(":", "\\:").replace(",", "\\,").replace("'", "\\'")
        vf = f"subtitles='{srt_filter_path}':charenc=UTF-8:force_style='{style_escaped}'"

    if log_fn:
        log_fn(f"ffmpeg filter: {vf}")
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if log_fn and result.stderr:
        tail = (result.stderr or "").strip()
        if tail:
            log_fn(f"ffmpeg: {tail[-300:]}")
    if result.returncode != 0:
        if log_fn:
            err = (result.stderr or "").strip()
            log_fn(f"Error quemando SRT: {err[-400:]}")
        raise RuntimeError("No se pudo quemar el SRT en el video.")
    try:
        if srt_use_path != srt_path and os.path.exists(srt_use_path):
            os.remove(srt_use_path)
    except Exception:
        pass
    return output_path

