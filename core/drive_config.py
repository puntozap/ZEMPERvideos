from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SERVICE_ACCOUNT_ENV = "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON"
OAUTH_CLIENT_ENV = "GOOGLE_DRIVE_OAUTH_CLIENT_SECRET"
TOKEN_PATH = Path("credentials") / "drive_oauth_token.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]
DRIVE_CONFIG_PATH = TOKEN_PATH.parent / "drive_config.json"
SERVICE_ACCOUNT_STORAGE = TOKEN_PATH.parent / "drive_service_account.json"
OAUTH_CLIENT_SECRET_STORAGE = TOKEN_PATH.parent / "drive_oauth_client_secret.json"


def _get_redirect_uri(client_path: str) -> str:
    try:
        data = json.loads(Path(client_path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("No se pudo leer el JSON del client secret.") from exc
    installed = data.get("installed") or data.get("web")
    if not isinstance(installed, dict):
        raise RuntimeError("El JSON de OAuth no contiene el bloque 'installed' o 'web'.")
    redirect_uris = installed.get("redirect_uris") or []
    if not redirect_uris:
        raise RuntimeError("El JSON de OAuth no lista 'redirect_uris'.")
    for uri in redirect_uris:
        if "localhost" in uri:
            return uri
    return redirect_uris[0]


def _get_port_from_uri(uri: str) -> int:
    parsed = urlparse(uri)
    return parsed.port or 4853


def _ensure_credentials_dir():
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)


def _copy_to_storage(source: Path, dest: Path) -> Path:
    _ensure_credentials_dir()
    shutil.copy2(str(source), str(dest))
    return dest


def _load_drive_config() -> dict:
    _ensure_credentials_dir()
    if not DRIVE_CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(DRIVE_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data


def _save_drive_config(data: dict):
    _ensure_credentials_dir()
    DRIVE_CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_drive_settings() -> dict:
    return _load_drive_config()


def update_drive_settings(**kwargs) -> dict:
    data = _load_drive_config()
    data.update(kwargs)
    _save_drive_config(data)
    return data


def get_drive_folder_id() -> str | None:
    settings = load_drive_settings()
    return settings.get("drive_folder_id")


def set_drive_folder_id(folder_id: str | None) -> str:
    value = (folder_id or "").strip()
    settings = load_drive_settings()
    if settings.get("drive_folder_id") == value:
        return value
    settings["drive_folder_id"] = value
    _save_drive_config(settings)
    return value


def set_service_account_json(path: str) -> str:
    if not path:
        raise ValueError("La ruta al JSON no puede estar vacía.")
    normalized = Path(path).expanduser().resolve()
    if not normalized.exists():
        raise FileNotFoundError(f"No existe el archivo JSON: {normalized}")
    stored = _copy_to_storage(normalized, SERVICE_ACCOUNT_STORAGE)
    try:
        validate_service_account(stored)
    except Exception:
        try:
            stored.unlink(missing_ok=True)
        except Exception:
            pass
        raise
    os.environ[SERVICE_ACCOUNT_ENV] = str(stored)
    update_drive_settings(service_json=str(stored))
    return str(stored)


def get_service_account_json() -> str | None:
    value = os.getenv(SERVICE_ACCOUNT_ENV, "").strip()
    if value:
        return value
    settings = load_drive_settings()
    stored = settings.get("service_json")
    if stored and Path(stored).exists():
        os.environ[SERVICE_ACCOUNT_ENV] = stored
        return stored
    return None


def validate_service_account(path: str) -> None:
    normalized = Path(path).expanduser().resolve()
    if not normalized.exists():
        raise FileNotFoundError(f"No existe el archivo JSON: {normalized}")
    service_account.Credentials.from_service_account_file(str(normalized))


def set_oauth_client_secret(path: str) -> str:
    if not path:
        raise ValueError("La ruta al JSON no puede estar vacía.")
    normalized = Path(path).expanduser().resolve()
    if not normalized.exists():
        raise FileNotFoundError(f"No existe el archivo JSON: {normalized}")
    stored = _copy_to_storage(normalized, OAUTH_CLIENT_SECRET_STORAGE)
    os.environ[OAUTH_CLIENT_ENV] = str(stored)
    update_drive_settings(oauth_client_secret=str(stored))
    return str(stored)


def get_oauth_client_secret() -> str | None:
    value = os.getenv(OAUTH_CLIENT_ENV, "").strip()
    if value:
        return value
    settings = load_drive_settings()
    stored = settings.get("oauth_client_secret")
    if stored and Path(stored).exists():
        os.environ[OAUTH_CLIENT_ENV] = stored
        return stored
    return None


def _save_oauth_credentials(creds: Credentials):
    _ensure_credentials_dir()
    creds_data = creds.to_json()
    TOKEN_PATH.write_text(creds_data, encoding="utf-8")


def _load_oauth_credentials() -> Credentials | None:
    if not TOKEN_PATH.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_oauth_credentials(creds)
    return creds if creds and creds.valid else None


def load_oauth_credentials() -> Credentials | None:
    creds = _load_oauth_credentials()
    if creds:
        return creds
    return None


def run_oauth_flow(log_fn=None) -> Credentials:
    client_path = get_oauth_client_secret()
    if not client_path:
        raise RuntimeError("No se ha seleccionado el JSON de cliente OAuth.")
    redirect_uri = _get_redirect_uri(client_path)
    flow = InstalledAppFlow.from_client_secrets_file(client_path, SCOPES, redirect_uri=redirect_uri)
    if log_fn:
        log_fn("Abriendo navegador para autorizar Google Drive...")
    port = _get_port_from_uri(redirect_uri)
    try:
        creds = flow.run_local_server(port=port, open_browser=True, prompt="consent")
    except OSError as exc:
        raise RuntimeError(f"No se pudo abrir el servidor local en el puerto {port}: {exc}") from exc
    _save_oauth_credentials(creds)
    if log_fn:
        log_fn("Token de Drive almacenado.")
    return creds
