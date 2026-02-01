"""
Gestión de archivos JSON con credenciales de YouTube (cliente + refresh token).

El módulo mantiene un directorio dedicado (`credentials/`) y un puntero a la credencial activa.
Permite registrar nuevos archivos (evitando duplicados si ya existen) y cargar el
registro activo de forma coherente.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_DIR = BASE_DIR / "credentials"
_ACTIVE_MARKER = CREDENTIALS_DIR / ".active_credentials"
DEFAULT_SCOPES = ("https://www.googleapis.com/auth/youtube.upload",)
_ALLOWED_EXTENSIONS = {".json"}


@dataclass(frozen=True)
class YouTubeCredentials:
    client_id: str
    client_secret: str
    refresh_token: str
    token_uri: str
    scopes: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict) -> "YouTubeCredentials":
        if not isinstance(data, dict):
            raise ValueError("La información debe ser un diccionario JSON válido.")
        installed = data.get("installed") or data.get("web")
        if not isinstance(installed, dict):
            raise ValueError("El JSON no provee el bloque 'installed' o 'web'.")

        client_id = installed.get("client_id")
        client_secret = installed.get("client_secret")
        token_uri = installed.get("token_uri") or data.get("token_uri")

        refresh_token = (
            data.get("refresh_token")
            or installed.get("refresh_token")
            or installed.get("refreshToken")
        )
        scopes = tuple(data.get("scopes") or installed.get("scopes") or DEFAULT_SCOPES)

        if not client_id or not client_secret or not token_uri or not refresh_token:
            raise ValueError("Faltan campos obligatorios en las credenciales de YouTube.")

        return cls(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            token_uri=token_uri,
            scopes=scopes,
        )


def ensure_credentials_dir() -> None:
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


def available_credentials() -> list[Path]:
    ensure_credentials_dir()
    return sorted(
        [
            candidate
            for candidate in CREDENTIALS_DIR.iterdir()
            if candidate.suffix.lower() in _ALLOWED_EXTENSIONS and candidate.is_file()
        ]
    )


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_active_name() -> Optional[str]:
    if not _ACTIVE_MARKER.exists():
        return None
    try:
        return _ACTIVE_MARKER.read_text(encoding="utf-8").strip()
    except Exception:
        return None


def _write_active_name(name: str) -> None:
    _ACTIVE_MARKER.write_text(name, encoding="utf-8")


def mark_active(path: Path) -> None:
    ensure_credentials_dir()
    relative = path.name
    _write_active_name(relative)


def _validate_credentials(path: Path) -> bool:
    try:
        YouTubeCredentials.from_dict(_load_json(path))
        return True
    except ValueError:
        return False


def find_active_credentials_file() -> Optional[Path]:
    ensure_credentials_dir()
    active_name = _read_active_name()
    if active_name:
        candidate = CREDENTIALS_DIR / active_name
        if candidate.exists() and _validate_credentials(candidate):
            return candidate

    for candidate in available_credentials():
        if _validate_credentials(candidate):
            mark_active(candidate)
            return candidate
    return None


def load_active_credentials() -> YouTubeCredentials:
    candidate = find_active_credentials_file()
    if not candidate:
        raise FileNotFoundError("No se encontró ninguna credencial válida en credentials/.")
    return YouTubeCredentials.from_dict(_load_json(candidate))


def register_credentials(
    source: Path | str,
    *,
    make_active: bool = True,
    prefer_name: Optional[str] = None,
) -> Path:
    ensure_credentials_dir()
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"No existe el archivo {source_path}.")

    if source_path.suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise ValueError("Solo se aceptan archivos con extensión .json en las credenciales.")

    source_hash = _hash(source_path)

    for candidate in available_credentials():
        if _hash(candidate) == source_hash:
            if make_active:
                mark_active(candidate)
            return candidate

    target_name = prefer_name or source_path.name
    target = CREDENTIALS_DIR / target_name
    if target.exists():
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        target = CREDENTIALS_DIR / f"{target.stem}_{timestamp}{target.suffix}"

    shutil.copy2(source_path, target)
    if make_active:
        mark_active(target)
    return target


__all__ = [
    "YouTubeCredentials",
    "available_credentials",
    "find_active_credentials_file",
    "load_active_credentials",
    "mark_active",
    "register_credentials",
    "ensure_credentials_dir",
]
