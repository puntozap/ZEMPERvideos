import os
import math
import subprocess
from core.extractor import extraer_audio
from core.utils import (
    dividir_audio_ffmpeg,
    dividir_audio_ffmpeg_partes,
    combinar_srt_partes,
    dividir_video_ffmpeg,
    dividir_video_vertical_individual,
    quemar_srt_en_video,
    nombre_base_principal,
    output_base_dir,
    next_correlative_dir,
    output_subtitulados_dir,
    guardar_resumen_rango,
    generar_vertical_tiktok,
    aplicar_fondo_imagen,
    obtener_duracion_segundos,
)
from core.transcriber import transcribir_srt
import re
from core import stop_control


def procesar_video(
    video_path: str,
    es_youtube: bool,
    es_audio: bool = False,
    minutos_por_parte: float = 5,
    inicio_min: float | None = None,
    fin_min: float | None = None,
    dividir_video: bool = True,
    vertical_tiktok: bool = False,
    vertical_orden: str = "LR",
    recorte_top: float = 0.12,
    recorte_bottom: float = 0.12,
    generar_srt: bool = True,
    fondo_path: str | None = None,
    fondo_estilo: str = "fill",
    fondo_escala: float = 0.92,
    solo_video: bool = False,
    barra=None,
    logs=None,
):
    """
    Procesa un archivo (video o audio):
    - Extrae audio si es video
    - Divide en N partes (sin transcripcion)
    """

    try:
        if logs: logs("Iniciando procesamiento...")
        base_name = nombre_base_principal(video_path)
        base_dir = output_base_dir(video_path)
        output_videos = []
        cortes_dir = None
        vertical_dir = None
        partes_video = []
        segundos_por_parte = max(1.0, float(minutos_por_parte) * 60)
        start_sec = float(inicio_min) * 60 if inicio_min is not None else 0.0
        end_sec = float(fin_min) * 60 if fin_min is not None else None
        if end_sec is not None and end_sec <= start_sec:
            if logs: logs("Rango invalido: el minuto final debe ser mayor al inicial.")
            return

        if es_youtube:
            if logs: logs("YouTube desactivado por ahora.")
            return

        # 1. Preparar audio (opcional)
        audio_path = None
        if not solo_video:
            if es_audio:
                audio_path = video_path
                if logs: logs(f"Audio seleccionado: {video_path}")
            else:
                if logs: logs(f"Video seleccionado: {video_path}")
                if logs: logs("Extrayendo audio...")
                audio_dir_base = os.path.join(base_dir, "audios")
                os.makedirs(audio_dir_base, exist_ok=True)
                audio_path = os.path.join(audio_dir_base, f"{base_name}_original.mp3")
                audio_path = extraer_audio(video_path, audio_path, logs if logs else None)
                if logs: logs(f"Audio original guardado: {audio_path}")
        else:
            if logs: logs(f"Video seleccionado: {video_path}")

        # 2. Dividir video (opcional, solo local)
        if not es_audio and dividir_video:
            if vertical_tiktok:
                if logs: logs("Generando vertical TikTok sin cortes normales...")
                vertical_dir = next_correlative_dir(base_dir, "verticales", "vertical-corte")
                partes_video = []
                total_partes = max(1, math.ceil((end_sec - start_sec) / segundos_por_parte)) if end_sec else None
                for i in range(total_partes or 0):
                    if stop_control.should_stop():
                        if logs: logs("Proceso detenido por el usuario.")
                        return
                    inicio = start_sec + i * segundos_por_parte
                    if end_sec is not None and inicio >= end_sec:
                        break
                    duracion_parte = min(segundos_por_parte, max(0.1, (end_sec - inicio) if end_sec else segundos_por_parte))
                    if logs: logs(f"Generando vertical: parte {i+1}")
                    tmp_out = os.path.join(vertical_dir, f"{base_name}_parte_{i+1:03d}_tmp.mp4")
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", video_path,
                        "-ss", str(inicio),
                        "-t", str(duracion_parte),
                        "-c:v", "libx264",
                        "-c:a", "aac",
                        "-movflags", "+faststart",
                        tmp_out
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    partes_video.append(tmp_out)
                if logs: logs(f"Vertical TikTok: partes base {len(partes_video)}")
            else:
                if logs: logs("Dividiendo video en partes...")
                cortes_dir = os.path.join(base_dir, "cortes")
                partes_video = dividir_video_ffmpeg(
                    video_path,
                    segundos_por_parte=segundos_por_parte,
                    out_dir=cortes_dir,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    log_fn=logs if logs else None,
                )
                if logs: logs(f"Video dividido en {len(partes_video)} fragmentos")
                output_videos = partes_video

            if fondo_path and os.path.exists(fondo_path) and partes_video:
                fondo_dir = os.path.join(os.path.dirname(partes_video[0]), "background")
                os.makedirs(fondo_dir, exist_ok=True)
                for parte in partes_video:
                    if stop_control.should_stop():
                        if logs: logs("Proceso detenido por el usuario.")
                        return
                    nombre = os.path.splitext(os.path.basename(parte))[0]
                    out_path = os.path.join(fondo_dir, f"{nombre}_bg.mp4")
                    aplicar_fondo_imagen(
                        parte,
                        out_path,
                        fondo_path,
                        estilo=fondo_estilo,
                        fg_scale=fondo_escala,
                        log_fn=logs if logs else None
                    )

            if vertical_tiktok and partes_video:
                for idx, parte in enumerate(partes_video):
                    if stop_control.should_stop():
                        if logs: logs("Proceso detenido por el usuario.")
                        return
                    nombre = os.path.splitext(os.path.basename(parte))[0]
                    if nombre.endswith("_tmp"):
                        nombre = nombre[:-4]
                    out_path = os.path.join(os.path.dirname(parte), f"{nombre}_vertical.mp4")
                    orden_actual = vertical_orden
                    if vertical_orden == "ALT":
                        orden_actual = "LR" if (idx % 2 == 0) else "RL"
                    generar_vertical_tiktok(
                        parte,
                        out_path,
                        orden=orden_actual,
                        recorte_top=recorte_top,
                        recorte_bottom=recorte_bottom,
                        log_fn=logs if logs else None
                    )
                    output_videos.append(out_path)
                    if os.path.basename(parte).endswith("_tmp.mp4"):
                        try:
                            os.remove(parte)
                        except Exception:
                            pass
                if fondo_path and os.path.exists(fondo_path):
                    vertical_bg_dir = os.path.join(os.path.dirname(partes_video[0]), "background")
                    os.makedirs(vertical_bg_dir, exist_ok=True)
                    for parte in partes_video:
                        if stop_control.should_stop():
                            if logs: logs("Proceso detenido por el usuario.")
                            return
                        nombre = os.path.splitext(os.path.basename(parte))[0]
                        if nombre.endswith("_tmp"):
                            nombre = nombre[:-4]
                        in_path = os.path.join(os.path.dirname(parte), f"{nombre}_vertical.mp4")
                        out_path = os.path.join(vertical_bg_dir, f"{nombre}_vertical_bg.mp4")
                        aplicar_fondo_imagen(
                            in_path,
                            out_path,
                            fondo_path,
                            estilo=fondo_estilo,
                            target_size=(1080, 1920),
                            fg_scale=fondo_escala,
                            log_fn=logs if logs else None
                        )

        elif not es_audio:
            output_videos = [video_path]

        partes_audio = []
        if not solo_video:
            # 3. Dividir audio en MP3
            if logs: logs("Dividiendo audio en partes...")
            audio_dir = os.path.join(base_dir, "audios")
            partes_audio = dividir_audio_ffmpeg(
                audio_path,
                segundos_por_parte=segundos_por_parte,
                out_dir=audio_dir,
                start_sec=start_sec,
                end_sec=end_sec,
                log_fn=logs if logs else None,
            )
            if logs: logs(f"Audio dividido en {len(partes_audio)} fragmentos")

            # 4. Subtitulos (SRT)
            if generar_srt and partes_audio:
                subs_dir = os.path.join(base_dir, "subtitulos")
                for idx, parte in enumerate(partes_audio, start=1):
                    if logs: logs(f"Generando SRT {idx}/{len(partes_audio)}...")
                    srt_path = transcribir_srt(parte, subs_dir, idioma="es", model_size="base")
                    if logs: logs(f"SRT listo: {srt_path}")

        # 5. Guardar resumen
        resumen_path = guardar_resumen_rango(
            video_path=video_path,
            base_name=base_name,
            minutos_por_parte=minutos_por_parte,
            inicio_min=inicio_min,
            fin_min=fin_min,
            partes_generadas=len(partes_audio),
        )
        if logs: logs(f"Resumen creado: {resumen_path}")

        # 6. (Temporal) no transcribir ni generar textos
        if partes_audio:
            for idx, _parte in enumerate(partes_audio, start=1):
                if logs: logs(f"Parte {idx}/{len(partes_audio)} lista (sin transcripcion).")
                if barra: barra.set(idx / len(partes_audio))

        return {
            "videos": output_videos,
            "base_dir": base_dir,
            "cortes_dir": cortes_dir,
            "vertical_dir": vertical_dir,
        }

    except Exception as e:
        if logs: logs(f"Error: {e}")
        raise e
    finally:
        if barra: barra.set(0)


def procesar_corte_individual(
    video_path: str,
    minutos_por_parte: float = 5,
    inicio_min: float | None = None,
    fin_min: float | None = None,
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
    barra=None,
    logs=None,
):
    """
    Corta un video en partes y genera versiones verticales 9:16.
    posicion: C (centro), L (izquierda), R (derecha)
    """
    try:
        if logs: logs("Iniciando corte individual...")
        base_dir = output_base_dir(video_path)
        output_videos = []
        cortes_dir = None
        vertical_dir = None
        segundos_por_parte = max(1.0, float(minutos_por_parte) * 60)
        start_sec = float(inicio_min) * 60 if inicio_min is not None else 0.0
        end_sec = float(fin_min) * 60 if fin_min is not None else None
        if end_sec is not None and end_sec <= start_sec:
            if logs: logs("Rango invalido: el minuto final debe ser mayor al inicial.")
            return

        vertical_dir = next_correlative_dir(base_dir, "verticales", "vertical-individual")
        partes = dividir_video_vertical_individual(
            video_path,
            segundos_por_parte=segundos_por_parte,
            out_dir=vertical_dir,
            posicion=posicion,
            zoom=zoom,
            bg_color=bg_color,
            motion=motion,
            motion_amount=motion_amount,
            motion_period=motion_period,
            outro_enabled=outro_enabled,
            outro_image=outro_image,
            outro_text=outro_text,
            outro_seconds=outro_seconds,
            outro_font_size=outro_font_size,
            outro_color=outro_color,
            start_sec=start_sec,
            end_sec=end_sec,
            log_fn=logs if logs else None,
        )
        if logs: logs(f"Corte individual generado: {len(partes)} partes")
        output_videos = partes
        return {
            "videos": output_videos,
            "base_dir": base_dir,
            "cortes_dir": cortes_dir,
            "vertical_dir": vertical_dir,
        }
    except Exception as e:
        if logs: logs(f"Error: {e}")
        raise e
    finally:
        if barra: barra.set(0)


def procesar_srt(
    path: str,
    es_audio: bool,
    idioma: str | None = "es",
    model_size: str = "base",
    temperature: float | None = None,
    beam_size: int | None = None,
    logs=None,
):
    """
    Genera un .srt a partir de un video o audio.
    """
    try:
        if logs: logs("Iniciando generacion de SRT...")
        file_base = os.path.splitext(os.path.basename(path))[0]
        base_dir = output_base_dir(path)
        if es_audio:
            audio_path = path
            if logs: logs(f"Audio seleccionado: {path}")
        else:
            if logs: logs(f"Video seleccionado: {path}")
            audio_dir_base = os.path.join(base_dir, "audios")
            os.makedirs(audio_dir_base, exist_ok=True)
            audio_path = os.path.join(audio_dir_base, f"{file_base}_srt_source.mp3")
            if logs: logs("Extrayendo audio para SRT...")
            extraer_audio(path, audio_path, logs if logs else None)
        subs_dir = os.path.join(base_dir, "subtitulos")
        dur = obtener_duracion_segundos(audio_path)
        if dur > 300:
            partes = 6
            if logs: logs(f"Duracion > 5 min. Dividiendo audio en {partes} partes...")
            partes_paths = dividir_audio_ffmpeg_partes(audio_path, partes=partes, log_fn=logs if logs else None)
            srt_parts = []
            offsets = []
            offset = 0.0
            for idx, parte in enumerate(partes_paths, start=1):
                if stop_control.should_stop():
                    if logs: logs("Proceso detenido por el usuario.")
                    return
                if logs: logs(f"Transcribiendo parte {idx}/{len(partes_paths)}...")
                srt_p = transcribir_srt(
                    parte,
                    subs_dir,
                    idioma=idioma or "",
                    model_size=model_size,
                    temperature=temperature,
                    beam_size=beam_size
                )
                srt_parts.append(srt_p)
                offsets.append(offset)
                try:
                    offset += obtener_duracion_segundos(parte)
                except Exception:
                    pass
            out_path = os.path.join(subs_dir, f"{file_base}_completo.srt")
            combinar_srt_partes(srt_parts, offsets, out_path, log_fn=logs if logs else None)
            if logs: logs(f"SRT final listo: {out_path}")
            return out_path
        else:
            if stop_control.should_stop():
                if logs: logs("Proceso detenido por el usuario.")
                return
            if logs: logs("Transcribiendo...")
            srt_path = transcribir_srt(
                audio_path,
                subs_dir,
                idioma=idioma or "",
                model_size=model_size,
                temperature=temperature,
                beam_size=beam_size
            )
            if logs: logs(f"SRT listo: {srt_path}")
            return srt_path
    except Exception as e:
        if logs: logs(f"Error: {e}")
        raise e


def procesar_quemar_srt(
    video_path: str,
    srt_path: str,
    posicion: str = "bottom",
    font_size: int = 46,
    outline: int = 2,
    shadow: int = 1,
    force_position: bool = True,
    max_chars: int = 32,
    max_lines: int = 2,
    use_ass: bool = True,
    logs=None,
):
    """
    Quema un .srt en un video y guarda en output/<base>/subtitulados
    o en el mismo folder si viene de verticales.
    """
    try:
        if logs: logs("Iniciando quemado de SRT...")
        try:
            from core.utils import obtener_duracion_segundos
            dur = obtener_duracion_segundos(video_path)
            if logs: logs(f"Duracion video: {dur:.2f}s")
        except Exception:
            dur = None

        try:
            with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
                data = f.read()
            m = re.search(r"(\d+:\d+:\d+,\d+)\s*-->\s*(\d+:\d+:\d+,\d+)", data)
            if m and logs:
                logs(f"Primer tiempo SRT: {m.group(1)} -> {m.group(2)}")
        except Exception:
            pass
        out_dir = output_subtitulados_dir(video_path)
        os.makedirs(out_dir, exist_ok=True)
        file_base = os.path.splitext(os.path.basename(video_path))[0]
        out_path = os.path.join(out_dir, f"{file_base}_subt.mp4")
        quemar_srt_en_video(
            video_path,
            srt_path,
            out_path,
            posicion=posicion,
            font_size=font_size,
            outline=outline,
            shadow=shadow,
            force_position=force_position,
            max_chars=max_chars,
            max_lines=max_lines,
            use_ass=use_ass,
            log_fn=logs
        )
        if logs: logs(f"Video subtitulado listo: {out_path}")
    except Exception as e:
        if logs: logs(f"Error: {e}")
        raise e




