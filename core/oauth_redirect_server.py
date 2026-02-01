from __future__ import annotations

import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

REDIRECT_PORT = 4850
CALLBACK_FILE = Path("credentials/oauth_callback.json")


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        code = query.get("code", [None])[0]
        data = {
            "code": code,
            "timestamp": datetime.utcnow().isoformat(),
            "raw_path": self.path,
        }
        if code:
            CALLBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            CALLBACK_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = "<html><body><h2>La autorización fue capturada.</h2><p>Regresa a la app.</p></body></html>"
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, fmt: str, *args: object) -> None:
        return


def start_redirect_server(port: int = REDIRECT_PORT) -> HTTPServer:
    server = HTTPServer(("localhost", port), _OAuthCallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def stop_redirect_server(server: HTTPServer) -> None:
    server.shutdown()
    server.server_close()


if __name__ == "__main__":
    srv = start_redirect_server()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        stop_redirect_server(srv)
