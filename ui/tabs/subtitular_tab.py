import os
import re
import threading
import unicodedata
import customtkinter as ctk

from core.workflow import procesar_quemar_srt
from ui.shared.preview import create_subtitle_preview
from ui.shared import helpers


def create_tab(parent, context):
    sub_state = context["sub_state"]
    log = context["log"]
    limpiar_entry = context["limpiar_entry"]
    alerta_busy = context["alerta_busy"]
    stop_control = context["stop_control"]
    beep_fin = context["beep_fin"]
    renombrar_si_largo = context["renombrar_si_largo"]

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

    sub_scroll = ctk.CTkScrollableFrame(left, corner_radius=0)
    sub_scroll.grid(row=0, column=0, sticky="nsew")
    sub_scroll.grid_columnconfigure(0, weight=1)

    sub_card = ctk.CTkFrame(sub_scroll, corner_radius=12)
    sub_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    sub_card.grid_columnconfigure(0, weight=2)
    sub_card.grid_columnconfigure(1, weight=0)

    lbl_sub_title = ctk.CTkLabel(
        sub_card,
        text="Quemar SRT en video (TikTok listo)",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_sub_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_sub_hint = ctk.CTkLabel(
        sub_card,
        text="Selecciona el video vertical y el archivo .srt para quemar los subtitulos.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_sub_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    sub_left = ctk.CTkFrame(sub_card, fg_color="transparent")
    sub_left.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
    sub_left.grid_columnconfigure(1, weight=1)

    sub_select = ctk.CTkFrame(sub_left, fg_color="transparent")
    sub_select.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    sub_select.grid_columnconfigure(1, weight=1)

    pos_row = ctk.CTkFrame(sub_left, fg_color="transparent")
    pos_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
    pos_row.grid_columnconfigure(1, weight=1)

    lbl_pos_sub = ctk.CTkLabel(pos_row, text="Posicion de subtitulo", font=ctk.CTkFont(size=12))
    lbl_pos_sub.grid(row=0, column=0, sticky="w")

    pos_sub_var = ctk.StringVar(value="bottom")
    opt_pos_sub = ctk.CTkOptionMenu(
        pos_row,
        values=["top", "top-center", "center", "bottom-center", "bottom"],
        variable=pos_sub_var,
    )
    opt_pos_sub.grid(row=0, column=1, sticky="w", padx=(8, 0))

    preview_card = ctk.CTkFrame(sub_card, corner_radius=10)
    preview_card.grid(row=0, column=1, rowspan=5, sticky="n", padx=(0, 16), pady=16)
    preview_card.grid_columnconfigure(0, weight=1)
    preview_card.grid_rowconfigure(1, weight=1)

    def get_preview_font_lines():
        try:
            font_size = int(entry_font.get().strip())
        except Exception:
            font_size = 46
        try:
            max_lines = int(entry_max_lines.get().strip())
        except Exception:
            max_lines = 2
        if font_size < 10:
            font_size = 10
        if max_lines < 1:
            max_lines = 1
        return font_size, max_lines

    preview_parts = create_subtitle_preview(
        preview_card,
        pos_sub_var,
        get_preview_font_lines,
        lambda: sub_state.get("video"),
    )
    actualizar_preview_sub = preview_parts["update"]

    def on_click_sub_video():
        from ui.dialogs import seleccionar_videos
        videos = seleccionar_videos()
        if videos:
            items = []
            for v in videos:
                v = renombrar_si_largo(v)
                if v:
                    items.append(v)
            if not items:
                return
            sub_state["videos"] = items
            if len(items) == 1:
                lbl_sub_video.configure(text=os.path.basename(items[0]))
                actualizar_preview_sub()
            else:
                lbl_sub_video.configure(text=f"{len(items)} video(s) seleccionados")
            for v in items:
                log(f"Video seleccionado: {v}")

    def on_click_sub_srt():
        from ui.dialogs import seleccionar_archivos
        srts = seleccionar_archivos("Seleccionar SRT", [("Subtitles", "*.srt")])
        if srts:
            items = []
            for s in srts:
                s = renombrar_si_largo(s)
                if s:
                    items.append(s)
            if not items:
                return
            sub_state["srts"] = items
            if len(items) == 1:
                lbl_sub_srt.configure(text=os.path.basename(items[0]))
            else:
                lbl_sub_srt.configure(text=f"{len(items)} srt(s) seleccionados")
            for s in items:
                log(f"SRT seleccionado: {s}")

    btn_sub_video = ctk.CTkButton(
        sub_select,
        text="Seleccionar Video",
        command=on_click_sub_video,
        height=40,
    )
    btn_sub_video.grid(row=0, column=0, sticky="w")

    btn_sub_srt = ctk.CTkButton(
        sub_select,
        text="Seleccionar SRT",
        command=on_click_sub_srt,
        height=40,
    )
    btn_sub_srt.grid(row=0, column=1, sticky="w", padx=(12, 0))

    lbl_sub_video = ctk.CTkLabel(
        sub_select,
        text="(sin video seleccionado)",
        font=ctk.CTkFont(size=12),
    )
    lbl_sub_video.grid(row=1, column=0, sticky="w", pady=(8, 0))

    lbl_sub_srt = ctk.CTkLabel(
        sub_select,
        text="(sin srt seleccionado)",
        font=ctk.CTkFont(size=12),
    )
    lbl_sub_srt.grid(row=1, column=1, sticky="w", padx=(12, 0), pady=(8, 0))

    txt_style_row = ctk.CTkFrame(sub_left, fg_color="transparent")
    txt_style_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
    txt_style_row.grid_columnconfigure(1, weight=1)

    lbl_font = ctk.CTkLabel(txt_style_row, text="Tamano de texto", font=ctk.CTkFont(size=12))
    lbl_font.grid(row=0, column=0, sticky="w")

    entry_font = ctk.CTkEntry(txt_style_row, width=80)
    entry_font.insert(0, "46")
    entry_font.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_outline = ctk.CTkLabel(txt_style_row, text="Borde", font=ctk.CTkFont(size=12))
    lbl_outline.grid(row=1, column=0, sticky="w", pady=(8, 0))

    entry_outline = ctk.CTkEntry(txt_style_row, width=80)
    entry_outline.insert(0, "2")
    entry_outline.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    lbl_shadow = ctk.CTkLabel(txt_style_row, text="Sombra", font=ctk.CTkFont(size=12))
    lbl_shadow.grid(row=2, column=0, sticky="w", pady=(8, 0))

    entry_shadow = ctk.CTkEntry(txt_style_row, width=80)
    entry_shadow.insert(0, "1")
    entry_shadow.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    wrap_row = ctk.CTkFrame(sub_left, fg_color="transparent")
    wrap_row.grid(row=3, column=0, sticky="ew", pady=(0, 12))
    wrap_row.grid_columnconfigure(1, weight=1)

    lbl_max_chars = ctk.CTkLabel(wrap_row, text="Max caracteres por linea", font=ctk.CTkFont(size=12))
    lbl_max_chars.grid(row=0, column=0, sticky="w")

    entry_max_chars = ctk.CTkEntry(wrap_row, width=80)
    entry_max_chars.insert(0, "32")
    entry_max_chars.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_max_lines = ctk.CTkLabel(wrap_row, text="Max lineas", font=ctk.CTkFont(size=12))
    lbl_max_lines.grid(row=1, column=0, sticky="w", pady=(8, 0))

    entry_max_lines = ctk.CTkEntry(wrap_row, width=80)
    entry_max_lines.insert(0, "2")
    entry_max_lines.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    entry_font.bind("<KeyRelease>", lambda _e: actualizar_preview_sub())
    entry_max_lines.bind("<KeyRelease>", lambda _e: actualizar_preview_sub())

    force_pos_var = ctk.BooleanVar(value=True)
    chk_force_pos = ctk.CTkCheckBox(
        sub_left,
        text="Forzar posicion del SRT",
        variable=force_pos_var,
    )
    chk_force_pos.grid(row=4, column=0, sticky="w", pady=(0, 12))

    use_ass_var = ctk.BooleanVar(value=True)
    chk_use_ass = ctk.CTkCheckBox(
        sub_left,
        text="Usar ASS (mas estable)",
        variable=use_ass_var,
    )
    chk_use_ass.grid(row=5, column=0, sticky="w", pady=(0, 12))

    def iniciar_subtitulado():
        if not sub_state["videos"] or not sub_state["srts"]:
            log("Selecciona video(s) y SRT(s) primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Subtitular video")
        pos = "center"
        pos_sub_var.set("center")
        try:
            font_size = int(entry_font.get().strip())
        except Exception:
            font_size = 46
        try:
            outline = int(entry_outline.get().strip())
        except Exception:
            outline = 2
        try:
            shadow = int(entry_shadow.get().strip())
        except Exception:
            shadow = 1
        try:
            max_chars = int(entry_max_chars.get().strip())
        except Exception:
            max_chars = 32
        try:
            max_lines = int(entry_max_lines.get().strip())
        except Exception:
            max_lines = 2
        if font_size < 10:
            font_size = 10
        if outline < 0:
            outline = 0
        if shadow < 0:
            shadow = 0

        def _norm_name(path: str) -> str:
            base = os.path.splitext(os.path.basename(path))[0].lower()
            base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
            base = re.sub(r"[^a-z0-9]+", " ", base).strip()
            tokens = base.split()
            strip_tokens = {
                "original",
                "completo",
                "srt",
                "source",
                "subt",
                "sub",
                "tmp",
                "vertical",
            }
            while tokens and tokens[-1] in strip_tokens:
                tokens.pop()
            return " ".join(tokens)

        def run_sub():
            try:
                videos = sub_state["videos"]
                srts = sub_state["srts"]
                if len(videos) == 1 and len(srts) == 1:
                    procesar_quemar_srt(
                        videos[0],
                        srts[0],
                        pos,
                        font_size,
                        outline,
                        shadow,
                        True,
                        max_chars,
                        max_lines,
                        use_ass_var.get(),
                        log,
                    )
                else:
                    srt_map = {}
                    for s in srts:
                        srt_map[_norm_name(s)] = s
                    for idx, v in enumerate(videos, start=1):
                        if stop_control.should_stop():
                            log("Proceso detenido por el usuario.")
                            return
                        key = _norm_name(v)
                        srt_match = srt_map.get(key)
                        if not srt_match:
                            log(f"No se encontro SRT para: {os.path.basename(v)}")
                            continue
                        log(f"Subtitulando {idx}/{len(videos)}: {os.path.basename(v)}")
                        procesar_quemar_srt(
                            v,
                            srt_match,
                            pos,
                            font_size,
                            outline,
                            shadow,
                            True,
                            max_chars,
                            max_lines,
                            use_ass_var.get(),
                            log,
                        )
                log("Finalizado proceso de subtitular video.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error subtitulando: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_sub, daemon=True).start()

    btn_sub_run = ctk.CTkButton(
        sub_left,
        text="Subtitular video",
        command=iniciar_subtitulado,
        height=46,
    )
    btn_sub_run.grid(row=6, column=0, sticky="ew", pady=(0, 8))

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
        "scroll": sub_scroll,
    }
