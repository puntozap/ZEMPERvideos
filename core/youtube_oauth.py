from __future__ import annotations

import urllib.parse

import requests

from core.api_endpoints import get_primary_endpoint_url

TOKEN_URL = get_primary_endpoint_url("YouTube token refresh")
AUTH_BASE_URL = get_primary_endpoint_url("YouTube OAuth")


def build_oauth_url(client_id: str, redirect_uri: str, scopes: list[str]) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict[str, str]:
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if "refresh_token" not in payload:
        raise ValueError("Google no devolvió refresh_token; asegúrate de usar access_type=offline.")
    return {
        "access_token": payload["access_token"],
        "refresh_token": payload["refresh_token"],
        "token_uri": payload.get("token_uri", TOKEN_URL),
    }
