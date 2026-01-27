import os
from core.extractor import extraer_audio
from core.utils import (
    dividir_audio_ffmpeg,
    dividir_video_ffmpeg,
    dividir_video_vertical_individual,
    quemar_srt_en_video,
    nombre_base_fuente,
    guardar_resumen_rango,
    generar_vertical_tiktok,
    aplicar_fondo_imagen,
)
from core.transcriber import transcribir_srt
import re


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
        base_name = nombre_base_fuente(video_path)
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
                audio_dir_base = f"output/audios/{base_name}"
                os.makedirs(audio_dir_base, exist_ok=True)
                audio_path = os.path.join(audio_dir_base, f"{base_name}_original.mp3")
                audio_path = extraer_audio(video_path, audio_path)
                if logs: logs(f"✅ Audio original guardado: {audio_path}")
        else:
            if logs: logs(f"Video seleccionado: {video_path}")

        # 2. Dividir video (opcional, solo local)
        if not es_audio and dividir_video:
            if logs: logs("Dividiendo video en partes...")
            video_dir = f"output/videos/{base_name}"
            partes_video = dividir_video_ffmpeg(
                video_path,
                segundos_por_parte=segundos_por_parte,
                out_dir=video_dir,
                start_sec=start_sec,
                end_sec=end_sec,
                log_fn=logs if logs else None,
            )
            if logs: logs(f"Video dividido en {len(partes_video)} fragmentos")
            if fondo_path and os.path.exists(fondo_path):
                fondo_dir = os.path.join(video_dir, "background")
                os.makedirs(fondo_dir, exist_ok=True)
                for parte in partes_video:
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
                vertical_dir = os.path.join(video_dir, "vertical")
                os.makedirs(vertical_dir, exist_ok=True)
                for idx, parte in enumerate(partes_video):
                    nombre = os.path.splitext(os.path.basename(parte))[0]
                    out_path = os.path.join(vertical_dir, f"{nombre}_vertical.mp4")
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
                if fondo_path and os.path.exists(fondo_path):
                    vertical_bg_dir = os.path.join(video_dir, "vertical", "background")
                    os.makedirs(vertical_bg_dir, exist_ok=True)
                    for parte in partes_video:
                        nombre = os.path.splitext(os.path.basename(parte))[0]
                        in_path = os.path.join(vertical_dir, f"{nombre}_vertical.mp4")
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

        partes_audio = []
        if not solo_video:
            # 3. Dividir audio en MP3
            if logs: logs("Dividiendo audio en partes...")
            audio_dir = f"output/audios/{base_name}"
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
                subs_dir = f"output/subtitulos/{base_name}"
                for idx, parte in enumerate(partes_audio, start=1):
                    if logs: logs(f"📝 Generando SRT {idx}/{len(partes_audio)}...")
                    srt_path = transcribir_srt(parte, subs_dir, idioma="es", model_size="base")
                    if logs: logs(f"✅ SRT listo: {srt_path}")

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
    barra=None,
    logs=None,
):
    """
    Corta un video en partes y genera versiones verticales 9:16.
    posicion: C (centro), L (izquierda), R (derecha)
    """
    try:
        if logs: logs("Iniciando corte individual...")
        base_name = nombre_base_fuente(video_path)
        segundos_por_parte = max(1.0, float(minutos_por_parte) * 60)
        start_sec = float(inicio_min) * 60 if inicio_min is not None else 0.0
        end_sec = float(fin_min) * 60 if fin_min is not None else None
        if end_sec is not None and end_sec <= start_sec:
            if logs: logs("Rango invalido: el minuto final debe ser mayor al inicial.")
            return

        out_dir = os.path.join("output", "videos", base_name, "individual")
        partes = dividir_video_vertical_individual(
            video_path,
            segundos_por_parte=segundos_por_parte,
            out_dir=out_dir,
            posicion=posicion,
            zoom=zoom,
            bg_color=bg_color,
            start_sec=start_sec,
            end_sec=end_sec,
            log_fn=logs if logs else None,
        )
        if logs: logs(f"Corte individual generado: {len(partes)} partes")
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
        base_name = nombre_base_fuente(path)
        if es_audio:
            audio_path = path
            if logs: logs(f"Audio seleccionado: {path}")
        else:
            if logs: logs(f"Video seleccionado: {path}")
            audio_dir_base = os.path.join("output", "audios", base_name)
            os.makedirs(audio_dir_base, exist_ok=True)
            audio_path = os.path.join(audio_dir_base, f"{base_name}_srt_source.mp3")
            if logs: logs("Extrayendo audio para SRT...")
            extraer_audio(path, audio_path)
        subs_dir = os.path.join("output", "subtitulos", base_name)
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
    logs=None,
):
    """
    Quema un .srt en un video y guarda en output/videos/<base>/subtitulados.
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
        base_name = nombre_base_fuente(video_path)
        out_dir = os.path.join("output", "videos", base_name, "subtitulados")
        out_path = os.path.join(out_dir, f"{base_name}_subt.mp4")
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
            log_fn=logs
        )
        if logs: logs(f"Video subtitulado listo: {out_path}")
    except Exception as e:
        if logs: logs(f"Error: {e}")
        raise e




