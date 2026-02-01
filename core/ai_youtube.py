import os
import re
import requests
from dotenv import load_dotenv

from core.transcriber import transcribir
from core.youtube_upload import upload_video
from core.utils import obtener_duracion_segundos

load_dotenv()

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


def _fetch_api_key(provided: str | None) -> str:
    if provided and provided.strip():
        return provided.strip()
    return os.getenv("OPENAI_API_KEY", "").strip()


def _parse_response(content: str) -> dict[str, str]:
    fields = {"titulo": "", "descripcion": "", "resumen": "", "palabras": ""}
    current = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("TITULO:"):
            current = "titulo"
            fields["titulo"] = line[len("TITULO:"):].strip()
            continue
        if upper.startswith("DESCRIPCION:"):
            current = "descripcion"
            fields["descripcion"] = line[len("DESCRIPCION:"):].strip()
            continue
        if upper.startswith("RESUMEN:"):
            current = "resumen"
            fields["resumen"] = line[len("RESUMEN:"):].strip()
            continue
        if upper.startswith("PALABRAS:"):
            current = "palabras"
            fields["palabras"] = line[len("PALABRAS:"):].strip()
            continue
        if current:
            fields[current] = (fields[current] + " " + line).strip()
    return fields


def generar_textos_youtube(
    video_path: str,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    idioma: str = "es",
    logs=None,
) -> dict[str, str]:
    if not video_path:
        raise ValueError("Video no especificado para generar texto.")
    api_key = _fetch_api_key(api_key)
    if not api_key:
        raise RuntimeError("Falta la API key de OpenAI (OPENAI_API_KEY).")
    if logs:
        logs("Transcribiendo video para IA...")
    texto = transcribir(video_path, idioma=idioma, model_size="small")
    if not texto:
        raise RuntimeError("La transcripción no devolvió texto válido.")
    max_chars = 9000
    if len(texto) > max_chars:
        if logs:
            logs(f"Transcripción truncada a {max_chars} caracteres.")
        texto = texto[:max_chars]

    system = (
        "Eres un redactor profesional para YouTube. "
        "Genera un resultado en español con el siguiente formato exacto:\n"
        "TITULO:\n...\n"
        "DESCRIPCION:\n...\n"
        "RESUMEN:\n...\n"
        "PALABRAS:\n...\n"
        "El título debe captar la atención, la descripción resumir el contenido y el resumen debe explicar el gancho y el valor. "
        "Incluye palabras clave o hashtags relevantes en PALABRAS."
    )
    user = f"Transcripción:\n{texto}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
    }
    if logs:
        logs("Llamando a OpenAI para generar metadatos...")
    response = requests.post(
        OPENAI_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"OpenAI error {response.status_code}: {response.text[:300]}")
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()
    return _parse_response(content)


def _format_hashtags(input_value: str) -> list[str]:
    parts = [entry.strip("# ").strip() for entry in re.split(r"[,\n]+", input_value) if entry.strip()]
    return [f"#{entry}" for entry in parts]


def subir_video_youtube_desde_ia(
    video_path: str,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    idioma: str = "es",
    privacy: str = "private",
    log_fn=None,
) -> dict[str, str]:
    metadata = generar_textos_youtube(video_path, api_key, model=model, idioma=idioma, logs=log_fn)
    title = metadata.get("titulo") or os.path.splitext(os.path.basename(video_path))[0]
    description = metadata.get("descripcion", "")
    hashtags = _format_hashtags(metadata.get("palabras", ""))
    if hashtags:
        description = f"{description}\n\n{','.join(hashtags)}"
    tags_list = [tag for tag in hashtags]
    duration = obtener_duracion_segundos(video_path)
    is_short = duration <= 60
    video_id = upload_video(
        video_path,
        title,
        description,
        tags_list,
        privacy=privacy,
        is_short=is_short,
        log_fn=log_fn,
    )
    return {
        "video_id": video_id,
        "title": title,
        "description": description,
        "tags": tags_list,
    }
