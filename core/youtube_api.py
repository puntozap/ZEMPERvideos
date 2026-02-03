from __future__ import annotations

import re
from typing import Any

import requests

from core.api_endpoints import get_primary_endpoint_url
from core.youtube_upload import obtener_token_activo

YOUTUBE_API_BASE = get_primary_endpoint_url("YouTube Data")


def _parse_duration(duration: str) -> float:
    pattern = re.compile(r"PT((?P<h>\d+)H)?((?P<m>\d+)M)?((?P<s>\d+)S)?")
    match = pattern.match(duration or "")
    if not match:
        return 0.0
    hours = int(match.group("h") or 0)
    minutes = int(match.group("m") or 0)
    seconds = int(match.group("s") or 0)
    return hours * 3600 + minutes * 60 + seconds


def _request(url: str, params: dict[str, Any], log_fn=None) -> dict[str, Any]:
    token = obtener_token_activo(log_fn=log_fn)
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def listar_videos_subidos(max_results: int = 25, log_fn=None) -> list[dict[str, Any]]:
    if max_results <= 0:
        raise ValueError("max_results debe ser mayor a cero.")
    channels = _request(f"{YOUTUBE_API_BASE}/channels", {"part": "contentDetails", "mine": True}, log_fn=log_fn)
    items = channels.get("items") or []
    if not items:
        raise RuntimeError("No se encontró ningún canal activo.")
    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    playlist_items = _request(
        f"{YOUTUBE_API_BASE}/playlistItems",
        {"part": "snippet", "playlistId": uploads_id, "maxResults": min(max_results, 50)},
        log_fn=log_fn,
    )
    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in playlist_items.get("items", [])]
    if not video_ids:
        return []
    videos = _request(
        f"{YOUTUBE_API_BASE}/videos",
        {"part": "snippet,contentDetails", "id": ",".join(video_ids)},
        log_fn=log_fn,
    )
    assets = []
    for video in videos.get("items", []):
        duration_seconds = _parse_duration(video.get("contentDetails", {}).get("duration", ""))
        assets.append(
            {
                "video_id": video.get("id"),
                "title": video.get("snippet", {}).get("title", ""),
                "duration_seconds": duration_seconds,
                "duration_formatted": f"{int(duration_seconds // 60):02d}:{int(duration_seconds % 60):02d}",
                "is_short": duration_seconds <= 60,
                "published_at": video.get("snippet", {}).get("publishedAt"),
            }
        )
    return assets
