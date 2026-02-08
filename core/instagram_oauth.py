import secrets
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from core.instagram_auth import exchange_long_lived_token


def _now() -> int:
    return int(time.time())


def build_auth_url(app_id: str, redirect_uri: str, scopes: str, state: str, api_version: str = "v19.0") -> str:
    params = {
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "state": state,
        "scope": scopes,
    }
    return f"https://www.facebook.com/{api_version}/dialog/oauth?" + urllib.parse.urlencode(params)


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
            "<html><body><h3>Autorización recibida</h3>"
            "<p>Ya puedes cerrar esta ventana.</p></body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):
        return


def wait_for_oauth_code(
    redirect_uri: str,
    expected_state: str,
    timeout_sec: int = 300,
    listen_host: str | None = None,
    listen_port: int | None = None,
) -> str:
    parsed = urllib.parse.urlparse(redirect_uri)
    host = listen_host or (parsed.hostname or "127.0.0.1")
    port = listen_port or (parsed.port or 80)
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
    raise TimeoutError("Timeout esperando autorización OAuth.")


def exchange_code_for_token(
    *,
    code: str,
    app_id: str,
    app_secret: str,
    redirect_uri: str,
    api_version: str = "v19.0",
) -> dict:
    url = f"https://graph.facebook.com/{api_version}/oauth/access_token"
    params = {
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
        "code": code.strip(),
    }
    resp = requests.get(url, params=params, timeout=30)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Respuesta no JSON ({resp.status_code}): {resp.text[:200]}")
    if resp.status_code >= 400 or "access_token" not in data:
        raise RuntimeError(f"Error intercambiando code por token: {data}")
    data["created_at"] = _now()
    return data


def oauth_login_flow(
    *,
    app_id: str,
    app_secret: str,
    redirect_uri: str,
    scopes: str,
    api_version: str = "v19.0",
    log_fn=None,
    timeout_sec: int = 300,
    listen_host: str | None = None,
    listen_port: int | None = None,
) -> dict:
    state = secrets.token_urlsafe(16)
    auth_url = build_auth_url(app_id, redirect_uri, scopes, state, api_version=api_version)
    if log_fn:
        log_fn("Abriendo navegador para autorizar Facebook/Instagram...")
    webbrowser.open(auth_url)
    code = wait_for_oauth_code(
        redirect_uri,
        state,
        timeout_sec=timeout_sec,
        listen_host=listen_host,
        listen_port=listen_port,
    )
    if log_fn:
        log_fn("Código OAuth recibido. Intercambiando por token...")
    short = exchange_code_for_token(
        code=code,
        app_id=app_id,
        app_secret=app_secret,
        redirect_uri=redirect_uri,
        api_version=api_version,
    )
    if log_fn:
        log_fn("Convirtiendo a token de larga duración...")
    long_data = exchange_long_lived_token(
        short_lived_token=short.get("access_token"),
        app_id=app_id,
        app_secret=app_secret,
        api_version=api_version,
    )
    return {
        "access_token": long_data.get("access_token"),
        "expires_in": long_data.get("expires_in"),
        "expires_at": long_data.get("expires_at"),
        "created_at": long_data.get("created_at"),
    }
