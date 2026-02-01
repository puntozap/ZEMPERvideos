from core import stop_control


def create_state():
    return {
        "estado": {"path": None, "es_audio": False, "fondo_path": None},
        "rango": {"duracion": 0.0, "inicio": 0.0, "fin": 0.0},
        "rango_ind": {"duracion": 0.0, "inicio": 0.0, "fin": 0.0},
        "srt_state": {"items": []},
        "sub_state": {"videos": [], "srts": []},
        "ai_state": {"srt": None},
        "youtube_state": {"last_video_id": None},
        "stop_control": stop_control,
    }
