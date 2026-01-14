from ui.main_window import iniciar_app
from core.workflow import procesar_video

if __name__ == "__main__":
    ventana, barra, log, entrada_url = iniciar_app(
        lambda path, es_youtube=False, es_audio=False: procesar_video(path, es_youtube, es_audio, barra, log)
    )
    ventana.mainloop()
