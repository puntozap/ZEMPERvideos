import os
import threading
import customtkinter as ctk
import tkinter as tk

from core.ai_youtube import subir_video_youtube_desde_ia
from core.utils import obtener_duracion_segundos, output_base_dir
from core.workflow import procesar_srt, procesar_quemar_srt
from ui.shared.preview import SimpleVideoPlayer
from ui.shared import helpers


def create_tab(parent, context):
    estado = context["estado"]
    rango = context["rango"]
    log = context["log"]
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

    def iniciar_proceso():
        if not estado["path"]:
            log("Selecciona un video primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Corte")
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
        fondo_path = estado["fondo_path"] if fondo_var.get() else None
        fondo_estilo = fondo_estilo_var.get().lower()
        try:
            fondo_escala = float(entry_fondo_escala.get().strip().replace(",", "."))
        except Exception:
            fondo_escala = 0.92

        def run_corte():
            try:
                estado["visualizador"] = visualizador_var.get()
                estado["posicion_visualizador"] = obtener_posicion_visualizador()
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
                    False,
                    fondo_path,
                    fondo_estilo,
                    fondo_escala,
                    solo_video=solo_video_flag,
                    visualizador=visualizador_var.get(),
                    posicion_visualizador=obtener_posicion_visualizador(),
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
        fondo_path = estado["fondo_path"] if fondo_var.get() else None
        fondo_estilo = fondo_estilo_var.get().lower()
        try:
            fondo_escala = float(entry_fondo_escala.get().strip().replace(",", "."))
        except Exception:
            fondo_escala = 0.92

        def run_auto():
            try:
                estado["visualizador"] = visualizador_var.get()
                estado["posicion_visualizador"] = obtener_posicion_visualizador()
                solo_video_flag = auto_subs_var.get()
                if visualizador_var.get():
                    solo_video_flag = False
                result = procesar_video_fn(
                    estado["path"],
                    False,
                    False,
                    minutos,
                    inicio_min,
                    fin_min,
                    True,
                    vertical_var.get(),
                    orden_var.get(),
                    recorte_top,
                    recorte_bottom,
                    False,
                    fondo_path,
                    fondo_estilo,
                    fondo_escala,
                    solo_video=solo_video_flag,
                    visualizador=visualizador_var.get(),
                    posicion_visualizador=obtener_posicion_visualizador(),
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

    fondo_var = ctk.BooleanVar(value=False)
    chk_fondo = ctk.CTkCheckBox(
        config,
        text="Aplicar imagen de fondo",
        variable=fondo_var,
    )
    chk_fondo.grid(row=11, column=0, sticky="w", padx=14, pady=(0, 8))

    row_fondo = ctk.CTkFrame(config, fg_color="transparent")
    row_fondo.grid(row=12, column=0, sticky="ew", padx=14, pady=(0, 10))
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
    lbl_estilo.grid(row=13, column=0, sticky="w", padx=14, pady=(0, 6))

    opt_estilo = ctk.CTkOptionMenu(
        config,
        values=["Fill", "Fit", "Blur"],
        variable=fondo_estilo_var,
    )
    opt_estilo.grid(row=14, column=0, sticky="w", padx=14, pady=(0, 12))

    row_fondo_escala = ctk.CTkFrame(config, fg_color="transparent")
    row_fondo_escala.grid(row=15, column=0, sticky="ew", padx=14, pady=(0, 10))
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

    row_recorte = ctk.CTkFrame(config, fg_color="transparent")
    row_recorte.grid(row=16, column=0, sticky="ew", padx=14, pady=(0, 10))
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
    hint_recorte.grid(row=17, column=0, sticky="w", padx=14, pady=(0, 12))

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
