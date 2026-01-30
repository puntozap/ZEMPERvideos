import os
import threading
import customtkinter as ctk

from core.workflow import procesar_srt
from core.utils import output_subdir
from ui.shared import helpers


def create_tab(parent, context):
    srt_state = context["srt_state"]
    log = context["log"]
    limpiar_entry = context["limpiar_entry"]
    alerta_busy = context["alerta_busy"]
    abrir_subtitulos = context["abrir_subtitulos"]
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

    srt_scroll = ctk.CTkScrollableFrame(left, corner_radius=0)
    srt_scroll.grid(row=0, column=0, sticky="nsew")
    srt_scroll.grid_columnconfigure(0, weight=1)

    srt_card = ctk.CTkFrame(srt_scroll, corner_radius=12)
    srt_card.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    srt_card.grid_columnconfigure(0, weight=1)

    lbl_srt_title = ctk.CTkLabel(
        srt_card,
        text="Generar subtitulos (.srt)",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_srt_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_srt_hint = ctk.CTkLabel(
        srt_card,
        text="Selecciona un video o audio y configura el modelo/idioma.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_srt_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    srt_select = ctk.CTkFrame(srt_card, fg_color="transparent")
    srt_select.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    srt_select.grid_columnconfigure(1, weight=1)

    def on_click_srt_video():
        from ui.dialogs import seleccionar_videos
        videos = seleccionar_videos()
        if videos:
            items = []
            for v in videos[:3]:
                v = renombrar_si_largo(v)
                if v:
                    items.append((v, False))
            if not items:
                return
            srt_state["items"] = items
            lbl_srt_file.configure(text=f"{len(items)} video(s) seleccionados")
            for v, _ in items:
                log(f"Video seleccionado: {v}")

    def on_click_srt_audio():
        from ui.dialogs import seleccionar_audios
        audios = seleccionar_audios()
        if audios:
            items = []
            for a in audios[:3]:
                a = renombrar_si_largo(a)
                if a:
                    items.append((a, True))
            if not items:
                return
            srt_state["items"] = items
            lbl_srt_file.configure(text=f"{len(items)} audio(s) seleccionados")
            for a, _ in items:
                log(f"Audio seleccionado: {a}")

    btn_srt_video = ctk.CTkButton(
        srt_select,
        text="Seleccionar Video",
        command=on_click_srt_video,
        height=40,
    )
    btn_srt_video.grid(row=0, column=0, sticky="w")

    btn_srt_audio = ctk.CTkButton(
        srt_select,
        text="Seleccionar Audio",
        command=on_click_srt_audio,
        height=40,
    )
    btn_srt_audio.grid(row=0, column=1, sticky="w", padx=(12, 0))

    lbl_srt_file = ctk.CTkLabel(
        srt_select,
        text="(sin archivo seleccionado)",
        font=ctk.CTkFont(size=12),
    )
    lbl_srt_file.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    srt_conf = ctk.CTkFrame(srt_card, fg_color="transparent")
    srt_conf.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
    srt_conf.grid_columnconfigure(1, weight=1)

    lbl_model = ctk.CTkLabel(srt_conf, text="Modelo", font=ctk.CTkFont(size=12))
    lbl_model.grid(row=0, column=0, sticky="w")

    model_var = ctk.StringVar(value="base")
    opt_model = ctk.CTkOptionMenu(
        srt_conf,
        values=["tiny", "base", "small", "medium", "large"],
        variable=model_var,
    )
    opt_model.grid(row=0, column=1, sticky="w", padx=(8, 0))

    lbl_idioma = ctk.CTkLabel(srt_conf, text="Idioma", font=ctk.CTkFont(size=12))
    lbl_idioma.grid(row=1, column=0, sticky="w", pady=(8, 0))

    idioma_var = ctk.StringVar(value="auto")
    opt_idioma = ctk.CTkOptionMenu(
        srt_conf,
        values=["auto", "es", "en", "pt", "fr"],
        variable=idioma_var,
    )
    opt_idioma.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    adv_var = ctk.BooleanVar(value=False)
    chk_adv = ctk.CTkCheckBox(
        srt_card,
        text="Opciones avanzadas",
        variable=adv_var,
    )
    chk_adv.grid(row=4, column=0, sticky="w", padx=16, pady=(0, 8))

    adv_card = ctk.CTkFrame(srt_card, fg_color="transparent")
    adv_card.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 12))
    adv_card.grid_columnconfigure(1, weight=1)

    lbl_temp = ctk.CTkLabel(adv_card, text="Temperature", font=ctk.CTkFont(size=12))
    lbl_temp.grid(row=0, column=0, sticky="w")

    entry_temp = ctk.CTkEntry(adv_card, width=80)
    entry_temp.insert(0, "0.0")
    entry_temp.grid(row=0, column=1, sticky="w", padx=(8, 0))

    btn_clear_temp = ctk.CTkButton(
        adv_card,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_temp),
    )
    btn_clear_temp.grid(row=0, column=2, sticky="e", padx=(8, 0))

    lbl_beam = ctk.CTkLabel(adv_card, text="Beam size", font=ctk.CTkFont(size=12))
    lbl_beam.grid(row=1, column=0, sticky="w", pady=(8, 0))

    entry_beam = ctk.CTkEntry(adv_card, width=80)
    entry_beam.insert(0, "5")
    entry_beam.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))

    btn_clear_beam = ctk.CTkButton(
        adv_card,
        text="Limpiar",
        width=80,
        height=28,
        command=lambda: limpiar_entry(entry_beam),
    )
    btn_clear_beam.grid(row=1, column=2, sticky="e", padx=(8, 0), pady=(8, 0))

    def _toggle_adv():
        adv_card.grid_remove() if not adv_var.get() else adv_card.grid()

    adv_var.trace_add("write", lambda *_: _toggle_adv())
    _toggle_adv()

    def iniciar_srt():
        if not srt_state["items"]:
            log("Selecciona videos o audio primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("SRT")
        idioma = idioma_var.get()
        if idioma == "auto":
            idioma = ""
        model = model_var.get()
        temperature = None
        beam_size = None
        if adv_var.get():
            try:
                temperature = float(entry_temp.get().strip().replace(",", "."))
            except Exception:
                temperature = None
            try:
                beam_size = int(entry_beam.get().strip())
            except Exception:
                beam_size = None

        def run_srt():
            try:
                for idx, (path, is_audio) in enumerate(srt_state["items"], start=1):
                    if stop_control.should_stop():
                        log("Proceso detenido por el usuario.")
                        return
                    log(f"Transcribiendo {idx}/{len(srt_state['items'])}...")
                    procesar_srt(
                        path,
                        is_audio,
                        idioma,
                        model,
                        temperature,
                        beam_size,
                        log,
                    )
                log("Finalizado proceso de SRT.")
                log("Fin de la automatizacion.")
                beep_fin()
            except Exception as e:
                log(f"Error en SRT: {e}")
            finally:
                stop_control.set_busy(False)

        threading.Thread(target=run_srt, daemon=True).start()

    btn_srt_run = ctk.CTkButton(
        srt_card,
        text="Generar SRT",
        command=iniciar_srt,
        height=46,
    )
    btn_srt_run.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 8))

    def abrir_carpeta_subs():
        if srt_state["items"]:
            first_path, _is_audio = srt_state["items"][0]
            folder = output_subdir(first_path, "subtitulos")
        else:
            folder = os.path.abspath("output")
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)

    btn_srt_open = ctk.CTkButton(
        srt_card,
        text="Abrir Carpeta de Subtitulos",
        command=abrir_carpeta_subs,
        height=40,
    )
    btn_srt_open.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 16))

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
        "scroll": srt_scroll,
    }
