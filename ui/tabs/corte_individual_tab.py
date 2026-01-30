import os
import threading
import customtkinter as ctk
from tkinter import colorchooser

from core.workflow import procesar_corte_individual, procesar_srt, procesar_quemar_srt
from core.utils import obtener_duracion_segundos, output_base_dir
from ui.shared import helpers


def create_tab(parent, context):
    estado = context["estado"]
    rango_ind = context["rango_ind"]
    log = context["log"]
    limpiar_entry = context["limpiar_entry"]
    alerta_busy = context["alerta_busy"]
    abrir_videos = context["abrir_videos"]
    stop_control = context["stop_control"]
    beep_fin = context["beep_fin"]
    renombrar_si_largo = context["renombrar_si_largo"]
    set_preview_enabled = context["set_preview_enabled"]
    cargar_video_preview = context["cargar_video_preview"]

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

    def actualizar_etiquetas_rango_ind():
        inicio = slider_inicio_ind.get()
        fin = slider_fin_ind.get()
        lbl_inicio_val_ind.configure(text=format_time(inicio))
        lbl_fin_val_ind.configure(text=format_time(fin))
        lbl_duracion_val_ind.configure(text=format_time(rango_ind["duracion"]))

    def on_inicio_ind_change(value):
        if value > slider_fin_ind.get():
            slider_fin_ind.set(value)
        actualizar_etiquetas_rango_ind()

    def on_fin_ind_change(value):
        if value < slider_inicio_ind.get():
            slider_inicio_ind.set(value)
        actualizar_etiquetas_rango_ind()

    def format_time(seconds):
        seconds = max(0, float(seconds))
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    ind_scroll = ctk.CTkScrollableFrame(left, corner_radius=0)
    ind_scroll.grid(row=0, column=0, sticky="nsew")
    ind_scroll.grid_columnconfigure(0, weight=1)

    ind_card = ctk.CTkFrame(ind_scroll, corner_radius=12)
    ind_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    ind_card.grid_columnconfigure(0, weight=1)

    lbl_ind_title = ctk.CTkLabel(
        ind_card,
        text="Corte individual vertical (9:16)",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_ind_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_ind_hint = ctk.CTkLabel(
        ind_card,
        text="Elige el punto de recorte (centro, izquierda o derecha) y corta por minutos.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_ind_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    ind_select = ctk.CTkFrame(ind_card, fg_color="transparent")
    ind_select.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    ind_select.grid_columnconfigure(1, weight=1)

    def on_click_individual_video():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            video = renombrar_si_largo(video)
            if not video:
                return
            estado["path"] = video
            estado["es_audio"] = False
            set_preview_enabled(True)
            cargar_video_preview(video)
            cargar_rango_individual(video)
            log(f"Video seleccionado: {video}")

    btn_ind_video = ctk.CTkButton(
        ind_select,
        text="Seleccionar Video",
        command=on_click_individual_video,
        height=40,
    )
    btn_ind_video.grid(row=0, column=0, sticky="w")

    lbl_ind_file = ctk.CTkLabel(
        ind_select,
        text="(usa el mismo rango de la pestana Corte)",
        font=ctk.CTkFont(size=12),
    )
    lbl_ind_file.grid(row=0, column=1, sticky="w", padx=(12, 0))

    ind_min_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    ind_min_row.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    ind_min_row.grid_columnconfigure(1, weight=1)

    lbl_ind_min = ctk.CTkLabel(ind_min_row, text="Minutos por parte", font=ctk.CTkFont(size=13))
    lbl_ind_min.grid(row=0, column=0, sticky="w")

    entry_ind_min = ctk.CTkEntry(ind_min_row, width=120)
    entry_ind_min.insert(0, "5")
    entry_ind_min.grid(row=0, column=1, sticky="e")

    btn_clear_ind_min = ctk.CTkButton(
        ind_min_row,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_ind_min),
    )
    btn_clear_ind_min.grid(row=0, column=2, sticky="e", padx=(8, 0))

    pos_var = ctk.StringVar(value="C")
    lbl_pos = ctk.CTkLabel(ind_card, text="Posicion de recorte:", font=ctk.CTkFont(size=13))
    lbl_pos.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 6))

    rb_pos_c = ctk.CTkRadioButton(ind_card, text="Centro", variable=pos_var, value="C")
    rb_pos_c.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 4))
    rb_pos_l = ctk.CTkRadioButton(ind_card, text="Izquierda", variable=pos_var, value="L")
    rb_pos_l.grid(row=6, column=0, sticky="w", padx=16, pady=(0, 4))
    rb_pos_r = ctk.CTkRadioButton(ind_card, text="Derecha", variable=pos_var, value="R")
    rb_pos_r.grid(row=7, column=0, sticky="w", padx=16, pady=(0, 12))

    zoom_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    zoom_row.grid(row=8, column=0, sticky="ew", padx=16, pady=(0, 10))
    zoom_row.grid_columnconfigure(1, weight=1)

    lbl_zoom = ctk.CTkLabel(zoom_row, text="Zoom (alejar/acercar)", font=ctk.CTkFont(size=12))
    lbl_zoom.grid(row=0, column=0, sticky="w")

    entry_zoom = ctk.CTkEntry(zoom_row, width=80)
    entry_zoom.insert(0, "1.0")
    entry_zoom.grid(row=0, column=1, sticky="w", padx=(6, 0))

    btn_clear_zoom = ctk.CTkButton(
        zoom_row,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_zoom),
    )
    btn_clear_zoom.grid(row=0, column=2, sticky="e", padx=(8, 0))

    zoom_slider_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    zoom_slider_row.grid(row=9, column=0, sticky="ew", padx=16, pady=(0, 12))
    zoom_slider_row.grid_columnconfigure(1, weight=1)

    lbl_zoom_min = ctk.CTkLabel(zoom_slider_row, text="0.7", font=ctk.CTkFont(size=11))
    lbl_zoom_min.grid(row=0, column=0, sticky="w")

    lbl_zoom_val = ctk.CTkLabel(zoom_slider_row, text="1.00", font=ctk.CTkFont(size=11))
    lbl_zoom_val.grid(row=0, column=2, sticky="e")

    def on_zoom_change(value):
        try:
            v = float(value)
        except Exception:
            v = 1.0
        lbl_zoom_val.configure(text=f"{v:.2f}")
        entry_zoom.delete(0, "end")
        entry_zoom.insert(0, f"{v:.2f}")

    slider_zoom = ctk.CTkSlider(zoom_slider_row, from_=0.7, to=1.3, command=on_zoom_change)
    slider_zoom.set(1.0)
    slider_zoom.grid(row=0, column=1, sticky="ew", padx=(8, 8))

    lbl_zoom_max = ctk.CTkLabel(zoom_slider_row, text="1.3", font=ctk.CTkFont(size=11))
    lbl_zoom_max.grid(row=0, column=3, sticky="e")

    color_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    color_row.grid(row=10, column=0, sticky="ew", padx=16, pady=(0, 12))
    color_row.grid_columnconfigure(1, weight=1)

    lbl_color = ctk.CTkLabel(color_row, text="Color de relleno (hex)", font=ctk.CTkFont(size=12))
    lbl_color.grid(row=0, column=0, sticky="w")

    entry_color = ctk.CTkEntry(color_row, width=120)
    entry_color.insert(0, "#000000")
    entry_color.grid(row=0, column=1, sticky="w", padx=(6, 0))

    def elegir_color():
        color = colorchooser.askcolor(title="Seleccionar color de relleno")
        if color and color[1]:
            entry_color.delete(0, "end")
            entry_color.insert(0, color[1])

    btn_pick_color = ctk.CTkButton(
        color_row,
        text="Elegir",
        width=80,
        height=28,
        command=elegir_color,
    )
    btn_pick_color.grid(row=0, column=2, sticky="e", padx=(8, 0))

    btn_clear_color = ctk.CTkButton(
        color_row,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_color),
    )
    btn_clear_color.grid(row=0, column=3, sticky="e", padx=(8, 0))

    motion_var = ctk.BooleanVar(value=False)
    chk_motion = ctk.CTkCheckBox(
        ind_card,
        text="Zoom in/out cada 30s",
        variable=motion_var,
    )
    chk_motion.grid(row=11, column=0, sticky="w", padx=16, pady=(0, 8))

    motion_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    motion_row.grid(row=12, column=0, sticky="ew", padx=16, pady=(0, 12))
    motion_row.grid_columnconfigure(1, weight=1)

    lbl_motion = ctk.CTkLabel(motion_row, text="Intensidad zoom", font=ctk.CTkFont(size=12))
    lbl_motion.grid(row=0, column=0, sticky="w")

    entry_motion = ctk.CTkEntry(motion_row, width=80)
    entry_motion.insert(0, "0.08")
    entry_motion.grid(row=0, column=1, sticky="w", padx=(6, 0))

    btn_clear_motion = ctk.CTkButton(
        motion_row,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_motion),
    )
    btn_clear_motion.grid(row=0, column=2, sticky="e", padx=(8, 0))

    motion_period_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    motion_period_row.grid(row=13, column=0, sticky="ew", padx=16, pady=(0, 12))
    motion_period_row.grid_columnconfigure(1, weight=1)

    lbl_motion_period = ctk.CTkLabel(motion_period_row, text="Ciclo (seg)", font=ctk.CTkFont(size=12))
    lbl_motion_period.grid(row=0, column=0, sticky="w")

    entry_motion_period = ctk.CTkEntry(motion_period_row, width=80)
    entry_motion_period.insert(0, "30")
    entry_motion_period.grid(row=0, column=1, sticky="w", padx=(6, 0))

    outro_var = ctk.BooleanVar(value=False)
    chk_outro = ctk.CTkCheckBox(
        ind_card,
        text="Agregar tarjeta final (imagen + texto)",
        variable=outro_var,
    )
    chk_outro.grid(row=14, column=0, sticky="w", padx=16, pady=(0, 8))

    outro_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    outro_row.grid(row=15, column=0, sticky="ew", padx=16, pady=(0, 12))
    outro_row.grid_columnconfigure(1, weight=1)

    outro_state = {"image": None}

    def on_click_outro_image():
        from ui.dialogs import seleccionar_imagen
        img = seleccionar_imagen()
        if img:
            outro_state["image"] = img
            lbl_outro_img.configure(text=os.path.basename(img))
            log(f"Imagen outro: {img}")

    btn_outro_img = ctk.CTkButton(
        outro_row,
        text="Seleccionar imagen",
        command=on_click_outro_image,
        height=28,
        width=150,
    )
    btn_outro_img.grid(row=0, column=0, sticky="w")

    lbl_outro_img = ctk.CTkLabel(outro_row, text="(sin imagen)", font=ctk.CTkFont(size=12))
    lbl_outro_img.grid(row=0, column=1, sticky="w", padx=(8, 0))

    outro_text_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    outro_text_row.grid(row=16, column=0, sticky="ew", padx=16, pady=(0, 12))
    outro_text_row.grid_columnconfigure(1, weight=1)

    lbl_outro_text = ctk.CTkLabel(outro_text_row, text="Texto final", font=ctk.CTkFont(size=12))
    lbl_outro_text.grid(row=0, column=0, sticky="w")

    entry_outro_text = ctk.CTkEntry(outro_text_row)
    entry_outro_text.grid(row=0, column=1, sticky="ew", padx=(8, 0))

    outro_conf_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    outro_conf_row.grid(row=17, column=0, sticky="ew", padx=16, pady=(0, 12))
    outro_conf_row.grid_columnconfigure(1, weight=1)

    lbl_outro_secs = ctk.CTkLabel(outro_conf_row, text="Duracion (seg)", font=ctk.CTkFont(size=12))
    lbl_outro_secs.grid(row=0, column=0, sticky="w")

    entry_outro_secs = ctk.CTkEntry(outro_conf_row, width=80)
    entry_outro_secs.insert(0, "3")
    entry_outro_secs.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_outro_font = ctk.CTkLabel(outro_conf_row, text="Tamano texto", font=ctk.CTkFont(size=12))
    lbl_outro_font.grid(row=1, column=0, sticky="w", pady=(8, 0))

    entry_outro_font = ctk.CTkEntry(outro_conf_row, width=80)
    entry_outro_font.insert(0, "54")
    entry_outro_font.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    outro_color_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    outro_color_row.grid(row=18, column=0, sticky="ew", padx=16, pady=(0, 12))
    outro_color_row.grid_columnconfigure(1, weight=1)

    lbl_outro_color = ctk.CTkLabel(outro_color_row, text="Color texto (hex)", font=ctk.CTkFont(size=12))
    lbl_outro_color.grid(row=0, column=0, sticky="w")

    entry_outro_color = ctk.CTkEntry(outro_color_row, width=120)
    entry_outro_color.insert(0, "#FFFFFF")
    entry_outro_color.grid(row=0, column=1, sticky="w", padx=(6, 0))

    range_ind_card = ctk.CTkFrame(ind_card, fg_color="transparent")
    range_ind_card.grid(row=19, column=0, sticky="ew", padx=16, pady=(0, 14))
    range_ind_card.grid_columnconfigure(1, weight=1)

    lbl_inicio_ind = ctk.CTkLabel(range_ind_card, text="Inicio", font=ctk.CTkFont(size=12))
    lbl_inicio_ind.grid(row=0, column=0, sticky="w")
    lbl_inicio_val_ind = ctk.CTkLabel(range_ind_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_inicio_val_ind.grid(row=0, column=2, sticky="e")

    slider_inicio_ind = ctk.CTkSlider(range_ind_card, from_=0, to=1, command=on_inicio_ind_change)
    slider_inicio_ind.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    lbl_fin_ind = ctk.CTkLabel(range_ind_card, text="Fin", font=ctk.CTkFont(size=12))
    lbl_fin_ind.grid(row=2, column=0, sticky="w")
    lbl_fin_val_ind = ctk.CTkLabel(range_ind_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_fin_val_ind.grid(row=2, column=2, sticky="e")

    slider_fin_ind = ctk.CTkSlider(range_ind_card, from_=0, to=1, command=on_fin_ind_change)
    slider_fin_ind.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 6))

    lbl_duracion_ind = ctk.CTkLabel(range_ind_card, text="Duracion", font=ctk.CTkFont(size=12))
    lbl_duracion_ind.grid(row=4, column=0, sticky="w")
    lbl_duracion_val_ind = ctk.CTkLabel(range_ind_card, text="00:00", font=ctk.CTkFont(size=12))
    lbl_duracion_val_ind.grid(row=4, column=2, sticky="e")

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

    def cargar_rango_individual(path):
        try:
            duracion = obtener_duracion_segundos(path)
        except Exception:
            duracion = 0.0
        rango_ind["duracion"] = max(0.0, duracion)
        slider_inicio_ind.configure(from_=0, to=rango_ind["duracion"])
        slider_fin_ind.configure(from_=0, to=rango_ind["duracion"])
        slider_inicio_ind.set(0)
        slider_fin_ind.set(rango_ind["duracion"])
        actualizar_etiquetas_rango_ind()

    def leer_minutos_ind():
        try:
            valor = float(entry_ind_min.get().strip().replace(",", "."))
            return valor if valor > 0 else 5
        except Exception:
            return 5

    def leer_rango_minutos_ind():
        if rango_ind["duracion"] <= 0:
            return None, None
        inicio = slider_inicio_ind.get()
        fin = slider_fin_ind.get()
        return inicio / 60.0, fin / 60.0

    def iniciar_corte_individual():
        if not estado["path"]:
            log("Selecciona un video primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Corte individual")
        minutos = leer_minutos_ind()
        inicio_min, fin_min = leer_rango_minutos_ind()
        posicion = pos_var.get()
        try:
            zoom = float(entry_zoom.get().strip().replace(",", "."))
        except Exception:
            zoom = slider_zoom.get()
        color = entry_color.get().strip() or "#000000"
        motion = motion_var.get()
        try:
            motion_amount = float(entry_motion.get().strip().replace(",", "."))
        except Exception:
            motion_amount = 0.08
        try:
            motion_period = float(entry_motion_period.get().strip().replace(",", "."))
        except Exception:
            motion_period = 30.0
        outro_enabled = outro_var.get()
        outro_image = outro_state.get("image")
        outro_text = entry_outro_text.get().strip()
        try:
            outro_seconds = float(entry_outro_secs.get().strip().replace(",", "."))
        except Exception:
            outro_seconds = 3.0
        try:
            outro_font = int(entry_outro_font.get().strip())
        except Exception:
            outro_font = 54
        outro_color = entry_outro_color.get().strip() or "#FFFFFF"

        def run_individual():
            try:
                result = procesar_corte_individual(
                    estado["path"],
                    minutos,
                    inicio_min,
                    fin_min,
                    posicion,
                    zoom,
                    color,
                    motion,
                    motion_amount,
                    motion_period,
                    outro_enabled,
                    outro_image,
                    outro_text,
                    outro_seconds,
                    outro_font,
                    outro_color,
                    None,
                    log,
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
                log("Finalizado proceso de corte individual.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error en corte individual: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_individual, daemon=True).start()

    procesar_todo_var = ctk.BooleanVar(value=False)
    chk_procesar_todo = ctk.CTkCheckBox(
        ind_card,
        text="Procesar todo (corte + SRT + subtitulado)",
        variable=procesar_todo_var,
    )
    chk_procesar_todo.grid(row=20, column=0, sticky="w", padx=16, pady=(0, 8))

    srt_row = ctk.CTkFrame(ind_card, fg_color="transparent")
    srt_row.grid(row=21, column=0, sticky="ew", padx=16, pady=(0, 8))
    srt_row.grid_columnconfigure(1, weight=1)

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

    btn_ind_run = ctk.CTkButton(
        ind_card,
        text="Cortar vertical",
        command=iniciar_corte_individual,
        height=46,
    )
    btn_ind_run.grid(row=22, column=0, sticky="ew", padx=16, pady=(0, 8))

    def abrir_carpeta_base():
        base = output_base_dir(estado["path"]) if estado.get("path") else os.path.abspath("output")
        if not os.path.exists(base):
            os.makedirs(base)
        os.startfile(base)

    btn_ind_open = ctk.CTkButton(
        ind_card,
        text="Abrir Carpeta de Videos",
        command=abrir_carpeta_base,
        height=40,
    )
    btn_ind_open.grid(row=23, column=0, sticky="ew", padx=16, pady=(0, 16))

    return {
        "scroll": ind_scroll,
        "actualizar_etiquetas_rango_ind": actualizar_etiquetas_rango_ind,
    }
