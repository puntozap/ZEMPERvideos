import threading
import customtkinter as ctk

from core.youtube_downloader import descargar_video_youtube_mp4
from ui.shared import helpers


def create_tab(parent, context):
    log = context["log"]
    limpiar_entry = context["limpiar_entry"]
    alerta_busy = context["alerta_busy"]
    stop_control = context["stop_control"]
    beep_fin = context["beep_fin"]
    abrir_descargas = context["abrir_descargas"]

    parent.grid_columnconfigure(0, weight=1)
    parent.grid_rowconfigure(0, weight=1)

    container = ctk.CTkFrame(parent, fg_color="transparent")
    container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    container.grid_columnconfigure(0, weight=1)
    container.grid_columnconfigure(1, weight=0)
    container.grid_rowconfigure(0, weight=1)

    yt_mp4_card = ctk.CTkFrame(container, corner_radius=12)
    yt_mp4_card.grid(row=0, column=0, sticky="nsew")
    yt_mp4_card.grid_columnconfigure(0, weight=1)

    lbl_yt_mp4_title = ctk.CTkLabel(
        yt_mp4_card,
        text="Descargar video de YouTube (MP4)",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    lbl_yt_mp4_title.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

    lbl_yt_mp4_hint = ctk.CTkLabel(
        yt_mp4_card,
        text="Pega el link y descarga el video en MP4.",
        font=ctk.CTkFont(size=12),
        text_color="#9aa4b2",
    )
    lbl_yt_mp4_hint.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 12))

    yt_mp4_row = ctk.CTkFrame(yt_mp4_card, fg_color="transparent")
    yt_mp4_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
    yt_mp4_row.grid_columnconfigure(0, weight=1)

    yt_mp4_entry = ctk.CTkEntry(yt_mp4_row, placeholder_text="https://www.youtube.com/watch?v=...")
    yt_mp4_entry.grid(row=0, column=0, sticky="ew")

    btn_clear_yt_mp4 = ctk.CTkButton(
        yt_mp4_row,
        text="Limpiar",
        width=90,
        height=28,
        command=lambda: limpiar_entry(yt_mp4_entry),
    )
    btn_clear_yt_mp4.grid(row=0, column=1, sticky="e", padx=(8, 0))

    def descargar_mp4_youtube():
        url = yt_mp4_entry.get().strip()
        if not url:
            log("Pega un link de YouTube primero.")
            return
        if stop_control.is_busy():
            alerta_busy()
            return
        stop_control.clear_stop()
        stop_control.set_busy(True)
        log_seccion("YouTube MP4")
        log("Descargando video de YouTube...")
        try:
            out_path = descargar_video_youtube_mp4(url, log_fn=log)
            log(f"OK Video MP4 guardado: {out_path}")
            log("Finalizado proceso de YouTube MP4.")
            log("Fin de la automatizacion.")
            beep_fin()
        except Exception as e:
            log(f"Error descargando MP4 de YouTube: {e}")
        finally:
            stop_control.set_busy(False)

    def iniciar_descarga_youtube_mp4():
        threading.Thread(target=descargar_mp4_youtube, daemon=True).start()

    btn_yt_mp4 = ctk.CTkButton(
        yt_mp4_card,
        text="Descargar MP4",
        command=iniciar_descarga_youtube_mp4,
        height=46,
    )
    btn_yt_mp4.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 8))

    btn_yt_mp4_open = ctk.CTkButton(
        yt_mp4_card,
        text="Abrir Descargas YouTube",
        command=abrir_descargas,
        height=40,
    )
    btn_yt_mp4_open.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 16))

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
