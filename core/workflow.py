import os
import math
import subprocess
import uuid
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
    obtener_tamano_video,
    asegurar_dir,
    generar_visualizador_audio,
    overlay_visualizador,
    overlay_image_temporizada,
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
    visualizador: bool = False,
    posicion_visualizador: str = "centro",
    color_visualizador: str = "#FFFFFF",
    margen_visualizador: int = 0,
    opacidad_visualizador: float = 0.65,
    exposicion_visualizador: float = 0.0,
    contraste_visualizador: float = 1.0,
    saturacion_visualizador: float = 1.0,
    temperatura_visualizador: float = 0.0,
    modo_visualizador: str = "lighten",
    overlay_image: str | None = None,
    overlay_start: float = 0.0,
    overlay_duration: float = 2.0,
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

            if visualizador and partes_audio and output_videos:
                original_outputs = output_videos[:]
                visualizado = []
                visual_dir = os.path.join(base_dir, "visualizador")
                if logs:
                    logs("Visualizador activado: generando onda y aplicando overlay...")
                for idx, (audio_seg, video_seg) in enumerate(zip(partes_audio, original_outputs), start=1):
                    try:
                        width, height = obtener_tamano_video(video_seg)
                        wave_height = max(64, min(height, int(height * 0.18)))
                        wave_path = os.path.join(visual_dir, f"{base_name}_parte_{idx:03d}_wave.mp4")
                        overlay_path = os.path.join(visual_dir, f"{base_name}_parte_{idx:03d}_wave_out.mp4")
                        generar_visualizador_audio(
                            audio_path=audio_seg,
                            output_path=wave_path,
                            width=width,
                            height=wave_height,
                            color=color_visualizador,
                            margen_horizontal=margen_visualizador,
                            exposicion=exposicion_visualizador,
                            contraste=contraste_visualizador,
                            saturacion=saturacion_visualizador,
                            temperatura=temperatura_visualizador,
                            log_fn=logs
                        )
                        overlay_visualizador(
                            video_path=video_seg,
                            visual_path=wave_path,
                            output_path=overlay_path,
                            posicion=posicion_visualizador,
                            opacidad=opacidad_visualizador,
                            modo_combinacion=modo_visualizador,
                            log_fn=logs
                        )
                        final_path = overlay_path
                        try:
                            if overlay_image and os.path.exists(overlay_image) and overlay_duration > 0:
                                image_overlay_path = os.path.join(
                                    visual_dir,
                                    f"{base_name}_parte_{idx:03d}_image.mp4"
                                )
                                overlay_image_temporizada(
                                    overlay_path,
                                    overlay_image,
                                    image_overlay_path,
                                    overlay_start,
                                    overlay_duration,
                                    log_fn=logs
                                )
                                final_path = image_overlay_path
                        except Exception as exc:
                            if logs:
                                logs(f"Advertencia: no se pudo agregar imagen en parte {idx} ({exc})")
                        visualizado.append(final_path)
                    except Exception as exc:
                        if logs:
                            logs(f"Advertencia: visualizador parte {idx} no se aplicó ({exc})")
                        visualizado.append(video_seg)
            if len(original_outputs) > len(visualizado):
                visualizado.extend(original_outputs[len(visualizado):])
            output_videos = visualizado

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


def _ffmpeg_escape_path(path: str) -> str:
    return path.replace("'", r"'\\''")


def _extraer_segmento_audio(source: str, dest: str, start: float, duration: float, logs=None):
    if duration <= 0:
        raise ValueError("La duración del segmento debe ser mayor que cero.")
    cmd = ["ffmpeg", "-y"]
    if start > 0:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", source]
    cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-acodec", "libmp3lame", "-b:a", "192k", dest]
    os.makedirs(os.path.dirname(dest), exist_ok=True) if os.path.dirname(dest) else None
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err = (result.stderr or "").strip()
        if logs: logs(f"❌ Creación de segmento de audio falló: {err[-300:]}")
        raise RuntimeError("No se pudo generar el segmento de audio.")
    return dest


def _concat_visualizadores(sources: list[str], output_path: str, logs=None):
    if len(sources) == 0:
        raise ValueError("No hay segmentos para concatenar.")
    if len(sources) == 1:
        os.replace(sources[0], output_path)
        return output_path
    list_path = os.path.join(os.path.dirname(output_path), f"concat_{uuid.uuid4().hex}.txt")
    try:
        with open(list_path, "w", encoding="utf-8") as fh:
            for src in sources:
                fh.write(f"file '{_ffmpeg_escape_path(os.path.abspath(src))}'\n")
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_path,
            "-c",
            "copy",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            err = (result.stderr or "").strip()
            if logs: logs(f"❌ Concatenación falló: {err[-300:]}")
            raise RuntimeError("No se pudo concatenar los visualizadores.")
    finally:
        try:
            os.remove(list_path)
        except Exception:
            pass
    return output_path


def _generar_visualizador_segmentado(
    audio_path: str,
    visual_dir: str,
    base_name: str,
    salida_visual: str,
    width: int,
    height: int,
    estilo: str,
    color: str,
    fps: int,
    margen_horizontal: int,
    exposicion: float,
    contraste: float,
    saturacion: float,
    temperatura: float,
    segmento_segundos: float,
    logs=None,
    progress_callback=None,
):
    duration = obtener_duracion_segundos(audio_path)
    if duration <= 0:
        duration = 0.1
    segmento_segundos = max(10.0, min(segmento_segundos or 60.0, duration))
    total_segments = max(1, int(math.ceil(duration / segmento_segundos)))
    acumulado = None
    start = 0.0
    for idx in range(total_segments):
        if stop_control.should_stop():
            raise RuntimeError("Proceso detenido por el usuario.")
        parte_duracion = min(segmento_segundos, duration - start)
        if parte_duracion <= 0:
            break
        segmento_audio = os.path.join(
            visual_dir,
            f"{base_name}_segmento_audio_{idx+1:03d}.mp3",
        )
        _extraer_segmento_audio(audio_path, segmento_audio, start, parte_duracion, logs=logs)
        if logs:
            logs(f"🧱 Segmento {idx+1}/{total_segments}: {parte_duracion:.2f}s (desde {start:.2f}s)")
        segmento_video = os.path.join(
            visual_dir,
            f"{base_name}_segmento_vis_{idx+1:03d}.mp4",
        )
        generar_visualizador_audio(
            segmento_audio,
            segmento_video,
            width,
            height,
            estilo=estilo,
            color=color,
            fps=fps,
            margen_horizontal=margen_horizontal,
            exposicion=exposicion,
            contraste=contraste,
            saturacion=saturacion,
            temperatura=temperatura,
            log_fn=logs,
        )
        if acumulado is None:
            acumulado = segmento_video
        else:
            unido = os.path.join(visual_dir, f"{base_name}_acumulado_{idx+1:03d}.mp4")
            _concat_visualizadores([acumulado, segmento_video], unido, logs=logs)
            try:
                os.remove(acumulado)
            except Exception:
                pass
            try:
                os.remove(segmento_video)
            except Exception:
                pass
            acumulado = unido
        try:
            os.remove(segmento_audio)
        except Exception:
            pass
        if progress_callback:
            progress_callback(idx + 1, total_segments)
        start += parte_duracion
    if not acumulado:
        raise RuntimeError("No se generó ningún segmento del visualizador.")
    if acumulado != salida_visual:
        os.replace(acumulado, salida_visual)
    return salida_visual


def generar_visualizador_solo(
    video_path: str,
    inicio_sec: float = 0.0,
    duracion_sec: float | None = None,
    estilo: str = "showwaves",
    color: str = "#FFFFFF",
    margen_horizontal: int = 0,
    exposicion: float = 0.0,
    contraste: float = 1.0,
    saturacion: float = 1.0,
    temperatura: float = 0.0,
    fps: int = 30,
    logs=None,
    segmento_segundos: float = 60.0,
    progress_callback=None,
):
    """
    Genera únicamente el video del visualizador a partir del audio del video original.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"No se encontró el video: {video_path}")
    base_dir = output_base_dir(video_path)
    base_name = nombre_base_principal(video_path)
    visual_dir = os.path.join(base_dir, "visualizador")
    asegurar_dir(visual_dir)
    audios_dir = os.path.join(base_dir, "audios")
    os.makedirs(audios_dir, exist_ok=True)
    audio_dest = os.path.join(audios_dir, f"{base_name}_original.mp3")
    if os.path.exists(audio_dest) and os.path.getsize(audio_dest) > 0:
        audio_source = audio_dest
        if logs: logs(f"Usando audio existente: {audio_dest}")
    else:
        if logs: logs("Extrayendo audio para visualizador...")
        audio_source = extraer_audio(video_path, audio_dest, logs if logs else None)
        if logs: logs(f"Audio generado: {audio_source}")
    total_duration = obtener_duracion_segundos(audio_source)
    start = max(0.0, float(inicio_sec or 0.0))
    if start >= total_duration:
        raise ValueError("El inicio supera la duración del audio disponible.")
    if duracion_sec and duracion_sec > 0:
        duration = min(duracion_sec, max(0.0, total_duration - start))
        if duration <= 0:
            raise ValueError("La duración solicitada no es válida.")
    else:
        duration = total_duration - start
    trimmed_audio = audio_source
    if start > 0 or (duracion_sec and duracion_sec > 0):
        trimmed_audio = os.path.join(
            visual_dir,
            f"{base_name}_audio_{int(start*1000)}_{int(duration*1000)}.mp3",
        )
        if not os.path.exists(trimmed_audio) or os.path.getsize(trimmed_audio) == 0:
            cmd = ["ffmpeg", "-y"]
            if start > 0:
                cmd += ["-ss", f"{start:.3f}"]
            cmd += ["-i", audio_source]
            if duration and duration > 0:
                cmd += ["-t", f"{duration:.3f}"]
            cmd += ["-acodec", "libmp3lame", "-b:a", "192k", trimmed_audio]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                err = (result.stderr or "").strip()
                if logs: logs(f"❌ Recorte de audio falló: {err[-300:]}")
                raise RuntimeError("No se pudo preparar el audio del visualizador.")
    if logs: logs("Generando visualizador por segmentos...")
    video_width, video_height = obtener_tamano_video(video_path)
    visual_width = max(64, video_width)
    visual_height = max(64, min(360, max(160, video_height // 4)))
    salida_visual = os.path.join(visual_dir, f"{base_name}_visualizador.mp4")
    _generar_visualizador_segmentado(
        trimmed_audio,
        visual_dir,
        base_name,
        salida_visual,
        visual_width,
        visual_height,
        estilo,
        color,
        fps,
        margen_horizontal,
        exposicion,
        contraste,
        saturacion,
        temperatura,
        segmento_segundos,
        logs=logs,
        progress_callback=progress_callback,
    )
    if logs: logs(f"Visualizador listo: {salida_visual}")
    return salida_visual


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




