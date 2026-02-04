import os
import re
import requests
from dotenv import load_dotenv

from core.video_transcription import (
    MAX_TRANSCRIPTION_CHARS,
    extraer_audio_y_subtitulos,
    obtener_transcripcion_para_video,
)
from core.youtube_upload import YouTubeUploadError, upload_video
from core.api_endpoints import get_primary_endpoint_url
from core.utils import obtener_duracion_segundos

MAX_METADATA_ATTEMPTS = 3

load_dotenv()

OPENAI_API_URL = get_primary_endpoint_url("OpenAI Chat")


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
    texto: str | None = None,
    logs=None,
) -> dict[str, str]:
    if not video_path:
        raise ValueError("Video no especificado para generar texto.")
    api_key = _fetch_api_key(api_key)
    if not api_key:
        raise RuntimeError("Falta la API key de OpenAI (OPENAI_API_KEY).")
    max_chars = MAX_TRANSCRIPTION_CHARS
    if texto is None:
        texto = obtener_transcripcion_para_video(video_path, idioma, logs=logs, max_chars=max_chars)
    else:
        if logs:
            logs("Usando transcripción existente para IA...")
        texto = texto.strip()
        if not texto:
            raise RuntimeError("La transcripción existente no contiene texto.")
        if len(texto) > max_chars:
            texto = texto[:max_chars]

    system = (
        "Eres un redactor profesional para YouTube con enfoque periodístico y clickbait sano. "
        "Genera en español un resultado que siga estrictamente este formato:\n"
        "TITULO:\n...\n"
        "DESCRIPCION:\n...\n"
        "RESUMEN:\n...\n"
        "PALABRAS:\n...\n"
        "El TITULO debe tener entre 15 y 100 caracteres, no puede ser solo espacios ni quedar vacío, y debe destacar un gancho informativo contundente sin exagerar. "
        "La DESCRIPCION debe resumir el contenido y transmitir el valor principal del video. "
        "El RESUMEN debe explicar el gancho y establecer el contexto periodístico. "
        "PALABRAS debe listar hashtags o palabras clave relevantes separados por comas (sin duplicados) y no debe repetir literalmente frases completas de las otras secciones. "
        "Si algún campo no puede generarse con veracidad, escribe 'NO DISPONIBLE' en ese campo."
    )
    user = f"Transcripción:\n{texto}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
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
    max_attempts: int = MAX_METADATA_ATTEMPTS,
) -> dict[str, str]:
    if not video_path:
        raise ValueError("Video no especificado para subir.")
    attempts = max(1, int(max_attempts))
    fallback_title = os.path.splitext(os.path.basename(video_path))[0]
    duration = obtener_duracion_segundos(video_path)
    is_short = duration <= 60
    texto_base = obtener_transcripcion_para_video(video_path, idioma, logs=log_fn)
    extraer_audio_y_subtitulos(video_path, idioma, logs=log_fn)

    for intento in range(1, attempts + 1):
        if log_fn:
            log_fn(f"Intento {intento}/{attempts} de subida a YouTube.")
        metadata = generar_textos_youtube(
            video_path,
            api_key,
            model=model,
            idioma=idioma,
            texto=texto_base,
            logs=log_fn,
        )
        title = metadata.get("titulo", "").strip() or fallback_title
        description = metadata.get("descripcion", "")
        hashtags = _format_hashtags(metadata.get("palabras", ""))
        if hashtags:
            description = f"{description}\n\n{','.join(hashtags)}"
        tags_list = [tag for tag in hashtags]
        try:
            video_id = upload_video(
                video_path,
                title,
                description,
                tags_list,
                privacy=privacy,
                is_short=is_short,
                log_fn=log_fn,
            )
            if log_fn:
                log_fn(f"Video subido con ID: {video_id}")
            return {
                "video_id": video_id,
                "title": title,
                "description": description,
                "tags": tags_list,
            }
        except YouTubeUploadError as exc:
            if intento >= attempts:
                raise YouTubeUploadError(
                    f"No se pudo iniciar la carga tras {attempts} intentos: {exc}"
                ) from exc
            if log_fn:
                log_fn(
                    f"Upload falló en el intento {intento}: {exc}; regenerando metadatos y reintentando."
                )
            continue
