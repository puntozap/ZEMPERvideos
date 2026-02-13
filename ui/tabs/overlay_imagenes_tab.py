import os
import threading
import customtkinter as ctk
import tkinter as tk

from core.utils import overlay_image_temporizada, append_image_outro, output_base_dir, obtener_duracion_segundos
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

    title = ctk.CTkLabel(card, text="Imagenes temporizadas", font=ctk.CTkFont(size=18, weight="bold"))
    title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    hint = ctk.CTkLabel(
        card,
        text="Agrega imagenes sobre el video en rangos de tiempo. El audio se mantiene.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    durations = {"video": 0.0}

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
                for item in overlays:
                    try:
                        item["slider_start"].configure(from_=0, to=durations["video"])
                        item["slider_end"].configure(from_=0, to=durations["video"])
                    except Exception:
                        pass
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

    overlays = []

    def add_overlay_row(image_path: str | None = None, start_val: float | None = None, end_val: float | None = None, zoom_val: float | None = None):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=4 + len(overlays), column=0, sticky="ew", padx=16, pady=(0, 8))
        row.grid_columnconfigure(1, weight=1)

        lbl_img = ctk.CTkLabel(row, text="(sin imagen)", font=ctk.CTkFont(size=12))

        def seleccionar_imagen():
            from ui.dialogs import seleccionar_imagen
            img = seleccionar_imagen()
            if img:
                lbl_img.configure(text=os.path.basename(img))
                item["image"] = img

        btn_img = ctk.CTkButton(row, text="Seleccionar imagen", command=seleccionar_imagen, height=28, width=150)
        btn_img.grid(row=0, column=0, sticky="w")
        lbl_img.grid(row=0, column=1, sticky="w", padx=(8, 0))

        row_times = ctk.CTkFrame(row, fg_color="transparent")
        row_times.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        lbl_start = ctk.CTkLabel(row_times, text="Inicio (mm:ss)", font=ctk.CTkFont(size=11))
        lbl_start.grid(row=0, column=0, sticky="w")
        entry_start = ctk.CTkEntry(row_times, width=110, placeholder_text="mm:ss")
        entry_start.insert(0, format_mmss(start_val))
        entry_start.grid(row=0, column=1, sticky="w", padx=(6, 12))
        slider_start = ctk.CTkSlider(row_times, from_=0, to=max(1.0, durations["video"]), width=220)
        slider_start.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))

        lbl_end = ctk.CTkLabel(row_times, text="Fin (mm:ss)", font=ctk.CTkFont(size=11))
        lbl_end.grid(row=0, column=2, sticky="w")
        entry_end = ctk.CTkEntry(row_times, width=110, placeholder_text="mm:ss")
        entry_end.insert(0, format_mmss(end_val))
        entry_end.grid(row=0, column=3, sticky="w", padx=(6, 0))
        slider_end = ctk.CTkSlider(row_times, from_=0, to=max(1.0, durations["video"]), width=220)
        slider_end.grid(row=1, column=2, columnspan=2, sticky="ew", pady=(6, 0))

        row_zoom = ctk.CTkFrame(row, fg_color="transparent")
        row_zoom.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        lbl_zoom = ctk.CTkLabel(row_zoom, text="Zoom imagen:", font=ctk.CTkFont(size=11))
        lbl_zoom.grid(row=0, column=0, sticky="w")
        lbl_zoom_val = ctk.CTkLabel(row_zoom, text="", font=ctk.CTkFont(size=11))
        lbl_zoom_val.grid(row=0, column=1, sticky="w", padx=(8, 0))
        slider_zoom = ctk.CTkSlider(row_zoom, from_=0.2, to=2.0, number_of_steps=18, width=220)
        slider_zoom.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        def remove_row():
            try:
                row.destroy()
            except Exception:
                pass
            overlays.remove(item)
            relayout_rows()

        btn_remove = ctk.CTkButton(row, text="Eliminar", command=remove_row, height=28, width=90)
        btn_remove.grid(row=0, column=2, sticky="e", padx=(8, 0))

        item = {
            "frame": row,
            "image": image_path,
            "start": entry_start,
            "end": entry_end,
            "label": lbl_img,
            "slider_start": slider_start,
            "slider_end": slider_end,
            "slider_zoom": slider_zoom,
        }
        if durations["video"] > 0:
            slider_start.configure(from_=0, to=durations["video"])
            slider_end.configure(from_=0, to=durations["video"])
        if start_val is not None:
            slider_start.set(float(start_val))
        if end_val is not None:
            slider_end.set(float(end_val))
        if image_path:
            lbl_img.configure(text=os.path.basename(image_path))
        overlays.append(item)

        def update_zoom_label(value=None):
            val = float(value if value is not None else slider_zoom.get())
            lbl_zoom_val.configure(text=f"{val:.2f}x")

        def sync_entry_from_slider(entry, value):
            entry.delete(0, "end")
            entry.insert(0, format_mmss(value))

        slider_start.configure(command=lambda v: sync_entry_from_slider(entry_start, v))
        slider_end.configure(command=lambda v: sync_entry_from_slider(entry_end, v))
        slider_zoom.configure(command=lambda v: update_zoom_label(v))

        def sync_from_entries():
            try:
                v = parse_time_optional(entry_start.get()) or 0.0
                slider_start.set(v)
            except Exception:
                pass
            try:
                v = parse_time_optional(entry_end.get())
                if v is not None:
                    slider_end.set(v)
            except Exception:
                pass

        entry_start.bind("<FocusOut>", lambda _e: sync_from_entries())
        entry_start.bind("<Return>", lambda _e: sync_from_entries())
        entry_end.bind("<FocusOut>", lambda _e: sync_from_entries())
        entry_end.bind("<Return>", lambda _e: sync_from_entries())

        if zoom_val is None:
            zoom_val = 1.0
        slider_zoom.set(float(zoom_val))
        update_zoom_label()

    def relayout_rows():
        for idx, item in enumerate(overlays):
            try:
                item["frame"].grid_configure(row=4 + idx)
            except Exception:
                pass

    btn_add = ctk.CTkButton(
        card,
        text="Agregar imagen",
        command=lambda: add_overlay_row(),
        height=34,
    )
    btn_add.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 8))

    outro_card = ctk.CTkFrame(card, fg_color="transparent")
    outro_card.grid(row=1000, column=0, sticky="ew", padx=16, pady=(6, 8))
    outro_card.grid_columnconfigure(1, weight=1)

    outro_var = ctk.BooleanVar(value=False)
    chk_outro = ctk.CTkCheckBox(
        outro_card,
        text="Agregar imagen final al terminar el video",
        variable=outro_var,
    )
    chk_outro.grid(row=0, column=0, sticky="w", columnspan=2)

    outro_state = {"image": None}

    def seleccionar_outro():
        from ui.dialogs import seleccionar_imagen
        img = seleccionar_imagen()
        if img:
            outro_state["image"] = img
            lbl_outro.configure(text=os.path.basename(img))

    btn_outro = ctk.CTkButton(outro_card, text="Seleccionar imagen", command=seleccionar_outro, height=28, width=150)
    btn_outro.grid(row=1, column=0, sticky="w", pady=(6, 0))
    lbl_outro = ctk.CTkLabel(outro_card, text="(sin imagen)", font=ctk.CTkFont(size=12))
    lbl_outro.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

    lbl_outro_dur = ctk.CTkLabel(outro_card, text="Duracion (mm:ss)", font=ctk.CTkFont(size=11))
    lbl_outro_dur.grid(row=2, column=0, sticky="w", pady=(6, 0))
    entry_outro_dur = ctk.CTkEntry(outro_card, width=110, placeholder_text="mm:ss")
    entry_outro_dur.insert(0, "00:03")
    entry_outro_dur.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(6, 0))

    hint_time = ctk.CTkLabel(
        card,
        text="Tip: puedes escribir mm:ss o segundos (ej: 12.5)",
        font=ctk.CTkFont(size=11),
        text_color="#9aa4b2",
    )
    hint_time.grid(row=1001, column=0, sticky="w", padx=16, pady=(6, 8))

    def aplicar_overlays():
        if not estado.get("path"):
            _log("Selecciona un video primero.")
            return
            if not overlays and not outro_var.get():
                _log("Agrega al menos una imagen o activa la imagen final.")
                return

            items = []
            if overlays:
                for item in overlays:
                    img = item.get("image")
                    if not img or not os.path.exists(img):
                        _log("Hay una imagen sin seleccionar.")
                        return
                    try:
                        start = parse_time_optional(item["start"].get()) or 0.0
                    except Exception as exc:
                        _log(f"Inicio invalido: {exc}")
                        return
                    try:
                        end = parse_time_optional(item["end"].get())
                    except Exception as exc:
                        _log(f"Fin invalido: {exc}")
                        return
                    if end is None or end <= start:
                        _log("El fin debe ser mayor que el inicio.")
                        return
                    try:
                        zoom = float(item["slider_zoom"].get())
                    except Exception:
                        zoom = 1.0
                    items.append((img, start, end, zoom))

            outro_img = None
            outro_dur = 0.0
            if outro_var.get():
                outro_img = outro_state.get("image")
                if not outro_img or not os.path.exists(outro_img):
                    _log("Selecciona una imagen final.")
                    return
                try:
                    outro_dur = float(parse_time_optional(entry_outro_dur.get()) or 0.0)
                except Exception as exc:
                    _log(f"Duracion final invalida: {exc}")
                    return
                if outro_dur <= 0:
                    _log("La duracion final debe ser mayor a 0.")
                    return

        video_path = estado["path"]
        base_dir = os.path.join(output_base_dir(video_path), "imagenes")
        os.makedirs(base_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        out_path = os.path.join(base_dir, f"{base_name}_imagenes.mp4")

        def run_apply():
                try:
                    current = video_path
                    for idx, (img, start, end, zoom) in enumerate(items, start=1):
                        temp_out = out_path if (idx == len(items) and not outro_var.get()) else os.path.join(base_dir, f"{base_name}_tmp_{idx:02d}.mp4")
                        overlay_image_temporizada(
                            current,
                            img,
                            temp_out,
                            start_sec=start,
                            duration=end - start,
                            zoom=zoom,
                            log_fn=_log,
                        )
                        if current != video_path:
                            try:
                                os.remove(current)
                            except Exception:
                                pass
                        current = temp_out
                    if outro_var.get():
                        append_image_outro(
                            current,
                            outro_img,
                            out_path,
                            duration=outro_dur,
                            log_fn=_log,
                        )
                        if current != video_path and current != out_path:
                            try:
                                os.remove(current)
                            except Exception:
                                pass
                    _log(f"Video con imagenes listo: {out_path}")
                except Exception as exc:
                    _log(f"Error aplicando imagenes: {exc}")

        threading.Thread(target=run_apply, daemon=True).start()

    btn_apply = ctk.CTkButton(card, text="Aplicar imagenes", command=aplicar_overlays, height=40)
    btn_apply.grid(row=1002, column=0, sticky="ew", padx=16, pady=(0, 16))

    log_card, _log_widget, log_local = helpers.create_log_panel(
        container,
        title="Actividad",
        height=220,
        mirror_fn=context.get("log_global"),
    )
    log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
    log_ref["fn"] = log_local

    return {}
