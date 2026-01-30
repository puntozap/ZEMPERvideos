import os
import threading
import customtkinter as ctk

from core.extractor import extraer_audio
from core.utils import output_base_dir, nombre_base_principal, output_subdir
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
    container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)
    container.grid_rowconfigure(0, weight=1)

    audio_card = ctk.CTkFrame(container, corner_radius=12)
    audio_card.grid(row=0, column=0, sticky="nsew")
    audio_card.grid_columnconfigure(0, weight=1)

    lbl_audio_title = ctk.CTkLabel(
        audio_card,
        text="Extraer audio en MP3",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_audio_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_audio_hint = ctk.CTkLabel(
        audio_card,
        text="Selecciona un video local y guarda el MP3 sin generar WAV.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_audio_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    audio_state = {"video_path": None}

    audio_select_row = ctk.CTkFrame(audio_card, fg_color="transparent")
    audio_select_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    audio_select_row.grid_columnconfigure(1, weight=1)

    def on_click_audio_video():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            video = renombrar_si_largo(video)
            if not video:
                return
            audio_state["video_path"] = video
            lbl_audio_file.configure(text=os.path.basename(video))
            log(f"Video seleccionado para MP3: {video}")

    btn_audio_video = ctk.CTkButton(
        audio_select_row,
        text="Seleccionar Video",
        command=on_click_audio_video,
        height=40,
    )
    btn_audio_video.grid(row=0, column=0, sticky="w")

    lbl_audio_file = ctk.CTkLabel(
        audio_select_row,
        text="(ningun video seleccionado)",
        font=ctk.CTkFont(size=12),
    )
    lbl_audio_file.grid(row=0, column=1, sticky="w", padx=(12, 0))

    def extraer_audio_mp3():
        video_path = audio_state.get("video_path")
        if not video_path:
            log("Selecciona un video para extraer el audio.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("Audio MP3")
        base_name = nombre_base_principal(video_path)
        audio_dir_base = os.path.join(output_base_dir(video_path), "audios")
        os.makedirs(audio_dir_base, exist_ok=True)
        out_path = os.path.join(audio_dir_base, f"{base_name}_original.mp3")
        log("Extrayendo audio en MP3...")
        try:
            extraer_audio(video_path, out_path, log)
            log(f"OK Audio MP3 guardado: {out_path}")
            log("Finalizado proceso de audio MP3.")
            log("Fin de la automatizacion.")
            beep_fin()
        except Exception as e:
            log(f"Error extrayendo MP3: {e}")
        finally:
            stop_control.set_busy(False)

    def iniciar_audio_mp3():
        threading.Thread(target=extraer_audio_mp3, daemon=True).start()

    btn_audio_extraer = ctk.CTkButton(
        audio_card,
        text="Extraer MP3",
        command=iniciar_audio_mp3,
        height=46,
    )
    btn_audio_extraer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

    def abrir_carpeta_audios():
        video_path = audio_state.get("video_path")
        if video_path:
            folder = output_subdir(video_path, "audios")
        else:
            folder = os.path.abspath("output")
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)

    btn_audio_open = ctk.CTkButton(
        audio_card,
        text="Abrir Carpeta de Audios",
        command=abrir_carpeta_audios,
        height=40,
    )
    btn_audio_open.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))

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

    return {}
