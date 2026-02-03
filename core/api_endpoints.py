"""Listado de endpoints externos consumidos por la app."""

EXTERNAL_API_ENDPOINTS = [
    {
        "name": "OpenAI Chat",
        "description": "Completions para generar metadatos (YouTube, mensajes WhatsApp, TikTok).",
        "url": "https://api.openai.com/v1/chat/completions",
    },
    {
        "name": "Google Drive API",
        "description": "Subida/compartido/eliminación de archivos mediante googleapiclient.",
        "url": "https://www.googleapis.com/drive/v3/files",
    },
    {
        "name": "Drive download link",
        "description": "Construcción de enlace compartido después de subir (export download).",
        "url": "https://drive.google.com/uc?export=download&id={file_id}",
    },
    {
        "name": "WhatsApp upload endpoint",
        "description": "Servicio de Chanzia que recibe número, mensaje y media.",
        "url": "https://chanzia.com/zemper/v1/messages",
    },
    {
        "name": "transfer.sh upload",
        "description": "Intento principal para subir media cuando no se usa Drive.",
        "url": "https://transfer.sh/{filename}",
    },
    {
        "name": "file.io upload",
        "description": "Fallback para subir media si transfer.sh falla.",
        "url": "https://file.io",
    },
    {
        "name": "YouTube OAuth",
        "description": "Autenticación OAuth para subir videos (cc client).",
        "url": "https://accounts.google.com/o/oauth2/auth",
    },
    {
        "name": "YouTube token refresh",
        "description": "Intercambio de código/token para proyectos YouTube.",
        "url": "https://oauth2.googleapis.com/token",
    },
    {
        "name": "YouTube upload",
        "description": "Carga resumable de videos y miniaturas.",
        "url": [
            "https://www.googleapis.com/upload/youtube/v3/videos",
            "https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
        ],
    },
    {
        "name": "YouTube Data",
        "description": "Consulta de playlists/videos subidos.",
        "url": "https://www.googleapis.com/youtube/v3",
    },
    {
        "name": "TikTok OAuth",
        "description": "Autenticación para la API de TikTok.",
        "url": [
            "https://www.tiktok.com/v2/auth/authorize/",
            "https://open.tiktokapis.com/v2/oauth/token/",
        ],
    },
    {
        "name": "TikTok upload init",
        "description": "Inicializa subida de videos a TikTok desde el backend.",
        "url": [
            "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/",
            "https://open.tiktokapis.com/v2/post/publish/video/init/",
        ],
    },
]


def get_endpoint(name: str) -> dict | None:
    for entry in EXTERNAL_API_ENDPOINTS:
        if entry["name"] == name:
            return entry
    return None


def get_primary_endpoint_url(name: str) -> str:
    entry = get_endpoint(name)
    if not entry:
        raise KeyError(f"Endpoint '{name}' no definido.")
    url = entry["url"]
    if isinstance(url, list):
        return url[0]
    return url


def get_all_endpoint_urls(name: str) -> list[str]:
    entry = get_endpoint(name)
    if not entry:
        raise KeyError(f"Endpoint '{name}' no definido.")
    url = entry["url"]
    return url if isinstance(url, list) else [url]
