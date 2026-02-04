from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Iterable, Sequence

import requests

from core.video_transcription import (
    extraer_audio_y_subtitulos,
    obtener_transcripcion_para_video,
)
from core.google_drive import delete_file, upload_and_share_file
from core.api_endpoints import get_primary_endpoint_url

TRANSFER_TEMPLATE = get_primary_endpoint_url("transfer.sh upload")
FILE_IO_URL = get_primary_endpoint_url("file.io upload")
DEFAULT_ENDPOINT = get_primary_endpoint_url("WhatsApp upload endpoint")
DEFAULT_INTERVAL_SECONDS = 90
DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_API_URL = get_primary_endpoint_url("OpenAI Chat")


def _fetch_api_key(provided: str | None) -> str:
    if provided and provided.strip():
        return provided.strip()
    return os.getenv("OPENAI_API_KEY", "").strip()


def _normalize_number(value: str) -> str | None:
    normalized = "".join(ch for ch in value if ch.isdigit() or ch == "+").strip()
    return normalized or None


def _normalize_numbers(values: Iterable[str]) -> list[str]:
    clean_list = []
    for value in values:
        normalized = _normalize_number(value)
        if normalized:
            clean_list.append(normalized)
    return clean_list


def _extract_json(content: str) -> dict | list:
    text = content.strip()
    if not text:
        raise ValueError("Respuesta vacía de la IA.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError("No se pudo interpretar la respuesta de OpenAI como JSON.")


def _extract_messages(payload: dict | list) -> list[str]:
    if isinstance(payload, dict):
        candidates = payload.get("mensajes") or payload.get("messages") or payload.get("arr") or payload.get("array")
    else:
        candidates = payload
    if not isinstance(candidates, list):
        raise ValueError("El JSON debe contener un array en la clave 'mensajes' o directamente ser una lista.")
    messages: list[str] = []
    for item in candidates:
        text = str(item).strip()
        if text:
            messages.append(text)
    return messages


def generar_mensajes_whatsapp(
    video_path: str,
    api_key: str | None = None,
    idioma: str = "es",
    cantidad: int = 3,
    model: str = DEFAULT_MODEL,
    logs=None,
) -> list[str]:
    if not video_path:
        raise ValueError("Debe especificarse un video o audio.")
    numero = max(1, int(cantidad))
    api_key = _fetch_api_key(api_key)
    if not api_key:
        raise RuntimeError("Falta la API key de OpenAI (OPENAI_API_KEY).")
    texto = obtener_transcripcion_para_video(video_path, idioma, logs=logs)
    extraer_audio_y_subtitulos(video_path, idioma, logs=logs)
    system = (
        "Eres un redactor que convierte contenido de video en mensajes cortos "
        "para WhatsApp que transmiten el mismo mensaje informativo."
        "Responde en español con un solo JSON válido que tenga la forma:\n"
        "{\n"
        '  "mensajes": [\n'
        '    "...",\n'
        "    ...\n"
        "  ]\n"
        "}\n"
        "Cada mensaje debe ser distinto, claro y no superar 200 caracteres. "
        "Incluye el nombre del video o un gancho directo en cada mensaje."
    )
    user = (
        f"Transcripción:\n{texto}\n\n"
        f"Genera exactamente {numero} mensajes distintos, cada uno asociado al mismo mensaje del video."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
    }
    if logs:
        logs("Llamando a OpenAI para construir mensajes de WhatsApp...")
    response = requests.post(
        OPENAI_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if response.status_code != 200:
        raise RuntimeError(f"OpenAI error {response.status_code}: {response.text[:300]}")
    content = response.json()["choices"][0]["message"]["content"]
    payload = _extract_json(content)
    messages = _extract_messages(payload)
    if len(messages) < numero:
        raise RuntimeError("OpenAI no devolvió suficientes mensajes.")
    return messages[:numero]


def upload_media_to_transfer(path: str, logs=None, max_attempts: int = 3) -> str:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        with path_obj.open("rb") as source:
            if logs:
                logs(f"Subiendo {path_obj.name} a transfer.sh (intento {attempt}/{max_attempts})...")
            try:
                url = TRANSFER_TEMPLATE.format(filename=path_obj.name)
                response = requests.put(
                    url,
                    data=source,
                    timeout=120,
                )
                response.raise_for_status()
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts:
                    if logs:
                        logs(f"Transfer.sh fallo: {exc}. Reintentando...")
                    time.sleep(1)
                    continue
                raise RuntimeError(f"Transfer.sh falló tras {max_attempts} intentos: {exc}") from exc
            url = response.text.strip()
            if not url:
                raise RuntimeError("Transfer.sh no devolvió URL.")
            if logs:
                logs(f"URL pública obtenida: {url}")
            return url
    raise RuntimeError(f"Transfer.sh falló sin respuesta válida: {last_exc}")


def _upload_to_fileio(path: str, logs=None) -> str:
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    if logs:
        logs(f"Subiendo {path_obj.name} a file.io...")
    with path_obj.open("rb") as source:
        response = requests.post(
            FILE_IO_URL,
            files={"file": (path_obj.name, source)},
            timeout=120,
        )
    response.raise_for_status()
    try:
        payload = response.json()
    except Exception:
        # file.io sometimes responds with non-JSON (HTML/text) depending on region/rate limits.
        preview = (response.text or "").strip().replace("\n", " ")[:240]
        if logs:
            logs(f"file.io respuesta no-JSON (status {response.status_code}): {preview}")
        match = re.search(r"https?://\\S+", response.text or "")
        if match:
            link = match.group(0).strip()
            if logs:
                logs(f"URL detectada en respuesta file.io: {link}")
            return link
        raise RuntimeError("file.io devolvió una respuesta inválida (no JSON).")
    link = payload.get("link") or (payload.get("data") or {}).get("link") or payload.get("url")
    if not link:
        raise RuntimeError("file.io no devolvió una URL.")
    if logs:
        logs(f"URL pública obtenida de file.io: {link}")
    return link


def _convert_drive_link(url: str) -> str | None:
    match = re.search(r"/file/d/([^/]+)", url)
    if not match:
        match = re.search(r"id=([^&]+)", url)
    if not match:
        return None
    file_id = match.group(1)
    return f"https://drive.google.com/uc?export=download&id={file_id}"


def ensure_media_url(path: str | None, logs=None) -> str | None:
    if not path:
        return None
    trimmed = path.strip()
    if not trimmed:
        return None
    lower = trimmed.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        if "drive.google.com" in lower:
            direct = _convert_drive_link(trimmed)
            if direct:
                if logs:
                    logs(f"Google Drive detectado, usando enlace directo: {direct}")
                return direct
        return trimmed
    try:
        return upload_media_to_transfer(trimmed, logs=logs)
    except Exception as exc:
        if logs:
            logs(f"Transfer.sh falló: {exc}. Probando file.io...")
    return _upload_to_fileio(trimmed, logs=logs)


def upload_media_to_drive(path: str, logs=None, folder_id: str | None = None) -> tuple[str, str]:
    file_id, link = upload_and_share_file(path, folder_id=folder_id)
    if logs:
        logs(f"URL pública generada en Drive: {link}")
    return file_id, link


def delete_drive_file(file_id: str, logs=None):
    delete_file(file_id)
    if logs:
        logs(f"Archivo eliminado de Google Drive: {file_id}")


def send_whatsapp_message(
    number: str,
    message: str,
    media_url: str | None = None,
    endpoint: str = DEFAULT_ENDPOINT,
) -> dict | None:
    payload = {"number": number, "message": message}
    if media_url:
        payload["urlMedia"] = media_url
    response = requests.post(endpoint, json=payload, timeout=30)
    response.raise_for_status()
    text = response.text.strip()
    if not text:
        return {"status_code": response.status_code}
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "raw": text}


def enviar_mensajes_whatsapp(
    entries: Sequence[dict],
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    log_fn=None,
    stop_control=None,
    endpoint: str = DEFAULT_ENDPOINT,
) -> None:
    if not entries:
        raise ValueError("No hay contactos para enviar.")
    total = len(entries)
    for idx, entry in enumerate(entries):
        raw_number = str(entry.get("number") or "").strip()
        message = str(entry.get("message") or "").strip()
        media_url = entry.get("media_url")
        number = _normalize_number(raw_number)
        if not number:
            raise ValueError(f"El número en la entrada {idx + 1} no es válido.")
        if not message:
            raise ValueError(f"Falta el mensaje para el número {number}.")
        if stop_control and stop_control.should_stop():
            if log_fn:
                log_fn("Stop solicitado. Finalizando envíos de WhatsApp.")
            break
        if log_fn:
            log_fn(f"[{idx+1}/{total}] Enviando a {number}...")
        try:
            send_whatsapp_message(number, message, media_url=media_url, endpoint=endpoint)
            if log_fn:
                log_fn(f"Mensaje enviado a {number}.")
        except Exception as exc:
            if log_fn:
                log_fn(f"Error al enviar a {number}: {exc}")
        if idx < total - 1:
            time.sleep(max(0.0, interval_seconds))
