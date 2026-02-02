from core import stop_control


def create_state():
    return {
        "estado": {
            "path": None,
            "es_audio": False,
            "fondo_path": None,
            "visualizador": False,
            "posicion_visualizador": "centro",
            "visualizador_opacidad": 0.65,
            "visualizador_color": "#FFFFFF",
            "visualizador_margen": 0,
            "visualizador_exposicion": 0.0,
            "visualizador_contraste": 1.0,
            "visualizador_saturacion": 1.0,
            "visualizador_temperatura": 0.0,
            "visualizador_blend_mode": "lighten",
            "visualizador_overlay_image": None,
            "visualizador_overlay_start": 0.0,
            "visualizador_overlay_duration": 2.0,
            "pegar_visualizador_base_video": None,
            "pegar_visualizador_overlay_video": None,
        },
        "rango": {"duracion": 0.0, "inicio": 0.0, "fin": 0.0},
        "rango_ind": {"duracion": 0.0, "inicio": 0.0, "fin": 0.0},
        "srt_state": {"items": []},
        "sub_state": {"videos": [], "srts": []},
        "ai_state": {"srt": None},
        "youtube_state": {"last_video_id": None},
        "stop_control": stop_control,
    }
