import threading
import customtkinter as ctk

from core.ai_tiktok import generar_descripcion_tiktok
from ui.shared import helpers


def create_tab(parent, context):
    ventana = context["ventana"]
    ai_state = context["ai_state"]
    log = context["log"]
    alerta_busy = context["alerta_busy"]
    stop_control = context["stop_control"]
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

    ai_scroll = ctk.CTkScrollableFrame(left, corner_radius=0)
    ai_scroll.grid(row=0, column=0, sticky="nsew")
    ai_scroll.grid_columnconfigure(0, weight=1)

    ai_card = ctk.CTkFrame(ai_scroll, corner_radius=12)
    ai_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    ai_card.grid_columnconfigure(0, weight=1)

    lbl_ai_title = ctk.CTkLabel(
        ai_card,
        text="IA TikTok: Resumen + Descripcion + Hashtags",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_ai_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_ai_hint = ctk.CTkLabel(
        ai_card,
        text="Sube un SRT y genera texto listo para copiar.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_ai_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    ai_select = ctk.CTkFrame(ai_card, fg_color="transparent")
    ai_select.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    ai_select.grid_columnconfigure(1, weight=1)

    def on_click_ai_srt():
        from ui.dialogs import seleccionar_archivo
        srt = seleccionar_archivo("Seleccionar SRT", [("Subtitles", "*.srt")])
        if srt:
            ai_state["srt"] = srt
            lbl_ai_srt.configure(text=srt)
            log(f"SRT seleccionado: {srt}")

    btn_ai_srt = ctk.CTkButton(
        ai_select,
        text="Seleccionar SRT",
        command=on_click_ai_srt,
        height=40,
    )
    btn_ai_srt.grid(row=0, column=0, sticky="w")

    lbl_ai_srt = ctk.CTkLabel(
        ai_select,
        text="(sin srt seleccionado)",
        font=ctk.CTkFont(size=12),
    )
    lbl_ai_srt.grid(row=0, column=1, sticky="w", padx=(12, 0))

    ai_conf = ctk.CTkFrame(ai_card, fg_color="transparent")
    ai_conf.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    ai_conf.grid_columnconfigure(1, weight=1)

    lbl_key = ctk.CTkLabel(ai_conf, text="API key (desde .env)", font=ctk.CTkFont(size=12))
    lbl_key.grid(row=0, column=0, sticky="w")

    lbl_key_hint = ctk.CTkLabel(
        ai_conf,
        text="Usa OPENAI_API_KEY en el archivo .env",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_key_hint.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_model_ai = ctk.CTkLabel(ai_conf, text="Modelo", font=ctk.CTkFont(size=12))
    lbl_model_ai.grid(row=1, column=0, sticky="w", pady=(8, 0))

    model_ai_var = ctk.StringVar(value="gpt-4o-mini")
    opt_model_ai = ctk.CTkOptionMenu(
        ai_conf,
        values=["gpt-4o-mini", "gpt-4o"],
        variable=model_ai_var,
    )
    opt_model_ai.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    def _set_textbox(tb, text):
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.insert("end", text)
        tb.configure(state="disabled")

    def _copy_text(text):
        ventana.clipboard_clear()
        ventana.clipboard_append(text)
        ventana.update_idletasks()

    out_frame = ctk.CTkFrame(ai_card)
    out_frame.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 12))
    out_frame.grid_columnconfigure(0, weight=1)

    lbl_title_ai = ctk.CTkLabel(out_frame, text="Titulo (clickbait)", font=ctk.CTkFont(size=12))
    lbl_title_ai.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
    txt_title_ai = ctk.CTkTextbox(out_frame, height=50)
    txt_title_ai.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

    lbl_res = ctk.CTkLabel(out_frame, text="Resumen", font=ctk.CTkFont(size=12))
    lbl_res.grid(row=2, column=0, sticky="w", padx=10, pady=(6, 4))
    txt_res = ctk.CTkTextbox(out_frame, height=80)
    txt_res.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 6))

    lbl_desc = ctk.CTkLabel(out_frame, text="Descripcion", font=ctk.CTkFont(size=12))
    lbl_desc.grid(row=4, column=0, sticky="w", padx=10, pady=(6, 4))
    txt_desc = ctk.CTkTextbox(out_frame, height=110)
    txt_desc.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 6))

    lbl_tags = ctk.CTkLabel(out_frame, text="Hashtags", font=ctk.CTkFont(size=12))
    lbl_tags.grid(row=6, column=0, sticky="w", padx=10, pady=(6, 4))
    txt_tags = ctk.CTkTextbox(out_frame, height=70)
    txt_tags.grid(row=7, column=0, sticky="ew", padx=10, pady=(0, 10))

    def iniciar_ai():
        if not ai_state["srt"]:
            log("Selecciona un SRT primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("IA TikTok")
        model = model_ai_var.get()

        def run_ai():
            try:
                result = generar_descripcion_tiktok(ai_state["srt"], None, model, log)
                _set_textbox(txt_title_ai, result.get("titulo", ""))
                _set_textbox(txt_res, result.get("resumen", ""))
                _set_textbox(txt_desc, result.get("descripcion", ""))
                _set_textbox(txt_tags, result.get("hashtags", ""))
                log("Finalizado proceso IA TikTok.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error IA TikTok: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_ai, daemon=True).start()

    btn_ai_run = ctk.CTkButton(
        ai_card,
        text="Generar texto",
        command=iniciar_ai,
        height=46,
    )
    btn_ai_run.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 8))

    btn_copy_desc = ctk.CTkButton(
        ai_card,
        text="Copiar descripcion + hashtags",
        command=lambda: _copy_text((txt_desc.get("1.0", "end").strip() + "\n" + txt_tags.get("1.0", "end").strip()).strip()),
        height=40,
    )
    btn_copy_desc.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 16))

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
        "scroll": ai_scroll,
    }
