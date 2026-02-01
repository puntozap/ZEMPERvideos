from ui.main_window import iniciar_app
from core.workflow import procesar_video

if __name__ == "__main__":
    ventana, barra, log, entrada_url = iniciar_app(
        lambda path, es_youtube=False, es_audio=False, minutos_por_parte=5, inicio_min=None, fin_min=None, dividir_video=True, vertical_tiktok=False, vertical_orden="LR", recorte_top=0.12, recorte_bottom=0.12, generar_srt=True, fondo_path=None, fondo_estilo="fill", fondo_escala=0.92, solo_video=False, visualizador=False, posicion_visualizador="centro":
        procesar_video(path, es_youtube, es_audio, minutos_por_parte, inicio_min, fin_min, dividir_video, vertical_tiktok, vertical_orden, recorte_top, recorte_bottom, generar_srt, fondo_path, fondo_estilo, fondo_escala, solo_video, barra, log, visualizador=visualizador, posicion_visualizador=posicion_visualizador)
    )
    ventana.mainloop()
