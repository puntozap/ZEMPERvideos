import os
import threading
import customtkinter as ctk
import tkinter as tk
from core.utils import aplicar_musica_fondo, output_base_dir, obtener_duracion_segundos
from ui.shared import helpers


def create_tab(parent, context):
    estado = context["estado"]
    log_ref = {"fn": context.get("log")}

    def _log(msg: str):
        if log_ref["fn"]:
            log_ref["fn"](msg)

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)
    container.grid_rowconfigure(0, weight=1)

    scroll = ctk.CTkScrollableFrame(container, corner_radius=0)
    scroll.grid(row=0, column=0, sticky="nsew")
    scroll.grid_columnconfigure(0, weight=1)

    card = ctk.CTkFrame(scroll, corner_radius=12)
    card.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
    card.grid_columnconfigure(0, weight=1)

    title = ctk.CTkLabel(card, text="Musica de fondo", font=ctk.CTkFont(size=18, weight="bold"))
    title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    hint = ctk.CTkLabel(
        card,
        text="Configura la pista de fondo para Corte y Corte individual.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    durations = {"video": 0.0, "music": 0.0}

    row_video = ctk.CTkFrame(card, fg_color="transparent")
    row_video.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
    row_video.grid_columnconfigure(1, weight=1)

    lbl_video_dur = ctk.CTkLabel(row_video, text="", font=ctk.CTkFont(size=11), text_color="#9aa4b2")

    def seleccionar_video():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            estado["path"] = video
            estado["es_audio"] = False
            lbl_video.configure(text=os.path.basename(video))
            try:
                durations["video"] = float(obtener_duracion_segundos(video))
            except Exception:
                durations["video"] = 0.0
            if durations["video"] > 0:
                lbl_video_dur.configure(text=f"Duracion: {format_mmss(durations['video'])}")
                slider_video_start.configure(from_=0, to=durations["video"])
            _log(f"Video seleccionado: {video}")

    btn_video = ctk.CTkButton(
        row_video,
        text="Seleccionar video",
        command=seleccionar_video,
        height=30,
        width=150,
    )
    btn_video.grid(row=0, column=0, sticky="w")

    default_video_label = "(sin video)"
    if estado.get("path"):
        try:
            default_video_label = os.path.basename(estado["path"])
        except Exception:
            default_video_label = "(sin video)"
    lbl_video = ctk.CTkLabel(row_video, text=default_video_label, font=ctk.CTkFont(size=12))
    lbl_video.grid(row=0, column=1, sticky="w", padx=(8, 0))
    lbl_video_dur.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(2, 0))

    def parse_time_optional(value: str):
        text = (value or "").strip()
        if not text:
            return None
        if ":" in text:
            parts = text.split(":")
            if len(parts) != 2:
                raise ValueError("Formato mm:ss")
            min_part, sec_part = parts
            try:
                minutes = int(min_part.strip())
            except Exception:
                raise ValueError("Minutos invalidos")
            try:
                seconds = float(sec_part.strip().replace(",", "."))
            except Exception:
                raise ValueError("Segundos invalidos")
            if minutes < 0:
                raise ValueError("Minutos invalidos")
            if seconds < 0 or seconds >= 60:
                raise ValueError("Segundos 00-59")
            return minutes * 60 + seconds
        try:
            seconds = float(text.replace(",", "."))
        except Exception:
            raise ValueError("Formato mm:ss o segundos")
        if seconds < 0:
            raise ValueError("Segundos invalidos")
        return seconds

    def format_mmss(seconds: float | None):
        if seconds is None:
            return ""
        try:
            seconds = max(0.0, float(seconds))
        except Exception:
            return ""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def aplicar_estado():
        estado["musica_fondo_habilitada"] = bool(musica_var.get())
        estado["musica_fondo_volumen"] = float(musica_vol_var.get()) / 100.0
        try:
            estado["musica_fondo_inicio"] = float(parse_time_optional(entry_music_start.get()) or 0.0)
        except Exception as exc:
            _log(f"Inicio musica invalido: {exc}")
            return
        try:
            estado["musica_fondo_fin"] = parse_time_optional(entry_music_end.get())
        except Exception as exc:
            _log(f"Fin musica invalido: {exc}")
            return
        if estado["musica_fondo_fin"] is not None and estado["musica_fondo_fin"] <= estado["musica_fondo_inicio"]:
            _log("Fin musica debe ser mayor que inicio musica.")
            return
        try:
            estado["musica_fondo_inicio_video"] = float(parse_time_optional(entry_music_video_start.get()) or 0.0)
        except Exception as exc:
            _log(f"Inicio musica en video invalido: {exc}")
            return
        _log("Musica de fondo actualizada.")

    musica_var = ctk.BooleanVar(value=bool(estado.get("musica_fondo_habilitada", False)))
    chk_musica = ctk.CTkCheckBox(
        card,
        text="Habilitar musica de fondo",
        variable=musica_var,
        command=aplicar_estado,
    )
    chk_musica.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 8))

    row_music = ctk.CTkFrame(card, fg_color="transparent")
    row_music.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 8))
    row_music.grid_columnconfigure(1, weight=1)

    lbl_music_dur = ctk.CTkLabel(row_music, text="", font=ctk.CTkFont(size=11), text_color="#9aa4b2")

    def seleccionar_musica():
        from ui.dialogs import seleccionar_audio
        audio = seleccionar_audio()
        if audio:
            estado["musica_fondo_path"] = audio
            lbl_music.configure(text=os.path.basename(audio))
            try:
                durations["music"] = float(obtener_duracion_segundos(audio))
            except Exception:
                durations["music"] = 0.0
            if durations["music"] > 0:
                lbl_music_dur.configure(text=f"Duracion: {format_mmss(durations['music'])}")
                slider_music_start.configure(from_=0, to=durations["music"])
                slider_music_end.configure(from_=0, to=durations["music"])
                if slider_music_end.get() <= 0:
                    slider_music_end.set(durations["music"])
            aplicar_estado()

    btn_music = ctk.CTkButton(
        row_music,
        text="Seleccionar musica",
        command=seleccionar_musica,
        height=28,
        width=150,
    )
    btn_music.grid(row=0, column=0, sticky="w")

    default_music_label = "(sin musica)"
    if estado.get("musica_fondo_path"):
        try:
            default_music_label = os.path.basename(estado["musica_fondo_path"])
        except Exception:
            default_music_label = "(sin musica)"
    lbl_music = ctk.CTkLabel(row_music, text=default_music_label, font=ctk.CTkFont(size=12))
    lbl_music.grid(row=0, column=1, sticky="w", padx=(8, 0))
    lbl_music_dur.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(2, 0))

    musica_vol_var = tk.DoubleVar(value=float(estado.get("musica_fondo_volumen", 0.25)) * 100.0)
    lbl_music_vol = ctk.CTkLabel(card, text="Volumen musica:", font=ctk.CTkFont(size=12))
    lbl_music_vol.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 4))
    lbl_music_vol_value = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=12))
    lbl_music_vol_value.grid(row=5, column=0, sticky="e", padx=16, pady=(0, 4))

    def actualizar_label_musica_vol(value=None):
        val = float(value if value is not None else musica_vol_var.get())
        lbl_music_vol_value.configure(text=f"{int(val)}%")
        estado["musica_fondo_volumen"] = val / 100.0

    slider_music_vol = ctk.CTkSlider(
        card,
        from_=0,
        to=100,
        number_of_steps=20,
        variable=musica_vol_var,
        command=lambda value: actualizar_label_musica_vol(value),
        width=220,
    )
    slider_music_vol.grid(row=6, column=0, sticky="w", padx=16, pady=(0, 12))
    actualizar_label_musica_vol()

    row_music_start = ctk.CTkFrame(card, fg_color="transparent")
    row_music_start.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 8))
    row_music_start.grid_columnconfigure(1, weight=1)
    lbl_music_start = ctk.CTkLabel(row_music_start, text="Inicio musica (mm:ss)", font=ctk.CTkFont(size=12))
    lbl_music_start.grid(row=0, column=0, sticky="w")
    entry_music_start = ctk.CTkEntry(row_music_start, width=120, placeholder_text="mm:ss")
    entry_music_start.insert(0, format_mmss(estado.get("musica_fondo_inicio", 0.0)))
    entry_music_start.grid(row=0, column=1, sticky="w", padx=(6, 0))
    slider_music_start = ctk.CTkSlider(row_music_start, from_=0, to=1, width=220)
    slider_music_start.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    row_music_end = ctk.CTkFrame(card, fg_color="transparent")
    row_music_end.grid(row=8, column=0, sticky="ew", padx=16, pady=(0, 8))
    row_music_end.grid_columnconfigure(1, weight=1)
    lbl_music_end = ctk.CTkLabel(row_music_end, text="Fin musica (mm:ss)", font=ctk.CTkFont(size=12))
    lbl_music_end.grid(row=0, column=0, sticky="w")
    entry_music_end = ctk.CTkEntry(row_music_end, width=120, placeholder_text="mm:ss")
    entry_music_end.insert(0, format_mmss(estado.get("musica_fondo_fin")))
    entry_music_end.grid(row=0, column=1, sticky="w", padx=(6, 0))
    slider_music_end = ctk.CTkSlider(row_music_end, from_=0, to=1, width=220)
    slider_music_end.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    row_music_video_start = ctk.CTkFrame(card, fg_color="transparent")
    row_music_video_start.grid(row=9, column=0, sticky="ew", padx=16, pady=(0, 12))
    row_music_video_start.grid_columnconfigure(1, weight=1)
    lbl_music_video_start = ctk.CTkLabel(row_music_video_start, text="Inicio en video (mm:ss)", font=ctk.CTkFont(size=12))
    lbl_music_video_start.grid(row=0, column=0, sticky="w")
    entry_music_video_start = ctk.CTkEntry(row_music_video_start, width=120, placeholder_text="mm:ss")
    entry_music_video_start.insert(0, format_mmss(estado.get("musica_fondo_inicio_video", 0.0)))
    entry_music_video_start.grid(row=0, column=1, sticky="w", padx=(6, 0))
    slider_video_start = ctk.CTkSlider(row_music_video_start, from_=0, to=1, width=220)
    slider_video_start.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

    hint_time = ctk.CTkLabel(
        card,
        text="Tip: puedes escribir mm:ss o segundos (ej: 12.5)",
        font=ctk.CTkFont(size=11),
        text_color="#9aa4b2",
    )
    hint_time.grid(row=10, column=0, sticky="w", padx=16, pady=(0, 8))

    btn_apply = ctk.CTkButton(
        card,
        text="Aplicar configuracion",
        command=aplicar_estado,
        height=38,
    )
    btn_apply.grid(row=11, column=0, sticky="ew", padx=16, pady=(0, 16))

    def aplicar_musica_video():
        if not estado.get("path"):
            _log("Selecciona un video primero.")
            return
        if not estado.get("musica_fondo_path"):
            _log("Selecciona una musica primero.")
            return
        aplicar_estado()
        video_path = estado["path"]
        base_dir = os.path.join(output_base_dir(video_path), "imagenes", "video con musica")
        os.makedirs(base_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        out_path = os.path.join(base_dir, f"{base_name}_musica.mp4")

        def run_apply():
            try:
                aplicar_musica_fondo(
                    video_path,
                    estado.get("musica_fondo_path"),
                    volumen=estado.get("musica_fondo_volumen", 0.25),
                    music_start=estado.get("musica_fondo_inicio", 0.0),
                    music_end=estado.get("musica_fondo_fin", None),
                    video_start=estado.get("musica_fondo_inicio_video", 0.0),
                    output_path=out_path,
                    log_fn=_log,
                )
                abs_out = os.path.abspath(out_path)
                if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    size_mb = os.path.getsize(out_path) / (1024 * 1024)
                    _log(f"Video con musica listo: {abs_out} ({size_mb:.1f} MB)")
                else:
                    _log(f"❌ No se creo el archivo de salida: {abs_out}")
            except Exception as exc:
                _log(f"Error aplicando musica: {exc}")

        threading.Thread(target=run_apply, daemon=True).start()

    btn_unir = ctk.CTkButton(
        card,
        text="Unir musica y video",
        command=aplicar_musica_video,
        height=40,
    )
    btn_unir.grid(row=12, column=0, sticky="ew", padx=16, pady=(0, 16))

    def abrir_carpeta_salida():
        base_dir = os.path.join(output_base_dir(estado.get("path", "")), "imagenes", "video con musica")
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)
        try:
            os.startfile(base_dir)
        except Exception:
            _log(f"Carpeta salida: {os.path.abspath(base_dir)}")

    btn_open = ctk.CTkButton(
        card,
        text="Abrir carpeta de salida",
        command=abrir_carpeta_salida,
        height=36,
    )
    btn_open.grid(row=13, column=0, sticky="ew", padx=16, pady=(0, 16))

    def sync_from_entries():
        try:
            v = parse_time_optional(entry_music_start.get()) or 0.0
            slider_music_start.set(v)
        except Exception:
            pass
        try:
            v = parse_time_optional(entry_music_end.get())
            if v is not None:
                slider_music_end.set(v)
        except Exception:
            pass
        try:
            v = parse_time_optional(entry_music_video_start.get()) or 0.0
            slider_video_start.set(v)
        except Exception:
            pass

    def sync_entry_from_slider(entry, value):
        entry.delete(0, "end")
        entry.insert(0, format_mmss(value))

    slider_music_start.configure(command=lambda v: sync_entry_from_slider(entry_music_start, v))
    slider_music_end.configure(command=lambda v: sync_entry_from_slider(entry_music_end, v))
    slider_video_start.configure(command=lambda v: sync_entry_from_slider(entry_music_video_start, v))

    entry_music_start.bind("<FocusOut>", lambda _e: sync_from_entries())
    entry_music_start.bind("<Return>", lambda _e: sync_from_entries())
    entry_music_end.bind("<FocusOut>", lambda _e: sync_from_entries())
    entry_music_end.bind("<Return>", lambda _e: sync_from_entries())
    entry_music_video_start.bind("<FocusOut>", lambda _e: sync_from_entries())
    entry_music_video_start.bind("<Return>", lambda _e: sync_from_entries())

    if estado.get("path"):
        try:
            durations["video"] = float(obtener_duracion_segundos(estado["path"]))
        except Exception:
            durations["video"] = 0.0
        if durations["video"] > 0:
            lbl_video_dur.configure(text=f"Duracion: {format_mmss(durations['video'])}")
            slider_video_start.configure(from_=0, to=durations["video"])
            slider_video_start.set(min(durations["video"], float(estado.get("musica_fondo_inicio_video", 0.0))))

    if estado.get("musica_fondo_path"):
        try:
            durations["music"] = float(obtener_duracion_segundos(estado["musica_fondo_path"]))
        except Exception:
            durations["music"] = 0.0
        if durations["music"] > 0:
            lbl_music_dur.configure(text=f"Duracion: {format_mmss(durations['music'])}")
            slider_music_start.configure(from_=0, to=durations["music"])
            slider_music_end.configure(from_=0, to=durations["music"])
            slider_music_start.set(min(durations["music"], float(estado.get("musica_fondo_inicio", 0.0))))
            end_val = estado.get("musica_fondo_fin")
            if end_val is None:
                slider_music_end.set(durations["music"])
            else:
                try:
                    slider_music_end.set(min(durations["music"], float(end_val)))
                except Exception:
                    slider_music_end.set(durations["music"])

    log_card, _log_widget, log_local = helpers.create_log_panel(
        container,
        title="Actividad",
        height=220,
        mirror_fn=context.get("log_global"),
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
    log_ref["fn"] = log_local

    return {}
