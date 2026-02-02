import os
import customtkinter as ctk
import winsound
from ui.shared import helpers
from ui.shared.state import create_state
from ui.shared.preview import create_subtitle_preview
from core.workflow import generar_visualizador_solo
from ui.tabs import (
    corte_tab,
    corte_individual_tab,
    corte_visualizer_tab,
    pegar_visualizador_tab,
    cortar_visualizador_tab,
    srt_tab,
    subtitular_tab,
    ia_clips_tab,
    ia_tiktok_tab,
    audio_tab,
    youtube_mp3_tab,
    youtube_mp4_tab,
    youtube_upload_tab,
    actividad_tab,
)


def iniciar_app(procesar_video_fn):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    ventana = ctk.CTk()
    ventana.title("Transcriptor de Video")
    ventana.geometry("980x680")
    ventana.minsize(820, 600)

    root = ctk.CTkFrame(master=ventana, corner_radius=14)
    root.pack(fill="both", expand=True, padx=24, pady=24)
    root.grid_columnconfigure(0, weight=1)
    root.grid_rowconfigure(1, weight=1)

    shared_state = create_state()
    log_state = {"widget": None}
    estado = shared_state["estado"]
    rango = shared_state["rango"]
    rango_ind = shared_state["rango_ind"]
    srt_state = shared_state["srt_state"]
    sub_state = shared_state["sub_state"]
    ai_state = shared_state["ai_state"]
    youtube_state = shared_state["youtube_state"]
    stop_control = shared_state["stop_control"]

    def log(msg):
        helpers.log_to_widget(log_state["widget"], msg)

    def beep_fin():
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

    def alerta_busy():
        helpers.alerta_busy(ventana)

    def renombrar_si_largo(path: str):
        return helpers.renombrar_si_largo(path, log)

    def log_seccion(titulo):
        helpers.log_seccion(log, tabs, titulo)

    def limpiar_entry(entry):
        helpers.limpiar_entry(entry)

    abrir_transcripciones = helpers.abrir_transcripciones
    abrir_subtitulos = helpers.abrir_subtitulos
    abrir_videos = helpers.abrir_videos
    abrir_audios = helpers.abrir_audios
    abrir_descargas = helpers.abrir_descargas

    def eliminar_audios(log_fn=None):
        output_root = os.path.abspath("output")
        if not os.path.exists(output_root):
            return
        count = 0
        for root_dir, _dirs, files in os.walk(output_root):
            if os.path.basename(root_dir).lower() != "audios":
                continue
            for f in files:
                if f.lower().endswith((".mp3", ".wav", ".webm", ".mp4")):
                    try:
                        os.remove(os.path.join(root_dir, f))
                        count += 1
                    except Exception as e:
                        if log_fn:
                            log_fn(f"No se pudo borrar {f}: {e}")
        if log_fn:
            log_fn(f"{count} audios eliminados de output/")

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
    header.grid_columnconfigure(0, weight=1)

    title = ctk.CTkLabel(
        header,
        text="Transcriptor de Video",
        font=ctk.CTkFont(size=26, weight="bold")
    )
    title.grid(row=0, column=0, sticky="w")

    subtitle = ctk.CTkLabel(
        header,
        text="Divide por minutos y marca el rango con sliders.",
        font=ctk.CTkFont(size=13)
    )
    subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

    tabs = ctk.CTkTabview(root, corner_radius=12)
    tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=(6, 10))
    tabs.add("Corte")
    tabs.add("Cortar visualizador")
    tabs.add("Subtitulos")
    tabs.add("IA generadores")
    tabs.add("Descargas")
    tabs.add("YouTube")
    tabs.add("Actividad")

    tab_corte_main = tabs.tab("Corte")
    tab_cortar_visual = tabs.tab("Cortar visualizador")
    tab_sub_main = tabs.tab("Subtitulos")
    tab_ia_main = tabs.tab("IA generadores")
    tab_desc_main = tabs.tab("Descargas")
    tab_youtube_main = tabs.tab("YouTube")
    tab_act = tabs.tab("Actividad")

    corte_tabs = ctk.CTkTabview(tab_corte_main, corner_radius=10)
    corte_tabs.pack(fill="both", expand=True, padx=6, pady=6)
    corte_tabs.add("Corte editado")
    corte_tabs.add("Corte individual")
    corte_tabs.add("Visualizador")
    corte_tabs.add("Pegar visualizador")

    sub_tabs = ctk.CTkTabview(tab_sub_main, corner_radius=10)
    sub_tabs.pack(fill="both", expand=True, padx=6, pady=6)
    sub_tabs.add("Generar subtitulos")
    sub_tabs.add("Subtitular video")

    ia_tabs = ctk.CTkTabview(tab_ia_main, corner_radius=10)
    ia_tabs.pack(fill="both", expand=True, padx=6, pady=6)
    ia_tabs.add("IA Clips")
    ia_tabs.add("IA TikTok")

    desc_tabs = ctk.CTkTabview(tab_desc_main, corner_radius=10)
    desc_tabs.pack(fill="both", expand=True, padx=6, pady=6)
    desc_tabs.add("Audio MP3")
    desc_tabs.add("YouTube MP3")
    desc_tabs.add("YouTube MP4")

    tab_corte = corte_tabs.tab("Corte editado")
    tab_ind = corte_tabs.tab("Corte individual")
    tab_srt = sub_tabs.tab("Generar subtitulos")
    tab_sub = sub_tabs.tab("Subtitular video")
    tab_clips = ia_tabs.tab("IA Clips")
    tab_ai = ia_tabs.tab("IA TikTok")
    tab_audio = desc_tabs.tab("Audio MP3")
    tab_youtube = desc_tabs.tab("YouTube MP3")
    tab_youtube_mp4 = desc_tabs.tab("YouTube MP4")

    corte_api = corte_tab.create_tab(tab_corte, {
        "estado": estado,
        "rango": rango,
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "limpiar_entry": limpiar_entry,
        "alerta_busy": alerta_busy,
        "abrir_videos": abrir_videos,
        "stop_control": stop_control,
        "procesar_video_fn": procesar_video_fn,
        "beep_fin": beep_fin,
    })
    corte_scroll = corte_api["scroll"]
    set_preview_enabled = corte_api["set_preview_enabled"]
    cargar_video_preview = corte_api["cargar_video_preview"]
    actualizar_etiquetas_rango = corte_api["actualizar_etiquetas_rango"]

    ind_api = corte_individual_tab.create_tab(tab_ind, {
        "estado": estado,
        "rango_ind": rango_ind,
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "limpiar_entry": limpiar_entry,
        "alerta_busy": alerta_busy,
        "abrir_videos": abrir_videos,
        "stop_control": stop_control,
        "beep_fin": beep_fin,
        "renombrar_si_largo": renombrar_si_largo,
        "set_preview_enabled": set_preview_enabled,
        "cargar_video_preview": cargar_video_preview,
    })
    ind_scroll = ind_api["scroll"]
    actualizar_etiquetas_rango_ind = ind_api["actualizar_etiquetas_rango_ind"]

    tab_visual = corte_tabs.tab("Visualizador")
    tab_pegar_visual = corte_tabs.tab("Pegar visualizador")
    corte_visualizer_tab.create_tab(tab_visual, {
        "estado": estado,
    })
    pegar_visualizador_tab.create_tab(tab_pegar_visual, {
        "estado": estado,
        "log": log,
        "stop_control": stop_control,
        "alerta_busy": alerta_busy,
        "beep_fin": beep_fin,
    })

    cortar_visualizador_tab.create_tab(tab_cortar_visual, {
        "estado": estado,
        "log": log,
        "log_seccion": log_seccion,
        "alerta_busy": alerta_busy,
        "stop_control": stop_control,
        "generar_visualizador_fn": generar_visualizador_solo,
    })

    srt_api = srt_tab.create_tab(tab_srt, {
        "srt_state": srt_state,
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "limpiar_entry": limpiar_entry,
        "alerta_busy": alerta_busy,
        "abrir_subtitulos": abrir_subtitulos,
        "stop_control": stop_control,
        "beep_fin": beep_fin,
        "renombrar_si_largo": renombrar_si_largo,
    })
    srt_scroll = srt_api["scroll"]

    sub_api = subtitular_tab.create_tab(tab_sub, {
        "sub_state": sub_state,
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "limpiar_entry": limpiar_entry,
        "alerta_busy": alerta_busy,
        "stop_control": stop_control,
        "beep_fin": beep_fin,
        "renombrar_si_largo": renombrar_si_largo,
    })
    sub_scroll = sub_api["scroll"]

    clips_api = ia_clips_tab.create_tab(tab_clips, {
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "alerta_busy": alerta_busy,
        "stop_control": stop_control,
        "beep_fin": beep_fin,
        "renombrar_si_largo": renombrar_si_largo,
    })
    clips_scroll = clips_api["scroll"]

    ai_api = ia_tiktok_tab.create_tab(tab_ai, {
        "ventana": ventana,
        "ai_state": ai_state,
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "alerta_busy": alerta_busy,
        "stop_control": stop_control,
        "beep_fin": beep_fin,
    })
    ai_scroll = ai_api["scroll"]

    audio_tab.create_tab(tab_audio, {
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "alerta_busy": alerta_busy,
        "stop_control": stop_control,
        "beep_fin": beep_fin,
        "renombrar_si_largo": renombrar_si_largo,
        "abrir_audios": abrir_audios,
    })

    youtube_mp3_tab.create_tab(tab_youtube, {
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "limpiar_entry": limpiar_entry,
        "alerta_busy": alerta_busy,
        "stop_control": stop_control,
        "beep_fin": beep_fin,
        "abrir_descargas": abrir_descargas,
    })

    youtube_mp4_tab.create_tab(tab_youtube_mp4, {
        "log": log,
        "log_global": log,
        "log_seccion": log_seccion,
        "limpiar_entry": limpiar_entry,
        "alerta_busy": alerta_busy,
        "stop_control": stop_control,
        "beep_fin": beep_fin,
        "abrir_descargas": abrir_descargas,
    })

    youtube_upload_tab.create_tab(tab_youtube_main, {
        "log": log,
        "log_global": log,
        "stop_control": stop_control,
        "youtube_state": youtube_state,
    })

    actividad_tab.create_tab(tab_act, {
        "log_state": log_state,
        "log": log,
        "abrir_transcripciones": abrir_transcripciones,
        "eliminar_audios": lambda: eliminar_audios(log),
        "stop_control": stop_control,
    })

    set_preview_enabled(True)
    actualizar_etiquetas_rango()
    actualizar_etiquetas_rango_ind()
    ventana.after(150, lambda: getattr(corte_scroll, "_parent_canvas", None) and corte_scroll._parent_canvas.yview_moveto(0))
    ventana.after_idle(lambda: ventana.state("zoomed"))

    return ventana, None, log, None

