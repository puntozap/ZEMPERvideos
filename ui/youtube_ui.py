import threading
import tkinter as tk

def configurar_youtube(master, procesar_video_fn):
    """
    Crea un campo de entrada + botón para pegar enlace de YouTube
    """
    frame = tk.Frame(master)

    entrada = tk.Entry(frame, width=40)
    entrada.pack(side=tk.LEFT, padx=5)

    def on_click():
        url = entrada.get().strip()
        if url:
            threading.Thread(target=procesar_video_fn, args=(url, True), daemon=True).start()

    btn = tk.Button(frame, text="📥 Descargar YouTube", command=on_click, height=2, width=18)
    btn.pack(side=tk.LEFT, padx=5)

    return frame, entrada
