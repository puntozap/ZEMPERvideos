import time
import requests


def _now() -> int:
    return int(time.time())


def exchange_long_lived_token(
    *,
    short_lived_token: str,
    app_id: str,
    app_secret: str,
    api_version: str = "v19.0",
) -> dict:
    if not short_lived_token or not app_id or not app_secret:
        raise RuntimeError("Faltan app_id, app_secret o access_token para renovar.")
    url = f"https://graph.facebook.com/{api_version}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token,
    }
    resp = requests.get(url, params=params, timeout=30)
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Respuesta no JSON ({resp.status_code}): {resp.text[:200]}")
    if resp.status_code >= 400 or "access_token" not in data:
        raise RuntimeError(f"Error renovando token: {data}")
    data["created_at"] = _now()
    expires_in = int(data.get("expires_in") or 0)
    if expires_in:
        data["expires_at"] = data["created_at"] + expires_in
    return data


def token_expired(expires_at: int | None, skew_sec: int = 60) -> bool:
    if not expires_at:
        return False
    return _now() >= int(expires_at) - skew_sec
