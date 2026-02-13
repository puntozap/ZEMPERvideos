import os
import threading
import customtkinter as ctk
import tkinter as tk

from core.ai_youtube import subir_video_youtube_desde_ia
from core.corte_config import get_corte_defaults, get_cintas_defaults, get_mensajes_defaults
from core.utils import obtener_duracion_segundos, output_base_dir
from core.workflow import procesar_srt, procesar_quemar_srt
from ui.shared.preview import SimpleVideoPlayer
from ui.shared import helpers


def create_tab(parent, context):
    estado = context["estado"]
    rango = context["rango"]
    log = context["log"]
    titulo_seccion = context.get("titulo_seccion", "Corte")
    modo_sin_bordes = bool(context.get("modo_sin_bordes", False))
    limpiar_entry = context["limpiar_entry"]
    alerta_busy = context["alerta_busy"]
    abrir_videos = context["abrir_videos"]
    stop_control = context["stop_control"]
    procesar_video_fn = context["procesar_video_fn"]
    beep_fin = context["beep_fin"]

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)
    container.grid_rowconfigure(0, weight=1)

    left = ctk.CTkFrame(container, fg_color="transparent")
    left.grid(row=0, column=0, sticky="nsew")
    left.grid_columnconfigure(0, weight=1)
    left.grid_rowconfigure(0, weight=1)

    def leer_minutos():
        try:
            valor = float(entry_minutos.get().strip().replace(",", "."))
            return valor if valor > 0 else 5
        except Exception:
            return 5

    def leer_rango_minutos():
        if rango["duracion"] <= 0:
            return None, None
        return rango["inicio"] / 60.0, rango["fin"] / 60.0

    def normalizar_posicion_visualizador(valor: str) -> str:
        texto = (valor or "centro").strip().lower()
        if texto not in ("arriba", "abajo", "centro"):
            return "centro"
        return texto

    def capitalizar_posicion(valor: str) -> str:
        mapeo = {"centro": "Centro", "arriba": "Arriba", "abajo": "Abajo"}
        return mapeo.get(normalizar_posicion_visualizador(valor), "Centro")

    def obtener_posicion_visualizador():
        return normalizar_posicion_visualizador(posicion_visualizador_var.get())

    defaults = get_corte_defaults()
    cintas_defaults = get_cintas_defaults()
    mensajes_defaults = get_mensajes_defaults()

    def iniciar_proceso():
        if not estado["path"]:
            log("Selecciona un video primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion(titulo_seccion)
        minutos = leer_minutos()
        inicio_min, fin_min = leer_rango_minutos()
        vertical = vertical_var.get()
        orden = orden_var.get()
        try:
            recorte_total = float(entry_recorte_total.get().strip().replace(",", "."))
        except Exception:
            recorte_total = 0.12
        recorte_top = recorte_total
        recorte_bottom = recorte_total
        recorte_bordes = recorte_bordes_var.get()
        if modo_sin_bordes:
            vertical = False
            recorte_bordes = True
        try:
            recorte_manual_top = float(entry_recorte_top.get().strip().replace(",", "."))
        except Exception:
            recorte_manual_top = float(defaults.get("recorte_manual_top", 0.0))
        try:
            recorte_manual_bottom = float(entry_recorte_bottom.get().strip().replace(",", "."))
        except Exception:
            recorte_manual_bottom = float(defaults.get("recorte_manual_bottom", 0.0))
        fondo_path = estado["fondo_path"] if fondo_var.get() else None
        fondo_estilo = fondo_estilo_var.get().lower()
        try:
            fondo_escala = float(entry_fondo_escala.get().strip().replace(",", "."))
        except Exception:
            fondo_escala = 0.92
        fondo_usar_tamano_imagen = bool(modo_sin_bordes)
        if modo_sin_bordes:
            try:
                inset_left = float(entry_left.get().strip().replace(",", ".")) / 100.0
                inset_right = float(entry_right.get().strip().replace(",", ".")) / 100.0
                inset_top = float(entry_top.get().strip().replace(",", ".")) / 100.0
                inset_bottom = float(entry_bottom.get().strip().replace(",", ".")) / 100.0
                fondo_inset_pct = (inset_left, inset_right, inset_top, inset_bottom)
                fondo_zoom = float(entry_zoom.get().strip().replace(",", "."))
            except Exception:
                fondo_inset_pct = (
                    float(defaults.get("inset_left_pct", 4.0)) / 100.0,
                    float(defaults.get("inset_right_pct", 4.0)) / 100.0,
                    float(defaults.get("inset_top_pct", 8.0)) / 100.0,
                    float(defaults.get("inset_bottom_pct", 8.0)) / 100.0,
                )
                fondo_zoom = float(defaults.get("zoom", 1.0))
        else:
            fondo_inset_pct = None
            fondo_zoom = 1.0
        if modo_sin_bordes and cintas_enabled_var.get():
            fondo_cintas = [
                {
                    "left_pct": float(entry_cinta_left_1.get().strip().replace(",", ".")),
                    "top_pct": float(entry_cinta_top_1.get().strip().replace(",", ".")),
                    "width_pct": float(entry_cinta_width_1.get().strip().replace(",", ".")),
                    "height_pct": float(entry_cinta_height_1.get().strip().replace(",", ".")),
                    "bg_color": entry_cinta_bg_1.get().strip(),
                    "border_color": entry_cinta_border_1.get().strip(),
                    "text_color": entry_cinta_text_1.get().strip(),
                    "fontfile_name": _cinta_text(0, "fontfile_name", ""),
                    "fontfile_role": _cinta_text(0, "fontfile_role", ""),
                    "nombre": entry_cinta_nombre_1.get().strip(),
                    "rol": entry_cinta_rol_1.get().strip(),
                },
                {
                    "left_pct": float(entry_cinta_left_2.get().strip().replace(",", ".")),
                    "top_pct": float(entry_cinta_top_2.get().strip().replace(",", ".")),
                    "width_pct": float(entry_cinta_width_2.get().strip().replace(",", ".")),
                    "height_pct": float(entry_cinta_height_2.get().strip().replace(",", ".")),
                    "bg_color": entry_cinta_bg_2.get().strip(),
                    "border_color": entry_cinta_border_2.get().strip(),
                    "text_color": entry_cinta_text_2.get().strip(),
                    "fontfile_name": _cinta_text(1, "fontfile_name", ""),
                    "fontfile_role": _cinta_text(1, "fontfile_role", ""),
                    "nombre": entry_cinta_nombre_2.get().strip(),
                    "rol": entry_cinta_rol_2.get().strip(),
                },
            ]
        else:
            fondo_cintas = None
        if modo_sin_bordes and mensajes_enabled_var.get():
            fondo_mensajes = [
                {
                    "left_pct": float(entry_msg_left.get().strip().replace(",", ".")),
                    "top_pct": float(entry_msg_top.get().strip().replace(",", ".")),
                    "width_pct": float(entry_msg_width.get().strip().replace(",", ".")),
                    "height_pct": float(entry_msg_height.get().strip().replace(",", ".")),
                    "bg_color": entry_msg_bg.get().strip(),
                    "text_color": entry_msg_text.get().strip(),
                    "border_color": entry_msg_border.get().strip(),
                    "text": entry_msg_textval.get().strip(),
                    "fontfile": msg_fontfile,
                }
            ]
        else:
            fondo_mensajes = None
        if modo_sin_bordes:
            try:
                fondo_bg_crop_top = float(entry_bg_crop_top.get().strip().replace(",", ".")) / 100.0
                fondo_bg_crop_bottom = float(entry_bg_crop_bottom.get().strip().replace(",", ".")) / 100.0
            except Exception:
                fondo_bg_crop_top = float(defaults.get("bg_crop_top_pct", 0.0)) / 100.0
                fondo_bg_crop_bottom = float(defaults.get("bg_crop_bottom_pct", 20.0)) / 100.0
        else:
            fondo_bg_crop_top = 0.0
            fondo_bg_crop_bottom = 0.0
        musica_habilitada = bool(estado.get("musica_fondo_habilitada", False))
        musica_path = estado.get("musica_fondo_path") if musica_habilitada else None
        try:
            musica_vol = float(estado.get("musica_fondo_volumen", 0.25))
        except Exception:
            musica_vol = 0.25
        try:
            musica_inicio = float(estado.get("musica_fondo_inicio", 0.0))
        except Exception:
            musica_inicio = 0.0
        musica_fin = estado.get("musica_fondo_fin", None)
        try:
            if musica_fin is not None:
                musica_fin = float(musica_fin)
        except Exception:
            musica_fin = None
        try:
            musica_inicio_video = float(estado.get("musica_fondo_inicio_video", 0.0))
        except Exception:
            musica_inicio_video = 0.0

        def run_corte():
            try:
                estado["visualizador"] = visualizador_var.get()
                estado["posicion_visualizador"] = obtener_posicion_visualizador()
                estado["visualizador_opacidad"] = visualizador_opacity_var.get()
                estado["visualizador_color"] = visualizador_color_var.get()
                estado["visualizador_margen"] = int(float(visualizador_margin_var.get()))
                solo_video_flag = not visualizador_var.get()
                result = procesar_video_fn(
                    estado["path"],
                    False,
                    False,
                    minutos,
                    inicio_min,
                    fin_min,
                    True,
                    vertical,
                    orden,
                    recorte_top,
                    recorte_bottom,
                    recorte_bordes,
                    recorte_manual_top,
                    recorte_manual_bottom,
                    False,
                    fondo_path,
                    fondo_estilo,
                    fondo_escala,
                    fondo_usar_tamano_imagen,
                    fondo_inset_pct,
                    fondo_zoom,
                    fondo_cintas,
                    fondo_mensajes,
                    fondo_bg_crop_top,
                    fondo_bg_crop_bottom,
                    solo_video=solo_video_flag,
                    visualizador=visualizador_var.get(),
                    posicion_visualizador=obtener_posicion_visualizador(),
                    visualizador_opacidad=visualizador_opacity_var.get(),
                    visualizador_color=visualizador_color_var.get(),
                    visualizador_margen=int(float(visualizador_margin_var.get())),
                    visualizador_exposicion=estado.get("visualizador_exposicion", 0.0),
                    visualizador_contraste=estado.get("visualizador_contraste", 1.0),
                    visualizador_saturacion=estado.get("visualizador_saturacion", 1.0),
                    visualizador_temperatura=estado.get("visualizador_temperatura", 0.0),
                    modo_visualizador=estado.get("visualizador_blend_mode", "lighten"),
                    musica_path=musica_path,
                    musica_volumen=musica_vol,
                    musica_inicio=musica_inicio,
                    musica_fin=musica_fin,
                    musica_inicio_video=musica_inicio_video,
                )
                if procesar_todo_var.get():
                    videos = []
                    if isinstance(result, dict):
                        videos = result.get("videos") or []
                    elif isinstance(result, list):
                        videos = result
                    if not videos:
                        log("No se generaron videos para subtitular.")
                    else:
                        idioma = idioma_var.get()
                        if idioma == "auto":
                            idioma = ""
                        modelo = modelo_var.get()
                        for idx, video in enumerate(videos, start=1):
                            if stop_control.should_stop():
                                log("Proceso detenido por el usuario.")
                                return
                            log(f"Generando SRT ({idx}/{len(videos)})...")
                            srt_path = procesar_srt(
                                video,
                                False,
                                idioma,
                                modelo,
                                None,
                                None,
                                log,
                            )
                            if not srt_path:
                                log("No se pudo generar SRT para este video.")
                                continue
                            procesar_quemar_srt(video, srt_path, logs=log)
                log("Finalizado proceso de corte.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error en corte: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_corte, daemon=True).start()

    def agregar_todo_youtube():
        if not estado["path"]:
            log("Selecciona un video primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        helpers.log_seccion(log, None, "Agregar todo YouTube")
        minutos = leer_minutos()
        inicio_min, fin_min = leer_rango_minutos()
        recorte_total = 0.12
        try:
            recorte_total = float(entry_recorte_total.get().strip().replace(",", "."))
        except Exception:
            recorte_total = 0.12
        recorte_top = recorte_total
        recorte_bottom = recorte_total
        recorte_bordes = recorte_bordes_var.get()
        if modo_sin_bordes:
            recorte_bordes = True
        try:
            recorte_manual_top = float(entry_recorte_top.get().strip().replace(",", "."))
        except Exception:
            recorte_manual_top = float(defaults.get("recorte_manual_top", 0.0))
        try:
            recorte_manual_bottom = float(entry_recorte_bottom.get().strip().replace(",", "."))
        except Exception:
            recorte_manual_bottom = float(defaults.get("recorte_manual_bottom", 0.0))
        fondo_path = estado["fondo_path"] if fondo_var.get() else None
        fondo_estilo = fondo_estilo_var.get().lower()
        try:
            fondo_escala = float(entry_fondo_escala.get().strip().replace(",", "."))
        except Exception:
            fondo_escala = 0.92
        fondo_usar_tamano_imagen = bool(modo_sin_bordes)
        if modo_sin_bordes:
            try:
                inset_left = float(entry_left.get().strip().replace(",", ".")) / 100.0
                inset_right = float(entry_right.get().strip().replace(",", ".")) / 100.0
                inset_top = float(entry_top.get().strip().replace(",", ".")) / 100.0
                inset_bottom = float(entry_bottom.get().strip().replace(",", ".")) / 100.0
                fondo_inset_pct = (inset_left, inset_right, inset_top, inset_bottom)
                fondo_zoom = float(entry_zoom.get().strip().replace(",", "."))
            except Exception:
                fondo_inset_pct = (
                    float(defaults.get("inset_left_pct", 4.0)) / 100.0,
                    float(defaults.get("inset_right_pct", 4.0)) / 100.0,
                    float(defaults.get("inset_top_pct", 8.0)) / 100.0,
                    float(defaults.get("inset_bottom_pct", 8.0)) / 100.0,
                )
                fondo_zoom = float(defaults.get("zoom", 1.0))
        else:
            fondo_inset_pct = None
            fondo_zoom = 1.0
        if modo_sin_bordes and cintas_enabled_var.get():
            fondo_cintas = [
                {
                    "left_pct": float(entry_cinta_left_1.get().strip().replace(",", ".")),
                    "top_pct": float(entry_cinta_top_1.get().strip().replace(",", ".")),
                    "width_pct": float(entry_cinta_width_1.get().strip().replace(",", ".")),
                    "height_pct": float(entry_cinta_height_1.get().strip().replace(",", ".")),
                    "bg_color": entry_cinta_bg_1.get().strip(),
                    "border_color": entry_cinta_border_1.get().strip(),
                    "text_color": entry_cinta_text_1.get().strip(),
                    "fontfile_name": _cinta_text(0, "fontfile_name", ""),
                    "fontfile_role": _cinta_text(0, "fontfile_role", ""),
                    "nombre": entry_cinta_nombre_1.get().strip(),
                    "rol": entry_cinta_rol_1.get().strip(),
                },
                {
                    "left_pct": float(entry_cinta_left_2.get().strip().replace(",", ".")),
                    "top_pct": float(entry_cinta_top_2.get().strip().replace(",", ".")),
                    "width_pct": float(entry_cinta_width_2.get().strip().replace(",", ".")),
                    "height_pct": float(entry_cinta_height_2.get().strip().replace(",", ".")),
                    "bg_color": entry_cinta_bg_2.get().strip(),
                    "border_color": entry_cinta_border_2.get().strip(),
                    "text_color": entry_cinta_text_2.get().strip(),
                    "fontfile_name": _cinta_text(1, "fontfile_name", ""),
                    "fontfile_role": _cinta_text(1, "fontfile_role", ""),
                    "nombre": entry_cinta_nombre_2.get().strip(),
                    "rol": entry_cinta_rol_2.get().strip(),
                },
            ]
        else:
            fondo_cintas = None
        if modo_sin_bordes and mensajes_enabled_var.get():
            fondo_mensajes = [
                {
                    "left_pct": float(entry_msg_left.get().strip().replace(",", ".")),
                    "top_pct": float(entry_msg_top.get().strip().replace(",", ".")),
                    "width_pct": float(entry_msg_width.get().strip().replace(",", ".")),
                    "height_pct": float(entry_msg_height.get().strip().replace(",", ".")),
                    "bg_color": entry_msg_bg.get().strip(),
                    "text_color": entry_msg_text.get().strip(),
                    "border_color": entry_msg_border.get().strip(),
                    "text": entry_msg_textval.get().strip(),
                    "fontfile": msg_fontfile,
                }
            ]
        else:
            fondo_mensajes = None
        if modo_sin_bordes:
            try:
                fondo_bg_crop_top = float(entry_bg_crop_top.get().strip().replace(",", ".")) / 100.0
                fondo_bg_crop_bottom = float(entry_bg_crop_bottom.get().strip().replace(",", ".")) / 100.0
            except Exception:
                fondo_bg_crop_top = float(defaults.get("bg_crop_top_pct", 0.0)) / 100.0
                fondo_bg_crop_bottom = float(defaults.get("bg_crop_bottom_pct", 20.0)) / 100.0
        else:
            fondo_bg_crop_top = 0.0
            fondo_bg_crop_bottom = 0.0
        musica_habilitada = bool(estado.get("musica_fondo_habilitada", False))
        musica_path = estado.get("musica_fondo_path") if musica_habilitada else None
        try:
            musica_vol = float(estado.get("musica_fondo_volumen", 0.25))
        except Exception:
            musica_vol = 0.25
        try:
            musica_inicio = float(estado.get("musica_fondo_inicio", 0.0))
        except Exception:
            musica_inicio = 0.0
        musica_fin = estado.get("musica_fondo_fin", None)
        try:
            if musica_fin is not None:
                musica_fin = float(musica_fin)
        except Exception:
            musica_fin = None
        try:
            musica_inicio_video = float(estado.get("musica_fondo_inicio_video", 0.0))
        except Exception:
            musica_inicio_video = 0.0
        vertical = vertical_var.get()
        if modo_sin_bordes:
            vertical = False

        def run_auto():
            try:
                estado["visualizador"] = visualizador_var.get()
                estado["posicion_visualizador"] = obtener_posicion_visualizador()
                solo_video_flag = auto_subs_var.get()
                if visualizador_var.get():
                    solo_video_flag = False
                estado["visualizador_opacidad"] = visualizador_opacity_var.get()
                estado["visualizador_color"] = visualizador_color_var.get()
                estado["visualizador_margen"] = int(float(visualizador_margin_var.get()))
                result = procesar_video_fn(
                    estado["path"],
                    False,
                    False,
                    minutos,
                    inicio_min,
                    fin_min,
                    True,
                    vertical,
                    orden_var.get(),
                    recorte_top,
                    recorte_bottom,
                    recorte_bordes,
                    recorte_manual_top,
                    recorte_manual_bottom,
                    False,
                    fondo_path,
                    fondo_estilo,
                    fondo_escala,
                    fondo_usar_tamano_imagen,
                    fondo_inset_pct,
                    fondo_zoom,
                    fondo_cintas,
                    fondo_mensajes,
                    fondo_bg_crop_top,
                    fondo_bg_crop_bottom,
                    solo_video=solo_video_flag,
                    visualizador=visualizador_var.get(),
                    posicion_visualizador=obtener_posicion_visualizador(),
                    visualizador_opacidad=visualizador_opacity_var.get(),
                    visualizador_color=visualizador_color_var.get(),
                    visualizador_margen=int(float(visualizador_margin_var.get())),
                    visualizador_exposicion=estado.get("visualizador_exposicion", 0.0),
                    visualizador_contraste=estado.get("visualizador_contraste", 1.0),
                    visualizador_saturacion=estado.get("visualizador_saturacion", 1.0),
                    visualizador_temperatura=estado.get("visualizador_temperatura", 0.0),
                    modo_visualizador=estado.get("visualizador_blend_mode", "lighten"),
                    musica_path=musica_path,
                    musica_volumen=musica_vol,
                    musica_inicio=musica_inicio,
                    musica_fin=musica_fin,
                    musica_inicio_video=musica_inicio_video,
                )
                videos = []
                if isinstance(result, dict):
                    videos = result.get("videos") or []
                elif isinstance(result, list):
                    videos = result
                if not videos:
                    log("No se generaron videos para subir.")
                    return
                for idx, video_path in enumerate(videos, start=1):
                    if stop_control.should_stop():
                        log("Proceso detenido por el usuario.")
                        return
                    helpers.log_seccion(log, None, "YouTube automático")
                    log(f"Subiendo {idx}/{len(videos)}: {video_path}")
                    subir_video_youtube_desde_ia(
                        video_path,
                        None,
                        model="gpt-4o-mini",
                        idioma="es",
                        privacy="private",
                        log_fn=log,
                    )
                    log(f"Video {idx}/{len(videos)} subido en privado.")
                log("Todos los videos se subieron como ocultos.")
            except Exception as exc:
                helpers.log_seccion(log, None, "Error YouTube")
                log(f"Error automático YouTube: {exc}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_auto, daemon=True).start()

    slider_programmatic = False
    ENTRY_ERROR_BORDER = "#ff6b6b"
    ENTRY_DEFAULT_BORDER = None

    def format_time(seconds):
        seconds = max(0, float(seconds))
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def format_entry_time(seconds):
        seconds = max(0, float(seconds))
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def parse_entry_time(value: str):
        text = (value or "").strip()
        if not text:
            raise ValueError("Formato mm:ss")
        if ":" not in text:
            raise ValueError("Formato mm:ss")
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError("Formato mm:ss")
        min_part, sec_part = parts
        try:
            minutes = int(min_part.strip())
        except Exception:
            raise ValueError("Minutos inválidos")
        try:
            seconds = float(sec_part.strip().replace(",", "."))
        except Exception:
            raise ValueError("Segundos inválidos")
        if minutes < 0:
            raise ValueError("Minutos inválidos")
        if seconds < 0 or seconds >= 60:
            raise ValueError("Segundos 00-59")
        return minutes * 60 + seconds


    def actualizar_etiquetas_rango():
        lbl_inicio_val.configure(text=format_time(rango["inicio"]))
        lbl_fin_val.configure(text=format_time(rango["fin"]))
        lbl_duracion_val.configure(text=format_time(rango["duracion"]))

    def set_preview_enabled(enabled: bool):
        estado["es_audio"] = False
        state = "normal" if enabled else "disabled"
        slider_inicio.configure(state=state)
        slider_fin.configure(state=state)
        entry_inicio.configure(state=state)
        entry_fin.configure(state=state)
        clear_feedback()
        if not enabled:
            rango["duracion"] = 0.0
            set_range_seconds(0, 0)
            clear_feedback()
            try:
                video_player.stop()
            except Exception:
                pass

    def cargar_video_preview(path):
        log("Cargando vista previa...")
        video_player.load(path)
        try:
            duracion = obtener_duracion_segundos(path)
        except Exception:
            duracion = 0.0
        rango["duracion"] = max(0.0, duracion)
        slider_inicio.configure(from_=0, to=rango["duracion"])
        slider_fin.configure(from_=0, to=rango["duracion"])
        set_range_seconds(0, rango["duracion"])

    corte_scroll = ctk.CTkScrollableFrame(left, corner_radius=0)
    corte_scroll.grid(row=0, column=0, sticky="nsew")
    corte_scroll.grid_columnconfigure(0, weight=1)

    # --- Corte: configuracion + acciones ---
    top = ctk.CTkFrame(corte_scroll, corner_radius=12)
    top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 12))
    top.grid_columnconfigure(0, weight=1)
    top.grid_columnconfigure(1, weight=1)

    config = ctk.CTkFrame(top, corner_radius=10)
    config.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    config.grid_columnconfigure(0, weight=1)

    lbl_conf = ctk.CTkLabel(config, text="Configuracion", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_conf.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    row_min = ctk.CTkFrame(config, fg_color="transparent")
    row_min.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
    row_min.grid_columnconfigure(1, weight=1)

    lbl_minutos = ctk.CTkLabel(row_min, text="Minutos por parte", font=ctk.CTkFont(size=13))
    lbl_minutos.grid(row=0, column=0, sticky="w")

    entry_minutos = ctk.CTkEntry(row_min, width=120)
    entry_minutos.insert(0, "5")
    entry_minutos.grid(row=0, column=1, sticky="e")

    btn_clear_min = ctk.CTkButton(
        row_min,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_minutos),
    )
    btn_clear_min.grid(row=0, column=2, sticky="e", padx=(8, 0))

    hint = ctk.CTkLabel(config, text="Puedes usar decimales. Ej: 2.5", font=ctk.CTkFont(size=12), text_color="#9aa4b2")
    hint.grid(row=2, column=0, sticky="w", padx=14, pady=(0, 12))

    vertical_var = ctk.BooleanVar(value=False)
    chk_vertical = ctk.CTkCheckBox(
        config,
        text="Generar formato TikTok (9:16, izquierda arriba / derecha abajo)",
        variable=vertical_var,
    )
    chk_vertical.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

    orden_var = ctk.StringVar(value="LR")
    lbl_orden = ctk.CTkLabel(config, text="Orden vertical:", font=ctk.CTkFont(size=13))
    lbl_orden.grid(row=4, column=0, sticky="w", padx=14, pady=(0, 6))

    rb_lr = ctk.CTkRadioButton(
        config,
        text="Izquierda arriba / Derecha abajo",
        variable=orden_var,
        value="LR",
    )
    rb_lr.grid(row=5, column=0, sticky="w", padx=14, pady=(0, 4))

    rb_rl = ctk.CTkRadioButton(
        config,
        text="Derecha arriba / Izquierda abajo",
        variable=orden_var,
        value="RL",
    )
    rb_rl.grid(row=6, column=0, sticky="w", padx=14, pady=(0, 12))

    rb_alt = ctk.CTkRadioButton(
        config,
        text="Intercalado (alterna por cada parte)",
        variable=orden_var,
        value="ALT",
    )
    rb_alt.grid(row=7, column=0, sticky="w", padx=14, pady=(0, 12))
    if modo_sin_bordes:
        chk_vertical.grid_remove()
        lbl_orden.grid_remove()
        rb_lr.grid_remove()
        rb_rl.grid_remove()
        rb_alt.grid_remove()

    visualizador_var = tk.BooleanVar(value=estado.get("visualizador", False))
    chk_visualizador = ctk.CTkCheckBox(
        config,
        text="Agregar visualizador de música",
        variable=visualizador_var,
    )
    chk_visualizador.grid(row=8, column=0, sticky="w", padx=14, pady=(0, 12))

    posicion_visualizador_var = tk.StringVar(
        value=capitalizar_posicion(estado.get("posicion_visualizador", "centro"))
    )
    lbl_pos_visual = ctk.CTkLabel(
        config,
        text="Posición del visualizador:",
        font=ctk.CTkFont(size=12),
    )
    lbl_pos_visual.grid(row=9, column=0, sticky="w", padx=14, pady=(0, 4))
    opt_pos_visual = ctk.CTkOptionMenu(
        config,
        values=["Centro", "Arriba", "Abajo"],
        variable=posicion_visualizador_var,
        width=140,
    )
    opt_pos_visual.grid(row=10, column=0, sticky="w", padx=14, pady=(0, 12))

    visualizador_opacity_var = tk.DoubleVar(value=estado.get("visualizador_opacidad", 0.65))
    lbl_opacity = ctk.CTkLabel(config, text="Opacidad del visualizador:", font=ctk.CTkFont(size=12))
    lbl_opacity.grid(row=11, column=0, sticky="w", padx=14, pady=(0, 4))
    lbl_opacity_value = ctk.CTkLabel(config, text="", font=ctk.CTkFont(size=12))
    lbl_opacity_value.grid(row=11, column=0, sticky="e", padx=14, pady=(0, 4))

    def actualizar_label_opacidad(value=None):
        val = float(value if value is not None else visualizador_opacity_var.get())
        lbl_opacity_value.configure(text=f"{int(val * 100)}%")

    slider_opacity = ctk.CTkSlider(
        config,
        from_=0.2,
        to=1.0,
        number_of_steps=16,
        variable=visualizador_opacity_var,
        command=lambda value: actualizar_label_opacidad(value),
        width=220,
    )
    slider_opacity.grid(row=12, column=0, sticky="w", padx=14, pady=(0, 12))
    actualizar_label_opacidad()

    visualizador_color_var = tk.StringVar(value=estado.get("visualizador_color", "#FFFFFF"))
    lbl_color = ctk.CTkLabel(config, text="Color del visualizador:", font=ctk.CTkFont(size=12))
    lbl_color.grid(row=13, column=0, sticky="w", padx=14, pady=(0, 4))
    entry_color = ctk.CTkEntry(
        config,
        width=120,
        textvariable=visualizador_color_var,
        placeholder_text="#RRGGBB",
    )
    entry_color.grid(row=14, column=0, sticky="w", padx=14, pady=(0, 12))

    visualizador_margin_var = tk.DoubleVar(value=estado.get("visualizador_margen", 0))
    lbl_margin = ctk.CTkLabel(config, text="Margen lateral (px cada lado):", font=ctk.CTkFont(size=12))
    lbl_margin.grid(row=15, column=0, sticky="w", padx=14, pady=(0, 4))
    lbl_margin_value = ctk.CTkLabel(config, text="", font=ctk.CTkFont(size=12))
    lbl_margin_value.grid(row=15, column=0, sticky="e", padx=14, pady=(0, 4))

    def actualizar_label_margen(value=None):
        val = int(float(value if value is not None else visualizador_margin_var.get()))
        lbl_margin_value.configure(text=f"{val}px")

    slider_margin = ctk.CTkSlider(
        config,
        from_=0,
        to=220,
        number_of_steps=22,
        variable=visualizador_margin_var,
        command=lambda value: actualizar_label_margen(value),
        width=220,
    )
    slider_margin.grid(row=16, column=0, sticky="w", padx=14, pady=(0, 12))
    actualizar_label_margen()

    fondo_var = ctk.BooleanVar(value=False)
    chk_fondo = ctk.CTkCheckBox(
        config,
        text="Aplicar imagen de fondo",
        variable=fondo_var,
    )
    chk_fondo.grid(row=17, column=0, sticky="w", padx=14, pady=(0, 8))

    row_fondo = ctk.CTkFrame(config, fg_color="transparent")
    row_fondo.grid(row=18, column=0, sticky="ew", padx=14, pady=(0, 10))
    row_fondo.grid_columnconfigure(1, weight=1)

    def seleccionar_fondo():
        from ui.dialogs import seleccionar_imagen
        img = seleccionar_imagen()
        if img:
            estado["fondo_path"] = img
            lbl_fondo.configure(text=os.path.basename(img))

    btn_fondo = ctk.CTkButton(
        row_fondo,
        text="Seleccionar imagen",
        command=seleccionar_fondo,
        height=28,
        width=150,
    )
    btn_fondo.grid(row=0, column=0, sticky="w")

    lbl_fondo = ctk.CTkLabel(row_fondo, text="(sin imagen)", font=ctk.CTkFont(size=12))
    lbl_fondo.grid(row=0, column=1, sticky="w", padx=(8, 0))

    fondo_estilo_var = ctk.StringVar(value="Fill")
    lbl_estilo = ctk.CTkLabel(config, text="Estilo de fondo:", font=ctk.CTkFont(size=12))
    lbl_estilo.grid(row=19, column=0, sticky="w", padx=14, pady=(0, 6))

    opt_estilo = ctk.CTkOptionMenu(
        config,
        values=["Fill", "Fit", "Blur"],
        variable=fondo_estilo_var,
    )
    opt_estilo.grid(row=20, column=0, sticky="w", padx=14, pady=(0, 12))

    row_fondo_escala = ctk.CTkFrame(config, fg_color="transparent")
    row_fondo_escala.grid(row=21, column=0, sticky="ew", padx=14, pady=(0, 10))
    row_fondo_escala.grid_columnconfigure(1, weight=1)

    lbl_fondo_escala = ctk.CTkLabel(row_fondo_escala, text="Tamano video sobre fondo", font=ctk.CTkFont(size=12))
    lbl_fondo_escala.grid(row=0, column=0, sticky="w")

    entry_fondo_escala = ctk.CTkEntry(row_fondo_escala, width=80)
    entry_fondo_escala.insert(0, "0.92")
    entry_fondo_escala.grid(row=0, column=1, sticky="w", padx=(6, 0))

    btn_clear_fondo = ctk.CTkButton(
        row_fondo_escala,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_fondo_escala),
    )
    btn_clear_fondo.grid(row=0, column=2, sticky="e", padx=(8, 0))
    if modo_sin_bordes:
        pass

    row_recorte = ctk.CTkFrame(config, fg_color="transparent")
    row_recorte.grid(row=22, column=0, sticky="ew", padx=14, pady=(0, 10))
    row_recorte.grid_columnconfigure(1, weight=1)

    lbl_recorte = ctk.CTkLabel(row_recorte, text="Recorte total", font=ctk.CTkFont(size=12))
    lbl_recorte.grid(row=0, column=0, sticky="w")

    entry_recorte_total = ctk.CTkEntry(row_recorte, width=80)
    entry_recorte_total.insert(0, "0.12")
    entry_recorte_total.grid(row=0, column=1, sticky="w", padx=(6, 0))

    btn_clear_recorte = ctk.CTkButton(
        row_recorte,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_recorte_total),
    )
    btn_clear_recorte.grid(row=0, column=2, sticky="e", padx=(8, 0))

    hint_recorte = ctk.CTkLabel(
        config,
        text="Ajusta si queda espacio negro. Valores 0.05 - 0.20",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    hint_recorte.grid(row=23, column=0, sticky="w", padx=14, pady=(0, 12))
    if modo_sin_bordes:
        row_recorte.grid_remove()
        hint_recorte.grid_remove()
        chk_visualizador.grid_remove()
        lbl_pos_visual.grid_remove()
        opt_pos_visual.grid_remove()
        lbl_opacity.grid_remove()
        lbl_opacity_value.grid_remove()
        slider_opacity.grid_remove()
        lbl_color.grid_remove()
        entry_color.grid_remove()
        lbl_margin.grid_remove()
        lbl_margin_value.grid_remove()
        slider_margin.grid_remove()
    row_recorte_manual = ctk.CTkFrame(config, fg_color="transparent")
    row_recorte_manual.grid(row=24, column=0, sticky="ew", padx=14, pady=(0, 10))
    row_recorte_manual.grid_columnconfigure(1, weight=1)
    row_recorte_manual.grid_columnconfigure(3, weight=1)

    lbl_recorte_top = ctk.CTkLabel(row_recorte_manual, text="Recorte Top", font=ctk.CTkFont(size=12))
    lbl_recorte_top.grid(row=0, column=0, sticky="w")
    entry_recorte_top = ctk.CTkEntry(row_recorte_manual, width=70)
    entry_recorte_top.insert(0, f"{defaults.get('recorte_manual_top', 0.08):.2f}")
    entry_recorte_top.grid(row=0, column=1, sticky="w", padx=(6, 12))

    lbl_recorte_bottom = ctk.CTkLabel(row_recorte_manual, text="Recorte Bottom", font=ctk.CTkFont(size=12))
    lbl_recorte_bottom.grid(row=0, column=2, sticky="w")
    entry_recorte_bottom = ctk.CTkEntry(row_recorte_manual, width=70)
    entry_recorte_bottom.insert(0, f"{defaults.get('recorte_manual_bottom', 0.08):.2f}")
    entry_recorte_bottom.grid(row=0, column=3, sticky="w", padx=(6, 0))

    hint_recorte_manual = ctk.CTkLabel(
        config,
        text="Recorte manual en proporciÃ³n (0.05 - 0.25). Ej: 0.08",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    hint_recorte_manual.grid(row=25, column=0, sticky="w", padx=14, pady=(0, 12))
    if not modo_sin_bordes:
        row_recorte_manual.grid_remove()
        hint_recorte_manual.grid_remove()

    row_inset = ctk.CTkFrame(config, fg_color="transparent")
    row_inset.grid(row=26, column=0, sticky="ew", padx=14, pady=(0, 8))
    row_inset.grid_columnconfigure(1, weight=1)

    lbl_inset = ctk.CTkLabel(row_inset, text="Encuadre (porcentaje)", font=ctk.CTkFont(size=12))
    lbl_inset.grid(row=0, column=0, sticky="w")

    inset_frame = ctk.CTkFrame(config, fg_color="transparent")
    inset_frame.grid(row=27, column=0, sticky="ew", padx=14, pady=(0, 10))
    inset_frame.grid_columnconfigure(1, weight=1)
    inset_frame.grid_columnconfigure(3, weight=1)

    inset_left_var = tk.DoubleVar(value=float(defaults.get("inset_left_pct", 4.0)))
    inset_right_var = tk.DoubleVar(value=float(defaults.get("inset_right_pct", 4.0)))
    inset_top_var = tk.DoubleVar(value=float(defaults.get("inset_top_pct", 8.0)))
    inset_bottom_var = tk.DoubleVar(value=float(defaults.get("inset_bottom_pct", 8.0)))
    inset_zoom_var = tk.DoubleVar(value=float(defaults.get("zoom", 1.0)))

    def _set_entry(entry, value, decimals=1):
        entry.delete(0, "end")
        entry.insert(0, f"{float(value):.{decimals}f}")

    lbl_left = ctk.CTkLabel(inset_frame, text="Izq %", font=ctk.CTkFont(size=12))
    lbl_left.grid(row=0, column=0, sticky="w")
    entry_left = ctk.CTkEntry(inset_frame, width=60)
    entry_left.insert(0, f"{float(defaults.get('inset_left_pct', 4.0)):.1f}")
    entry_left.grid(row=0, column=1, sticky="w", padx=(6, 12))
    slider_left = ctk.CTkSlider(
        inset_frame, from_=0, to=20, number_of_steps=40,
        variable=inset_left_var,
        command=lambda v: _set_entry(entry_left, v),
        width=140,
    )
    slider_left.grid(row=0, column=2, sticky="w", padx=(0, 10))

    lbl_right = ctk.CTkLabel(inset_frame, text="Der %", font=ctk.CTkFont(size=12))
    lbl_right.grid(row=0, column=3, sticky="w")
    entry_right = ctk.CTkEntry(inset_frame, width=60)
    entry_right.insert(0, f"{float(defaults.get('inset_right_pct', 4.0)):.1f}")
    entry_right.grid(row=0, column=4, sticky="w", padx=(6, 12))
    slider_right = ctk.CTkSlider(
        inset_frame, from_=0, to=20, number_of_steps=40,
        variable=inset_right_var,
        command=lambda v: _set_entry(entry_right, v),
        width=140,
    )
    slider_right.grid(row=0, column=5, sticky="w")

    lbl_top = ctk.CTkLabel(inset_frame, text="Arriba %", font=ctk.CTkFont(size=12))
    lbl_top.grid(row=1, column=0, sticky="w", pady=(8, 0))
    entry_top = ctk.CTkEntry(inset_frame, width=60)
    entry_top.insert(0, f"{float(defaults.get('inset_top_pct', 8.0)):.1f}")
    entry_top.grid(row=1, column=1, sticky="w", padx=(6, 12), pady=(8, 0))
    slider_top = ctk.CTkSlider(
        inset_frame, from_=0, to=30, number_of_steps=60,
        variable=inset_top_var,
        command=lambda v: _set_entry(entry_top, v),
        width=140,
    )
    slider_top.grid(row=1, column=2, sticky="w", padx=(0, 10), pady=(8, 0))

    lbl_bottom = ctk.CTkLabel(inset_frame, text="Abajo %", font=ctk.CTkFont(size=12))
    lbl_bottom.grid(row=1, column=3, sticky="w", pady=(8, 0))
    entry_bottom = ctk.CTkEntry(inset_frame, width=60)
    entry_bottom.insert(0, f"{float(defaults.get('inset_bottom_pct', 8.0)):.1f}")
    entry_bottom.grid(row=1, column=4, sticky="w", padx=(6, 12), pady=(8, 0))
    slider_bottom = ctk.CTkSlider(
        inset_frame, from_=0, to=30, number_of_steps=60,
        variable=inset_bottom_var,
        command=lambda v: _set_entry(entry_bottom, v),
        width=140,
    )
    slider_bottom.grid(row=1, column=5, sticky="w", pady=(8, 0))

    lbl_zoom = ctk.CTkLabel(inset_frame, text="Zoom", font=ctk.CTkFont(size=12))
    lbl_zoom.grid(row=2, column=0, sticky="w", pady=(8, 0))
    entry_zoom = ctk.CTkEntry(inset_frame, width=60)
    entry_zoom.insert(0, f"{float(defaults.get('zoom', 1.0)):.2f}")
    entry_zoom.grid(row=2, column=1, sticky="w", padx=(6, 12), pady=(8, 0))
    slider_zoom = ctk.CTkSlider(
        inset_frame, from_=0.8, to=1.3, number_of_steps=50,
        variable=inset_zoom_var,
        command=lambda v: _set_entry(entry_zoom, v, decimals=2),
        width=140,
    )
    slider_zoom.grid(row=2, column=2, sticky="w", padx=(0, 10), pady=(8, 0))

    if not modo_sin_bordes:
        row_inset.grid_remove()
        inset_frame.grid_remove()

    cintas_card = ctk.CTkFrame(config, corner_radius=10)
    cintas_card.grid(row=28, column=0, sticky="ew", padx=14, pady=(0, 10))
    cintas_card.grid_columnconfigure(0, weight=1)

    cintas_enabled_var = tk.BooleanVar(value=True)
    chk_cintas = ctk.CTkCheckBox(
        cintas_card,
        text="Agregar cintas (nombre y rol)",
        variable=cintas_enabled_var,
    )
    chk_cintas.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 6))

    def _cinta_defaults(idx, key, fallback):
        try:
            return float(cintas_defaults[idx].get(key, fallback))
        except Exception:
            return fallback

    def _cinta_text(idx, key, fallback):
        try:
            return str(cintas_defaults[idx].get(key, fallback))
        except Exception:
            return fallback

    left_cfg = ctk.CTkFrame(cintas_card, fg_color="transparent")
    left_cfg.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
    left_cfg.grid_columnconfigure(1, weight=1)
    left_cfg.grid_columnconfigure(3, weight=1)

    c1_title = ctk.CTkLabel(left_cfg, text="Cinta izquierda", font=ctk.CTkFont(size=12, weight="bold"))
    c1_title.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

    entry_cinta_nombre_1 = ctk.CTkEntry(left_cfg, width=220)
    entry_cinta_nombre_1.insert(0, _cinta_text(0, "nombre", "Invitado"))
    entry_cinta_nombre_1.grid(row=1, column=0, columnspan=2, sticky="w", padx=(0, 12))
    entry_cinta_rol_1 = ctk.CTkEntry(left_cfg, width=220)
    entry_cinta_rol_1.insert(0, _cinta_text(0, "rol", "Rol / Profesión"))
    entry_cinta_rol_1.grid(row=1, column=2, columnspan=2, sticky="w")

    entry_cinta_bg_1 = ctk.CTkEntry(left_cfg, width=90)
    entry_cinta_bg_1.insert(0, _cinta_text(0, "bg_color", "#000000"))
    entry_cinta_bg_1.grid(row=2, column=0, sticky="w", pady=(6, 0))
    entry_cinta_border_1 = ctk.CTkEntry(left_cfg, width=90)
    entry_cinta_border_1.insert(0, _cinta_text(0, "border_color", "#FFC400"))
    entry_cinta_border_1.grid(row=2, column=1, sticky="w", padx=(8, 12), pady=(6, 0))
    entry_cinta_text_1 = ctk.CTkEntry(left_cfg, width=90)
    entry_cinta_text_1.insert(0, _cinta_text(0, "text_color", "#FFFFFF"))
    entry_cinta_text_1.grid(row=2, column=2, sticky="w", pady=(6, 0))

    entry_cinta_left_1 = ctk.CTkEntry(left_cfg, width=70)
    entry_cinta_left_1.insert(0, f"{_cinta_defaults(0, 'left_pct', 6.0):.1f}")
    entry_cinta_left_1.grid(row=3, column=0, sticky="w", pady=(6, 0))
    entry_cinta_top_1 = ctk.CTkEntry(left_cfg, width=70)
    entry_cinta_top_1.insert(0, f"{_cinta_defaults(0, 'top_pct', 50.0):.1f}")
    entry_cinta_top_1.grid(row=3, column=1, sticky="w", padx=(8, 12), pady=(6, 0))
    entry_cinta_width_1 = ctk.CTkEntry(left_cfg, width=70)
    entry_cinta_width_1.insert(0, f"{_cinta_defaults(0, 'width_pct', 42.0):.1f}")
    entry_cinta_width_1.grid(row=3, column=2, sticky="w", pady=(6, 0))
    entry_cinta_height_1 = ctk.CTkEntry(left_cfg, width=70)
    entry_cinta_height_1.insert(0, f"{_cinta_defaults(0, 'height_pct', 10.0):.1f}")
    entry_cinta_height_1.grid(row=3, column=3, sticky="w", padx=(8, 0), pady=(6, 0))

    # positions moved below color fields

    right_cfg = ctk.CTkFrame(cintas_card, fg_color="transparent")
    right_cfg.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
    right_cfg.grid_columnconfigure(1, weight=1)
    right_cfg.grid_columnconfigure(3, weight=1)

    c2_title = ctk.CTkLabel(right_cfg, text="Cinta derecha", font=ctk.CTkFont(size=12, weight="bold"))
    c2_title.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

    entry_cinta_nombre_2 = ctk.CTkEntry(right_cfg, width=220)
    entry_cinta_nombre_2.insert(0, _cinta_text(1, "nombre", "Host"))
    entry_cinta_nombre_2.grid(row=1, column=0, columnspan=2, sticky="w", padx=(0, 12))
    entry_cinta_rol_2 = ctk.CTkEntry(right_cfg, width=220)
    entry_cinta_rol_2.insert(0, _cinta_text(1, "rol", "Rol / Profesión"))
    entry_cinta_rol_2.grid(row=1, column=2, columnspan=2, sticky="w")

    entry_cinta_bg_2 = ctk.CTkEntry(right_cfg, width=90)
    entry_cinta_bg_2.insert(0, _cinta_text(1, "bg_color", "#000000"))
    entry_cinta_bg_2.grid(row=2, column=0, sticky="w", pady=(6, 0))
    entry_cinta_border_2 = ctk.CTkEntry(right_cfg, width=90)
    entry_cinta_border_2.insert(0, _cinta_text(1, "border_color", "#FFC400"))
    entry_cinta_border_2.grid(row=2, column=1, sticky="w", padx=(8, 12), pady=(6, 0))
    entry_cinta_text_2 = ctk.CTkEntry(right_cfg, width=90)
    entry_cinta_text_2.insert(0, _cinta_text(1, "text_color", "#FFFFFF"))
    entry_cinta_text_2.grid(row=2, column=2, sticky="w", pady=(6, 0))

    entry_cinta_left_2 = ctk.CTkEntry(right_cfg, width=70)
    entry_cinta_left_2.insert(0, f"{_cinta_defaults(1, 'left_pct', 48.0):.1f}")
    entry_cinta_left_2.grid(row=3, column=0, sticky="w", pady=(6, 0))
    entry_cinta_top_2 = ctk.CTkEntry(right_cfg, width=70)
    entry_cinta_top_2.insert(0, f"{_cinta_defaults(1, 'top_pct', 52.0):.1f}")
    entry_cinta_top_2.grid(row=3, column=1, sticky="w", padx=(8, 12), pady=(6, 0))
    entry_cinta_width_2 = ctk.CTkEntry(right_cfg, width=70)
    entry_cinta_width_2.insert(0, f"{_cinta_defaults(1, 'width_pct', 42.0):.1f}")
    entry_cinta_width_2.grid(row=3, column=2, sticky="w", pady=(6, 0))
    entry_cinta_height_2 = ctk.CTkEntry(right_cfg, width=70)
    entry_cinta_height_2.insert(0, f"{_cinta_defaults(1, 'height_pct', 10.0):.1f}")
    entry_cinta_height_2.grid(row=3, column=3, sticky="w", padx=(8, 0), pady=(6, 0))

    # positions moved below color fields

    if not modo_sin_bordes:
        cintas_card.grid_remove()

    msg_card = ctk.CTkFrame(config, corner_radius=10)
    msg_card.grid(row=29, column=0, sticky="ew", padx=14, pady=(0, 10))
    msg_card.grid_columnconfigure(0, weight=1)

    mensajes_enabled_var = tk.BooleanVar(value=True)
    chk_msg = ctk.CTkCheckBox(
        msg_card,
        text="Agregar mensaje superior",
        variable=mensajes_enabled_var,
    )
    chk_msg.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 6))

    def _msg_default(key, fallback):
        try:
            return mensajes_defaults[0].get(key, fallback)
        except Exception:
            return fallback

    msg_fontfile = str(_msg_default("fontfile", "C:\\Windows\\Fonts\\arialbd.ttf"))

    msg_row = ctk.CTkFrame(msg_card, fg_color="transparent")
    msg_row.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
    msg_row.grid_columnconfigure(1, weight=1)
    msg_row.grid_columnconfigure(3, weight=1)

    entry_msg_textval = ctk.CTkEntry(msg_row, width=280)
    entry_msg_textval.insert(0, str(_msg_default("text", "Suscríbete y comparte")))
    entry_msg_textval.grid(row=0, column=0, columnspan=2, sticky="w", padx=(0, 12))

    entry_msg_bg = ctk.CTkEntry(msg_row, width=90)
    entry_msg_bg.insert(0, str(_msg_default("bg_color", "#D91E18")))
    entry_msg_bg.grid(row=0, column=2, sticky="w")
    entry_msg_text = ctk.CTkEntry(msg_row, width=90)
    entry_msg_text.insert(0, str(_msg_default("text_color", "#FFFFFF")))
    entry_msg_text.grid(row=0, column=3, sticky="w", padx=(8, 0))
    entry_msg_border = ctk.CTkEntry(msg_row, width=90)
    entry_msg_border.insert(0, str(_msg_default("border_color", "#FFC400")))
    entry_msg_border.grid(row=0, column=4, sticky="w", padx=(8, 0))

    entry_msg_left = ctk.CTkEntry(msg_row, width=70)
    entry_msg_left.insert(0, f"{float(_msg_default('left_pct', 6.0)):.1f}")
    entry_msg_left.grid(row=1, column=0, sticky="w", pady=(6, 0))
    entry_msg_top = ctk.CTkEntry(msg_row, width=70)
    entry_msg_top.insert(0, f"{float(_msg_default('top_pct', 6.0)):.1f}")
    entry_msg_top.grid(row=1, column=1, sticky="w", padx=(8, 12), pady=(6, 0))
    entry_msg_width = ctk.CTkEntry(msg_row, width=70)
    entry_msg_width.insert(0, f"{float(_msg_default('width_pct', 48.0)):.1f}")
    entry_msg_width.grid(row=1, column=2, sticky="w", pady=(6, 0))
    entry_msg_height = ctk.CTkEntry(msg_row, width=70)
    entry_msg_height.insert(0, f"{float(_msg_default('height_pct', 6.0)):.1f}")
    entry_msg_height.grid(row=1, column=3, sticky="w", padx=(8, 0), pady=(6, 0))

    if not modo_sin_bordes:
        msg_card.grid_remove()

    bg_crop_card = ctk.CTkFrame(config, corner_radius=10)
    bg_crop_card.grid(row=30, column=0, sticky="ew", padx=14, pady=(0, 10))
    bg_crop_card.grid_columnconfigure(1, weight=1)
    lbl_bg_crop = ctk.CTkLabel(bg_crop_card, text="Recorte fondo (%)", font=ctk.CTkFont(size=12))
    lbl_bg_crop.grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))

    entry_bg_crop_top = ctk.CTkEntry(bg_crop_card, width=70)
    entry_bg_crop_top.insert(0, f"{float(defaults.get('bg_crop_top_pct', 0.0)):.1f}")
    entry_bg_crop_top.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
    lbl_bg_top = ctk.CTkLabel(bg_crop_card, text="Top", font=ctk.CTkFont(size=11))
    lbl_bg_top.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 8))

    entry_bg_crop_bottom = ctk.CTkEntry(bg_crop_card, width=70)
    entry_bg_crop_bottom.insert(0, f"{float(defaults.get('bg_crop_bottom_pct', 20.0)):.1f}")
    entry_bg_crop_bottom.grid(row=1, column=1, sticky="w", padx=8, pady=(0, 8))
    lbl_bg_bottom = ctk.CTkLabel(bg_crop_card, text="Bottom", font=ctk.CTkFont(size=11))
    lbl_bg_bottom.grid(row=2, column=1, sticky="w", padx=8, pady=(0, 8))

    if not modo_sin_bordes:
        bg_crop_card.grid_remove()

    recorte_bordes_var = ctk.BooleanVar(value=modo_sin_bordes)
    chk_recorte_bordes = ctk.CTkCheckBox(
        config,
        text="Recortar bordes negros (mantener formato original)",
        variable=recorte_bordes_var,
    )
    chk_recorte_bordes.grid(row=31, column=0, sticky="w", padx=14, pady=(0, 12))
    if modo_sin_bordes:
        chk_recorte_bordes.configure(state="disabled")
        chk_recorte_bordes.grid_remove()
    actions = ctk.CTkFrame(top, corner_radius=10)
    actions.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    actions.grid_columnconfigure(0, weight=1)

    lbl_acc = ctk.CTkLabel(actions, text="Seleccion y ejecucion", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_acc.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    def on_click_local():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            estado["path"] = video
            estado["es_audio"] = False
            set_preview_enabled(True)
            cargar_video_preview(video)
            log(f"Video seleccionado: {video}")

    btn_local = ctk.CTkButton(actions, text="Seleccionar Video Local", command=on_click_local, height=44)
    btn_local.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

    btn_iniciar = ctk.CTkButton(actions, text="Cortar", command=iniciar_proceso, height=46)
    btn_iniciar.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))

    procesar_todo_var = ctk.BooleanVar(value=False)
    chk_procesar_todo = ctk.CTkCheckBox(
        actions,
        text="Procesar todo (corte + SRT + subtitulado)",
        variable=procesar_todo_var,
    )
    chk_procesar_todo.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 8))

    srt_row = ctk.CTkFrame(actions, fg_color="transparent")
    srt_row.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 8))
    srt_row.grid_columnconfigure(1, weight=1)

    auto_subs_var = tk.BooleanVar(value=True)
    auto_frame = ctk.CTkFrame(actions, fg_color="transparent")
    auto_frame.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 8))
    auto_frame.grid_columnconfigure(1, weight=1)
    lbl_auto = ctk.CTkLabel(
        auto_frame,
        text="Agregar todo y subir a YouTube (privado)",
        font=ctk.CTkFont(size=12, weight="bold"),
    )
    lbl_auto.grid(row=0, column=0, sticky="w", columnspan=2)
    switch_subs = ctk.CTkSwitch(
        auto_frame,
        text="Con subtítulos",
        variable=auto_subs_var,
    )
    switch_subs.grid(row=1, column=0, sticky="w", pady=(4, 0))
    btn_auto_youtube = ctk.CTkButton(
        auto_frame,
        text="Agregar todo y subir",
        command=lambda: agregar_todo_youtube(),
        height=40,
    )
    btn_auto_youtube.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    lbl_modelo = ctk.CTkLabel(srt_row, text="Modelo SRT", font=ctk.CTkFont(size=12))
    lbl_modelo.grid(row=0, column=0, sticky="w")

    modelo_var = ctk.StringVar(value="base")
    opt_modelo = ctk.CTkOptionMenu(
        srt_row,
        values=["tiny", "base", "small", "medium", "large"],
        variable=modelo_var,
    )
    opt_modelo.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_idioma = ctk.CTkLabel(srt_row, text="Idioma", font=ctk.CTkFont(size=12))
    lbl_idioma.grid(row=1, column=0, sticky="w", pady=(8, 0))

    idioma_var = ctk.StringVar(value="auto")
    opt_idioma = ctk.CTkOptionMenu(
        srt_row,
        values=["auto", "es", "en", "pt", "fr"],
        variable=idioma_var,
    )
    opt_idioma.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
    if modo_sin_bordes:
        chk_procesar_todo.grid_remove()
        srt_row.grid_remove()
        auto_frame.grid_remove()

    def abrir_carpeta_base():
        base = output_base_dir(estado["path"]) if estado.get("path") else os.path.abspath("output")
        if not os.path.exists(base):
            os.makedirs(base)
        os.startfile(base)

    btn_abrir_videos = ctk.CTkButton(actions, text="Abrir Carpeta de Videos", command=abrir_carpeta_base, height=40)
    btn_abrir_videos.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 12))

    # --- Corte: preview ---
    preview_card = ctk.CTkFrame(corte_scroll, corner_radius=12)
    preview_card.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
    preview_card.grid_columnconfigure(0, weight=1)
    preview_card.grid_rowconfigure(1, weight=1)

    lbl_preview = ctk.CTkLabel(preview_card, text="Vista previa", font=ctk.CTkFont(size=15, weight="bold"))
    lbl_preview.grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

    video_container = ctk.CTkFrame(preview_card, corner_radius=8)
    video_container.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
    video_container.configure(height=300)
    video_container.grid_propagate(False)

    video_host = tk.Frame(video_container, bg="#000000")
    video_host.pack(fill="both", expand=True)
    video_host.pack_propagate(False)

    video_player = SimpleVideoPlayer(video_host, log_fn=log)

    controls = ctk.CTkFrame(preview_card, fg_color="transparent")
    controls.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
    controls.grid_columnconfigure(1, weight=1)

    btn_play = ctk.CTkButton(controls, text="Play", width=80, height=28, command=lambda: video_player.play())
    btn_play.grid(row=0, column=0, sticky="w")

    btn_pause = ctk.CTkButton(controls, text="Pause", width=80, height=28, command=lambda: video_player.pause())
    btn_pause.grid(row=0, column=1, sticky="w", padx=(8, 0))

    range_card = ctk.CTkFrame(preview_card, fg_color="transparent")
    range_card.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
    range_card.grid_columnconfigure(1, weight=1)

    entry_inicio_var = tk.StringVar(value=format_entry_time(rango.get("inicio", 0.0)))
    entry_fin_var = tk.StringVar(value=format_entry_time(rango.get("fin", 0.0)))

    lbl_inicio = ctk.CTkLabel(range_card, text="Inicio", font=ctk.CTkFont(size=12))
    lbl_inicio.grid(row=0, column=0, sticky="w")

    entry_inicio = ctk.CTkEntry(
        range_card,
        width=120,
        textvariable=entry_inicio_var,
        placeholder_text="mm:ss",
    )
    entry_inicio.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    lbl_inicio_val = ctk.CTkLabel(range_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_inicio_val.grid(row=0, column=2, sticky="e")

    slider_inicio = ctk.CTkSlider(range_card, from_=0, to=1, command=lambda value: on_slider_change("inicio", value))
    slider_inicio.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    lbl_fin = ctk.CTkLabel(range_card, text="Fin", font=ctk.CTkFont(size=12))
    lbl_fin.grid(row=2, column=0, sticky="w")

    entry_fin = ctk.CTkEntry(
        range_card,
        width=120,
        textvariable=entry_fin_var,
        placeholder_text="mm:ss",
    )
    entry_fin.grid(row=2, column=1, sticky="ew", padx=(6, 0))

    lbl_fin_val = ctk.CTkLabel(range_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_fin_val.grid(row=2, column=2, sticky="e")

    slider_fin = ctk.CTkSlider(range_card, from_=0, to=1, command=lambda value: on_slider_change("fin", value))
    slider_fin.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    range_feedback_label = ctk.CTkLabel(
        range_card,
        text="",
        font=ctk.CTkFont(size=11),
        text_color="#ff6b6b",
    )
    range_feedback_label.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    lbl_duracion = ctk.CTkLabel(range_card, text="Duracion", font=ctk.CTkFont(size=12))
    lbl_duracion.grid(row=5, column=0, sticky="w")
    lbl_duracion_val = ctk.CTkLabel(range_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_duracion_val.grid(row=5, column=2, sticky="e")

    ENTRY_DEFAULT_BORDER = entry_inicio.cget("border_color")

    def update_entries_from_state():
        entry_inicio_var.set(format_entry_time(rango["inicio"]))
        entry_fin_var.set(format_entry_time(rango["fin"]))

    def clear_feedback():
        if ENTRY_DEFAULT_BORDER is not None:
            entry_inicio.configure(border_color=ENTRY_DEFAULT_BORDER)
            entry_fin.configure(border_color=ENTRY_DEFAULT_BORDER)
        range_feedback_label.configure(text="")

    def mark_entry_invalid(entry_widget, message):
        entry_widget.configure(border_color=ENTRY_ERROR_BORDER)
        range_feedback_label.configure(text=message)

    def set_slider_values(start, end):
        nonlocal slider_programmatic
        slider_programmatic = True
        try:
            slider_inicio.set(start)
            slider_fin.set(end)
        finally:
            slider_programmatic = False

    def sync_state_from_sliders():
        rango["inicio"] = slider_inicio.get()
        rango["fin"] = slider_fin.get()
        actualizar_etiquetas_rango()
        update_entries_from_state()
        clear_feedback()

    def set_range_seconds(start, end):
        max_duration = max(0.0, rango.get("duracion", 0.0))
        start = max(0.0, min(start, max_duration))
        end = max(start, min(end, max_duration))
        rango["inicio"] = start
        rango["fin"] = end
        set_slider_values(start, end)
        actualizar_etiquetas_rango()
        update_entries_from_state()
        clear_feedback()

    def on_slider_change(side, _value):
        if slider_programmatic:
            return
        inicio_val = slider_inicio.get()
        fin_val = slider_fin.get()
        if side == "inicio" and inicio_val > fin_val:
            set_slider_values(inicio_val, inicio_val)
            fin_val = inicio_val
        elif side == "fin" and fin_val < inicio_val:
            set_slider_values(fin_val, fin_val)
            inicio_val = fin_val
        sync_state_from_sliders()

    def on_entry_commit(side, _event=None):
        clear_feedback()
        try:
            inicio_val = parse_entry_time(entry_inicio_var.get())
        except ValueError as exc:
            mark_entry_invalid(entry_inicio, str(exc))
            return
        try:
            fin_val = parse_entry_time(entry_fin_var.get())
        except ValueError as exc:
            mark_entry_invalid(entry_fin, str(exc))
            return
        if inicio_val >= fin_val:
            target_entry = entry_inicio if side == "inicio" else entry_fin
            mark_entry_invalid(target_entry, "Inicio debe ser menor que Fin")
            return
        if rango["duracion"] > 0 and fin_val > rango["duracion"]:
            mark_entry_invalid(entry_fin, "Fin no puede superar la duración total del video")
            return
        set_range_seconds(inicio_val, fin_val)

    entry_inicio.bind("<FocusOut>", lambda event: on_entry_commit("inicio"))
    entry_inicio.bind("<Return>", lambda event: on_entry_commit("inicio"))
    entry_fin.bind("<FocusOut>", lambda event: on_entry_commit("fin"))
    entry_fin.bind("<Return>", lambda event: on_entry_commit("fin"))

    log_card, _log_widget, log_local = helpers.create_log_panel(
        container,
        title="Actividad",
        height=220,
        mirror_fn=context.get("log_global"),
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    def log_seccion(titulo):
        log_local("")
        log_local("========================================")
        log_local(f"=== {titulo}")
        log_local("========================================")

    log = log_local

    return {
        "scroll": corte_scroll,
        "set_preview_enabled": set_preview_enabled,
        "cargar_video_preview": cargar_video_preview,
        "actualizar_etiquetas_rango": actualizar_etiquetas_rango,
    }
