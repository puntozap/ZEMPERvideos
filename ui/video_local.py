import threading
from ui.dialogs import seleccionar_video

def configurar_boton_video(master, btn_kwargs, procesar_video_fn):
    """
    Crea botón de selección de video local.
    - master: frame donde se coloca
    - btn_kwargs: kwargs para botón (ej. text, width, height)
    - procesar_video_fn: función callback para procesar el archivo seleccionado
    """
    import tkinter as tk
    def on_click():
        video = seleccionar_video()
        if video:
            threading.Thread(target=procesar_video_fn, args=(video, False), daemon=True).start()

    return tk.Button(master, command=on_click, **btn_kwargs)
