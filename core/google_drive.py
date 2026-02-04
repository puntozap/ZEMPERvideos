from __future__ import annotations

import os
import io
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from googleapiclient.http import MediaIoBaseUpload

from core.drive_config import (
    get_service_account_json,
    load_oauth_credentials,
    get_drive_folder_id,
)

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_credentials():
    service_path = get_service_account_json()
    if service_path:
        return service_account.Credentials.from_service_account_file(
            service_path, scopes=SCOPES
        )
    oauth = load_oauth_credentials()
    if oauth:
        return oauth
    raise RuntimeError(
        "No hay credenciales configuradas para Google Drive (service account o OAuth)."
    )


def _get_service():
    creds = _get_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def upload_and_share_file(path: str, folder_id: str | None = None, mime_type: str | None = None):
    service = _get_service()
    metadata = {"name": os.path.basename(path)}
    if folder_id:
        metadata["parents"] = [folder_id]
    media = MediaFileUpload(path, resumable=True, mimetype=mime_type or "application/octet-stream")
    file = service.files().create(body=metadata, media_body=media, fields="id").execute()
    file_id = file.get("id")
    if not file_id:
        raise RuntimeError("No se pudo obtener el ID del archivo subido.")
    try:
        service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
            fields="id",
        ).execute()
    except HttpError as exc:
        # Si el permiso ya existe, ignorar
        if exc.resp.status not in (409,):
            raise
    link = f"https://drive.google.com/uc?export=download&id={file_id}"
    return file_id, link


def create_google_doc_from_text(
    *,
    title: str,
    content: str,
    folder_id: str | None = None,
    share_anyone: bool = True,
    share_emails: list[str] | None = None,
    share_role: str = "writer",
):
    """
    Crea un Google Doc en Drive a partir de texto plano y devuelve (file_id, doc_url).

    Requiere credenciales de Drive (service account u OAuth). No usa Docs API; usa conversión
    de Drive (mimeType application/vnd.google-apps.document).
    """
    service = _get_service()
    name = (title or "Reporte").strip() or "Reporte"
    parent = (folder_id or "").strip() or (get_drive_folder_id() or "").strip() or None
    metadata: dict = {"name": name, "mimeType": "application/vnd.google-apps.document"}
    if parent:
        metadata["parents"] = [parent]

    data = (content or "").encode("utf-8")
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype="text/plain", resumable=False)
    file = service.files().create(body=metadata, media_body=media, fields="id").execute()
    file_id = file.get("id")
    if not file_id:
        raise RuntimeError("No se pudo obtener el ID del Google Doc creado.")

    if share_anyone:
        try:
            service.permissions().create(
                fileId=file_id,
                body={"role": "reader", "type": "anyone"},
                fields="id",
            ).execute()
        except HttpError as exc:
            if exc.resp.status not in (409,):
                raise

    emails = [e.strip() for e in (share_emails or []) if e and e.strip()]
    for email in emails:
        service.permissions().create(
            fileId=file_id,
            body={"role": share_role, "type": "user", "emailAddress": email},
            fields="id",
            sendNotificationEmail=True,
        ).execute()

    doc_url = f"https://docs.google.com/document/d/{file_id}/edit"
    return file_id, doc_url


def delete_file(file_id: str):
    service = _get_service()
    try:
        service.files().delete(fileId=file_id).execute()
    except HttpError as exc:
        if exc.resp.status == 404:
            return
        raise
