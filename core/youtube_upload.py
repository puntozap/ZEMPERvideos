from __future__ import annotations

import mimetypes
import os
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, List, Optional

import requests

from core.youtube_credentials import YouTubeCredentials, load_active_credentials
from core.api_endpoints import get_all_endpoint_urls

UPLOAD_INIT_URL, THUMBNAIL_UPLOAD_URL = get_all_endpoint_urls("YouTube upload")
CHUNK_SIZE = 256 * 1024
_token_lock = threading.Lock()
_token_cache: dict[str, object] = {}


class YouTubeUploadError(Exception):
    pass


def _guess_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "video/mp4"


def _chunked_reader(path: Path, chunk_size: int = CHUNK_SIZE) -> Iterable[bytes]:
    with path.open("rb") as source:
        while True:
            chunk = source.read(chunk_size)
            if not chunk:
                break
            yield chunk


def _cache_token(creds: YouTubeCredentials, access_token: str, expires_in: int) -> None:
    expires_at = time.time() + expires_in
    _token_cache.update(
        {
            "access_token": access_token,
            "expires_at": expires_at,
            "client_id": creds.client_id,
        }
    )


def _get_cached_token(creds: YouTubeCredentials) -> Optional[str]:
    token = _token_cache.get("access_token")
    if not token:
        return None
    if _token_cache.get("client_id") != creds.client_id:
        return None
    expires_at = _token_cache.get("expires_at", 0)
    if time.time() >= expires_at - 30:
        return None
    return token


def _refresh_access_token(creds: YouTubeCredentials) -> str:
    with _token_lock:
        cached = _get_cached_token(creds)
        if cached:
            return cached
        response = requests.post(
            creds.token_uri,
            data={
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "refresh_token": creds.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise YouTubeUploadError(f"No se pudo renovar token: {exc}") from exc

    payload = response.json()
    access_token = payload.get("access_token")
    expires_in = int(payload.get("expires_in", 3600))
    if not access_token:
        raise YouTubeUploadError("La respuesta del token no devolvió access_token.")
    _cache_token(creds, access_token, expires_in)
    return access_token


def _get_access_token(creds: YouTubeCredentials) -> str:
    token = _get_cached_token(creds)
    if token:
        return token
    return _refresh_access_token(creds)


def _prepare_snippet(title: str, description: str, tags: Optional[List[str]], is_short: bool) -> dict:
    safe_tags = [tag for tag in (tags or []) if tag.strip()]
    if is_short and "#Shorts" not in (tag.lower() for tag in safe_tags):
        safe_tags.append("#Shorts")
    snippet = {
        "title": title,
        "description": description,
    }
    if safe_tags:
        snippet["tags"] = safe_tags
    return snippet


def _init_resumable_upload(
    access_token: str,
    snippet: dict,
    privacy: str,
    file_size: int,
    content_type: str,
    log_fn: Optional[Callable[[str], None]] = None,
) -> str:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": content_type,
        "Content-Type": "application/json; charset=UTF-8",
    }
    response = requests.post(
        UPLOAD_INIT_URL,
        params={"uploadType": "resumable", "part": "snippet,status"},
        json={"snippet": snippet, "status": {"privacyStatus": privacy}},
        headers=headers,
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        if log_fn:
            log_fn(f"Respuesta init resumable: {response.status_code} {response.text}")
        raise YouTubeUploadError(f"No se pudo iniciar la carga: {exc}") from exc
    upload_url = response.headers.get("Location") or response.headers.get("location")
    if not upload_url:
        raise YouTubeUploadError("La respuesta no devolvió la URL de carga.")
    return upload_url


def _upload_media(upload_url: str, path: Path, content_type: str, log_fn: Optional[Callable[[str], None]] = None) -> dict:
    file_size = path.stat().st_size
    # 10MB por pedazo (debe ser múltiplo de 256KB)
    chunk_size = 10 * 1024 * 1024 
    
    with path.open("rb") as f:
        start_byte = 0
        while start_byte < file_size:
            chunk = f.read(chunk_size)
            end_byte = start_byte + len(chunk) - 1
            
            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
                "Content-Type": content_type,
            }

            try:
                # Al enviar por trozos, el socket se abre y cierra correctamente
                response = requests.put(upload_url, data=chunk, headers=headers, timeout=60)
                
                # 308 es "Resume Incomplete", significa que YouTube recibió el trozo y espera más
                if response.status_code in [200, 201]:
                    return response.json()
                elif response.status_code == 308:
                    start_byte += len(chunk)
                    if log_fn:
                        progreso = (start_byte / file_size) * 100
                        log_fn(f"Subido: {progreso:.2f}%")
                else:
                    response.raise_for_status()

            except (requests.exceptions.ConnectionError, ConnectionAbortedError):
                if log_fn:
                    log_fn("Conexión interrumpida por el sistema. Reintentando trozo...")
                # Retrocedemos el puntero del archivo para reintentar este trozo
                f.seek(start_byte)
                time.sleep(2)
    file_size = path.stat().st_size
    headers = {
        "Content-Length": str(file_size),
        "Content-Type": content_type,
        "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
    }
    if log_fn:
        log_fn(f"Media headers: {headers}")
    response = requests.put(
        upload_url,
        data=_chunked_reader(path),
        headers=headers,
        timeout=300,
    )
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        raise YouTubeUploadError(f"Error al subir el video: {exc}") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise YouTubeUploadError(f"Respuesta inesperada de YouTube: {exc}") from exc


def _guess_image_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/jpeg"


def set_thumbnail(
    video_id: str,
    thumbnail_path: Path | str,
    log_fn: Optional[Callable[[str], None]] = None,
) -> dict:
    if isinstance(thumbnail_path, str):
        thumbnail_path = Path(thumbnail_path)
    if not thumbnail_path.exists():
        raise YouTubeUploadError("No existe la miniatura seleccionada.")
    creds = load_active_credentials()
    access_token = _get_access_token(creds)
    data = thumbnail_path.read_bytes()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": _guess_image_type(thumbnail_path),
    }
    params = {"videoId": video_id}
    response = requests.post(
        THUMBNAIL_UPLOAD_URL,
        params=params,
        headers=headers,
        data=data,
        timeout=60,
    )
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        if log_fn:
            log_fn(f"Miniatura error: {response.status_code} {response.text}")
        raise YouTubeUploadError(f"No se pudo subir la miniatura: {exc}") from exc
    return response.json()


def upload_video(
    path: Path | str,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    privacy: str = "public",
    is_short: bool = False,
    log_fn: Optional[Callable[[str], None]] = None,
) -> str:
    if isinstance(path, str):
        path = Path(path)
    if not path.exists():
        raise YouTubeUploadError("El archivo de video no existe.")

    creds = load_active_credentials()
    access_token = _get_access_token(creds)
    snippet = _prepare_snippet(title, description, tags, is_short)
    file_size = path.stat().st_size
    content_type = _guess_mime_type(path)
    if log_fn:
        log_fn(f"Iniciando carga resumable ({file_size / (1024**2):.1f} MB)...")
    upload_url = _init_resumable_upload(
        access_token, snippet, privacy, file_size, content_type, log_fn=log_fn
    )
    if log_fn:
        log_fn("Subiendo bytes del video...")
    response = _upload_media(upload_url, path, content_type, log_fn=log_fn)
    video_id = response.get("id") or response.get("videoId")
    if not video_id:
        raise YouTubeUploadError("YouTube no devolvió el ID del video.")
    if log_fn:
        log_fn(f"Video subido con ID: {video_id}")
    return video_id

def obtener_token_activo(log_fn: Optional[Callable[[str], None]] = None) -> str:
    creds = load_active_credentials()
    token = _get_access_token(creds)
    if log_fn:
        log_fn("Token activo obtenido.")
    return token


__all__ = ["upload_video", "set_thumbnail", "YouTubeUploadError", "obtener_token_activo"]
