import threading
import customtkinter as ctk

from core.ai_tiktok import generar_recomendaciones_clips
from ui.shared import helpers


def create_tab(parent, context):
    log = context["log"]
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

    clips_scroll = ctk.CTkScrollableFrame(left, corner_radius=0)
    clips_scroll.grid(row=0, column=0, sticky="nsew")
    clips_scroll.grid_columnconfigure(0, weight=1)

    clips_card = ctk.CTkFrame(clips_scroll, corner_radius=12)
    clips_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    clips_card.grid_columnconfigure(0, weight=1)

    lbl_clips_title = ctk.CTkLabel(
        clips_card,
        text="IA Clips: recomendaciones",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_clips_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_clips_hint = ctk.CTkLabel(
        clips_card,
        text="Sube un SRT y genera cortes recomendados.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_clips_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    clips_state = {"srt": None}

    clips_select = ctk.CTkFrame(clips_card, fg_color="transparent")
    clips_select.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    clips_select.grid_columnconfigure(1, weight=1)

    def on_click_clips_srt():
        from ui.dialogs import seleccionar_archivo
        srt = seleccionar_archivo("Seleccionar SRT", [("Subtitles", "*.srt")])
        if srt:
            srt = renombrar_si_largo(srt)
            if not srt:
                return
            clips_state["srt"] = srt
            lbl_clips_srt.configure(text=srt)
            log(f"SRT seleccionado: {srt}")

    btn_clips_srt = ctk.CTkButton(
        clips_select,
        text="Seleccionar SRT",
        command=on_click_clips_srt,
        height=40,
    )
    btn_clips_srt.grid(row=0, column=0, sticky="w")

    lbl_clips_srt = ctk.CTkLabel(
        clips_select,
        text="(sin srt seleccionado)",
        font=ctk.CTkFont(size=12),
    )
    lbl_clips_srt.grid(row=0, column=1, sticky="w", padx=(12, 0))

    clips_conf = ctk.CTkFrame(clips_card, fg_color="transparent")
    clips_conf.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    clips_conf.grid_columnconfigure(1, weight=1)

    lbl_model_clips = ctk.CTkLabel(clips_conf, text="Modelo", font=ctk.CTkFont(size=12))
    lbl_model_clips.grid(row=0, column=0, sticky="w")

    model_clips_var = ctk.StringVar(value="gpt-4o-mini")
    opt_model_clips = ctk.CTkOptionMenu(
        clips_conf,
        values=["gpt-4o-mini", "gpt-4o"],
        variable=model_clips_var,
    )
    opt_model_clips.grid(row=0, column=1, sticky="w", padx=(8, 0))

    clips_out = ctk.CTkFrame(clips_card)
    clips_out.grid(row=4, column=0, sticky="nsew", padx=16, pady=(0, 12))
    clips_out.grid_columnconfigure(0, weight=1)

    lbl_clips_out = ctk.CTkLabel(clips_out, text="Resultado", font=ctk.CTkFont(size=12))
    lbl_clips_out.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))

    txt_clips = ctk.CTkTextbox(clips_out, height=220)
    txt_clips.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
    txt_clips.configure(state="disabled")

    lbl_json = ctk.CTkLabel(clips_card, text="JSON: (sin generar)", font=ctk.CTkFont(size=12))
    lbl_json.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 8))

    def iniciar_ai_clips():
        if not clips_state["srt"]:
            log("Selecciona un SRT primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("IA Clips")
        model = model_clips_var.get()

        def run_clips():
            try:
                result = generar_recomendaciones_clips(clips_state["srt"], None, model, log)
                data = result.get("data", {})
                json_path = result.get("json_path", "")
                text_out = result.get("text", "")
                txt_clips.configure(state="normal")
                txt_clips.delete("1.0", "end")
                txt_clips.insert("end", text_out.strip())
                txt_clips.configure(state="disabled")
                if json_path:
                    lbl_json.configure(text=f"JSON creado: {json_path}")
                    log(f"JSON creado: {json_path}")
                if data:
                    pass
                log("Finalizado proceso IA Clips.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error IA Clips: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_clips, daemon=True).start()

    btn_clips_run = ctk.CTkButton(
        clips_card,
        text="Generar recomendaciones",
        command=iniciar_ai_clips,
        height=46,
    )
    btn_clips_run.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 16))

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
        "scroll": clips_scroll,
    }
