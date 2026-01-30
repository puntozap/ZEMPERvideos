import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests


AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INBOX_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
DIRECT_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TOKENS_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output", "tiktok_tokens.json"))


def _now() -> int:
    return int(time.time())


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(32)
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def build_auth_url(
    client_key: str,
    redirect_uri: str,
    scopes: str,
    state: str,
    code_challenge: str | None,
) -> str:
    params = {
        "client_key": client_key,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scopes,
        "state": state,
    }
    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def load_tokens(path: str = TOKENS_PATH) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_tokens(tokens: dict, path: str = TOKENS_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=True)


def token_is_valid(tokens: dict, skew_sec: int = 60) -> bool:
    if not tokens:
        return False
    access_token = tokens.get("access_token")
    expires_in = tokens.get("expires_in")
    created_at = tokens.get("created_at")
    if not access_token or not expires_in or not created_at:
        return False
    return _now() < int(created_at) + int(expires_in) - skew_sec


def _request_json(method: str, url: str, **kwargs) -> dict:
    resp = requests.request(method, url, timeout=30, **kwargs)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Respuesta no JSON ({resp.status_code}): {resp.text[:200]}")
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {data}")
    return data


def exchange_code_for_token(
    client_key: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str | None,
) -> dict:
    payload = {
        "client_key": client_key,
        "client_secret": client_secret,
        "code": code.strip(),
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = _request_json("POST", TOKEN_URL, data=payload, headers=headers)
    token_data = data.get("data", data)
    if "access_token" not in token_data:
        err = token_data.get("error_description") or token_data.get("error") or "Token invalido."
        raise RuntimeError(err)
    token_data["created_at"] = _now()
    return token_data


def refresh_access_token(client_key: str, client_secret: str, refresh_token: str) -> dict:
    payload = {
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    data = _request_json("POST", TOKEN_URL, data=payload)
    token_data = data.get("data", data)
    if "access_token" not in token_data:
        err = token_data.get("error_description") or token_data.get("error") or "Token invalido."
        raise RuntimeError(err)
    token_data["created_at"] = _now()
    return token_data


class _OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        code = qs.get("code", [None])[0]
        state = qs.get("state", [None])[0]
        error = qs.get("error", [None])[0]
        if code or error:
            self.server.oauth_code = code
            self.server.oauth_state = state
            self.server.oauth_error = error
        body = (
            "<html><body><h3>Autorizacion recibida</h3>"
            "<p>Ya puedes cerrar esta ventana.</p></body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        return


def wait_for_oauth_code(redirect_uri: str, expected_state: str, timeout_sec: int = 300) -> str:
    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    server = HTTPServer((host, port), _OAuthHandler)
    server.oauth_code = None
    server.oauth_state = None
    server.oauth_error = None
    server.running = True

    def _serve():
        while server.running:
            server.handle_request()

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()

    start = _now()
    while _now() - start < timeout_sec:
        if server.oauth_error:
            server.running = False
            raise RuntimeError(f"OAuth error: {server.oauth_error}")
        if server.oauth_code:
            if expected_state and server.oauth_state != expected_state:
                server.running = False
                raise RuntimeError(f"State OAuth no coincide. Recibido: {server.oauth_state}, Esperado: {expected_state}")
            server.running = False
            return server.oauth_code
        time.sleep(0.2)
    server.running = False
    raise TimeoutError("Timeout esperando autorizacion OAuth.")


def oauth_login_flow(
    client_key: str,
    client_secret: str,
    redirect_uri: str,
    scopes: str,
    use_pkce: bool = False,
    log_fn=None,
    timeout_sec: int = 300,
) -> dict:
    state = secrets.token_urlsafe(16)
    verifier = None
    challenge = None
    if use_pkce:
        verifier, challenge = make_pkce_pair()
    auth_url = build_auth_url(client_key, redirect_uri, scopes, state, challenge)
    if log_fn:
        log_fn("Abriendo navegador para autorizar TikTok...")
    webbrowser.open(auth_url)
    code = wait_for_oauth_code(redirect_uri, state, timeout_sec=timeout_sec)
    if log_fn:
        log_fn("Codigo OAuth recibido. Intercambiando por token...")
    tokens = exchange_code_for_token(client_key, client_secret, code, redirect_uri, verifier)
    return tokens


def get_valid_access_token(client_key: str, client_secret: str, tokens: dict, log_fn=None) -> dict:
    if not tokens:
        raise RuntimeError("No hay tokens guardados.")
    if token_is_valid(tokens):
        return tokens
    refresh = tokens.get("refresh_token")
    access = tokens.get("access_token")
    if not refresh:
        if access:
            if log_fn:
                log_fn("No hay refresh_token. Usando access_token actual.")
            if not tokens.get("created_at"):
                tokens["created_at"] = _now()
            if not tokens.get("expires_in"):
                tokens["expires_in"] = 3600
            return tokens
        raise RuntimeError("No hay refresh_token para renovar.")
    if log_fn:
        log_fn("Refrescando access_token...")
    new_tokens = refresh_access_token(client_key, client_secret, refresh)
    return new_tokens


def _compute_chunks(file_size: int) -> tuple[int, int]:
    if file_size <= 0:
        raise ValueError("Archivo vacio.")
    max_chunk = 64 * 1024 * 1024
    min_chunk = 5 * 1024 * 1024
    if file_size <= max_chunk:
        chunk_size = file_size
    else:
        chunk_size = max_chunk
    if file_size < min_chunk:
        chunk_size = file_size
    total = (file_size + chunk_size - 1) // chunk_size
    return chunk_size, total


def init_upload_inbox(access_token: str, video_path: str) -> dict:
    size = os.path.getsize(video_path)
    chunk_size, total = _compute_chunks(size)
    payload = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": chunk_size,
            "total_chunk_count": total,
        }
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = _request_json("POST", INBOX_INIT_URL, json=payload, headers=headers)
    return data.get("data", data)


def init_upload_direct(access_token: str, video_path: str, caption: str, privacy: str, disable_comment: bool, disable_duet: bool, disable_stitch: bool) -> dict:
    size = os.path.getsize(video_path)
    chunk_size, total = _compute_chunks(size)
    payload = {
        "post_info": {
            "title": caption or "",
            "privacy_level": privacy,
            "disable_comment": bool(disable_comment),
            "disable_duet": bool(disable_duet),
            "disable_stitch": bool(disable_stitch),
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": chunk_size,
            "total_chunk_count": total,
        },
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    data = _request_json("POST", DIRECT_INIT_URL, json=payload, headers=headers)
    return data.get("data", data)


def upload_video(upload_url: str, video_path: str, log_fn=None) -> None:
    size = os.path.getsize(video_path)
    chunk_size, total = _compute_chunks(size)
    content_type = "video/mp4"
    start = 0
    part = 1
    with open(video_path, "rb") as f:
        while start < size:
            end = min(size - 1, start + chunk_size - 1)
            f.seek(start)
            chunk = f.read(end - start + 1)
            headers = {
                "Content-Type": content_type,
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end}/{size}",
            }
            resp = requests.put(upload_url, data=chunk, headers=headers, timeout=120)
            if resp.status_code >= 400:
                raise RuntimeError(f"Error subiendo chunk {part}/{total}: {resp.status_code} {resp.text[:200]}")
            if log_fn:
                log_fn(f"Chunk {part}/{total} subido.")
            start = end + 1
            part += 1
