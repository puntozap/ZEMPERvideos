DEFAULT_CORTE_CONFIG = {
    "recorte_manual_top": 0.25,
    "recorte_manual_bottom": 0.25,
    "inset_left_pct": 7.0,
    "inset_right_pct": 4.0,
    "inset_top_pct": 22.0,
    "inset_bottom_pct": 8.0,
    "zoom": 1.0,
    "bg_crop_top_pct": 0.0,
    "bg_crop_bottom_pct": 0.0,
}

DEFAULT_CINTAS_CONFIG = [
    {
        "lado": "izquierda",
        "left_pct": 7.0,
        "top_pct": 73.0,
        "width_pct": 42.0,
        "height_pct": 10.0,
        "bg_color": "#000000",
        "border_color": "#F8BA11",
        "text_color": "#FFFFFF",
        "fontfile_name": "C:\\Windows\\Fonts\\arialbd.ttf",
        "fontfile_role": "C:\\Windows\\Fonts\\arial.ttf",
        "nombre": "Invitado",
        "rol": "Rol / Profesión",
    },
    {
        "lado": "derecha",
        "left_pct": 51.5,
        "top_pct": 73.0,
        "width_pct": 42.0,
        "height_pct": 10.0,
        "bg_color": "#000000",
        "border_color": "#F8BA11",
        "text_color": "#FFFFFF",
        "fontfile_name": "C:\\Windows\\Fonts\\arialbd.ttf",
        "fontfile_role": "C:\\Windows\\Fonts\\arial.ttf",
        "nombre": "Host",
        "rol": "Rol / Profesión",
    },
]

DEFAULT_MENSAJES_CONFIG = [
    {
        "left_pct": 2.0,
        "top_pct": 9.0,
        "width_pct": 48.0,
        "height_pct": 6.0,
        "bg_color": "#D91E18",
        "text_color": "#FFFFFF",
        "border_color": "#FFC400",
        "text": "Suscríbete y comparte",
        "fontfile": "C:\\Windows\\Fonts\\arialbd.ttf",
        "radius_pct": 0.5,
        "border_width": 2,
    }
]


def get_corte_defaults() -> dict:
    return dict(DEFAULT_CORTE_CONFIG)


def get_cintas_defaults() -> list[dict]:
    return [dict(item) for item in DEFAULT_CINTAS_CONFIG]


def get_mensajes_defaults() -> list[dict]:
    return [dict(item) for item in DEFAULT_MENSAJES_CONFIG]
