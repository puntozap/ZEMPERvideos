import os
import threading
import customtkinter as ctk


def iniciar_app(procesar_video_fn):
    # Configuración global
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    ventana = ctk.CTk()
    ventana.title("🎬 Transcriptor de Video")
    ventana.geometry("700x500")

    frame_main = ctk.CTkFrame(master=ventana, corner_radius=12)
    frame_main.pack(fill="both", expand=True, padx=20, pady=20)

    # --- Área de logs y progreso se crean después ---
    txt_logs = ctk.CTkTextbox(frame_main, height=220, width=650, corner_radius=10)
    txt_logs.pack_forget()  # lo ocultamos de momento, se organiza abajo
    progress = ctk.CTkProgressBar(frame_main, width=650)

    # --- Funciones auxiliares ---
    def log(msg):
        txt_logs.configure(state="normal")
        txt_logs.insert("end", msg + "\n")
        txt_logs.see("end")
        txt_logs.configure(state="disabled")

    def actualizar_progreso(valor, maximo=100):
        progress.set(valor / maximo if maximo > 0 else 0)

    def abrir_transcripciones():
        folder = os.path.abspath("output/transcripciones")
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.startfile(folder)  # Windows

    def eliminar_audios(log_fn=None):
        folder = os.path.abspath("downloads")
        if not os.path.exists(folder):
            return
        count = 0
        for f in os.listdir(folder):
            if f.lower().endswith((".wav", ".webm", ".mp4")):
                try:
                    os.remove(os.path.join(folder, f))
                    count += 1
                except Exception as e:
                    if log_fn:
                        log_fn(f"❌ No se pudo borrar {f}: {e}")
        if log_fn:
            log_fn(f"🗑 {count} audios eliminados de downloads/")

    # --- Botón para seleccionar video local ---
    def on_click_local():
        from ui.dialogs import seleccionar_video
        video = seleccionar_video()
        if video:
            threading.Thread(
                target=procesar_video_fn,
                args=(video, False, False),
                daemon=True
            ).start()

    btn_local = ctk.CTkButton(
        frame_main,
        text="🎥 Seleccionar Video Local",
        command=on_click_local,
        height=50,
        width=640,
        font=ctk.CTkFont(size=16, weight="bold")
    )
    btn_local.pack(pady=15)

    # --- Boton para seleccionar audio local ---
    def on_click_audio():
        from ui.dialogs import seleccionar_audio
        audio = seleccionar_audio()
        if audio:
            threading.Thread(
                target=procesar_video_fn,
                args=(audio, False, True),
                daemon=True
            ).start()

    btn_audio = ctk.CTkButton(
        frame_main,
        text="Seleccionar Audio Local",
        command=on_click_audio,
        height=45,
        width=640,
        font=ctk.CTkFont(size=14, weight="bold")
    )
    btn_audio.pack(pady=5)

    # --- Label + input + botón YouTube ---
    lbl_youtube = ctk.CTkLabel(
        frame_main,
        text="Subir link de video de YouTube:",
        font=ctk.CTkFont(size=14)
    )
    lbl_youtube.pack(pady=(10, 5))

    frame_youtube = ctk.CTkFrame(frame_main, fg_color="transparent")
    frame_youtube.pack(pady=5)

    entrada_url = ctk.CTkEntry(
        frame_youtube,
        placeholder_text="Pega el enlace aquí",
        width=400
    )
    entrada_url.pack(side="left", padx=10)

    def on_click_youtube():
        url = entrada_url.get().strip()
        if url:
            threading.Thread(
                target=procesar_video_fn,
                args=(url, True, False),
                daemon=True
            ).start()

    btn_youtube = ctk.CTkButton(
        frame_youtube,
        text="📥 Descargar Audio",
        command=on_click_youtube,
        height=40,
        width=180
    )
    btn_youtube.pack(side="left", padx=10)

    # --- Botones adicionales ---
    btn_abrir = ctk.CTkButton(
        frame_main,
        text="📂 Abrir Transcripciones",
        command=abrir_transcripciones,
        height=40,
        width=300
    )
    btn_abrir.pack(pady=5)

    btn_eliminar = ctk.CTkButton(
        frame_main,
        text="🗑 Eliminar Audios",
        command=lambda: eliminar_audios(log),
        fg_color="red",
        hover_color="#b22222",
        height=40,
        width=300
    )
    btn_eliminar.pack(pady=5)

    # --- Barra de progreso ---
    progress.pack(pady=15)
    progress.set(0)

    # --- Área de logs ---
    txt_logs.pack(pady=10, padx=10)
    txt_logs.configure(state="disabled")

    return ventana, progress, log, entrada_url
