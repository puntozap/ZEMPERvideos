from __future__ import annotations

from datetime import date, datetime, timedelta
import re
from typing import Any

import requests
from requests.exceptions import HTTPError, ReadTimeout, RequestException

from core.api_endpoints import get_primary_endpoint_url
from core.youtube_upload import obtener_token_activo

YOUTUBE_API_BASE = get_primary_endpoint_url("YouTube Data")
YOUTUBE_ANALYTICS_BASE = get_primary_endpoint_url("YouTube Analytics")

# Query endpoints (declared in core/api_endpoints.py)
YOUTUBE_CHANNELS_URL = get_primary_endpoint_url("YouTube Data channels")
YOUTUBE_PLAYLIST_ITEMS_URL = get_primary_endpoint_url("YouTube Data playlistItems")
YOUTUBE_VIDEOS_URL = get_primary_endpoint_url("YouTube Data videos")
YOUTUBE_COMMENT_THREADS_URL = get_primary_endpoint_url("YouTube Data commentThreads")
YOUTUBE_ANALYTICS_REPORTS_URL = get_primary_endpoint_url("YouTube Analytics reports")
DEFAULT_ANALYTICS_METRICS = ("views", "estimatedMinutesWatched", "averageViewDuration")
YOUTUBE_REQUEST_TIMEOUT = (10, 90)
YOUTUBE_MAX_RETRIES = 2


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
    last_exc: Exception | None = None
    for attempt in range(1, YOUTUBE_MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=YOUTUBE_REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except ReadTimeout as exc:
            last_exc = exc
            if log_fn:
                log_fn(f"Timeout en YouTube Analytics (intento {attempt}/{YOUTUBE_MAX_RETRIES}).")
            if attempt >= YOUTUBE_MAX_RETRIES:
                raise
            continue
        except RequestException as exc:
            raise
    raise last_exc  # pragma: no cover


def _to_iso_date(value: str | date | datetime | None) -> str | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text if text else None


def _parse_video_dimension(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value)
    if "==" in text:
        return text.split("==", 1)[1]
    return text


def listar_videos_subidos(max_results: int = 25, *, only_public: bool = False, log_fn=None) -> list[dict[str, Any]]:
    """
    Lista videos del playlist "uploads" del canal autenticado.

    - `max_results`: cantidad a devolver. Si <= 0, intenta traer todos (paginando).
    - `only_public`: filtra por `privacyStatus == public`.
    """
    limit = int(max_results)
    fetch_all = limit <= 0
    if fetch_all:
        # guardrail: YouTube uploads playlist can be huge; keep it large but bounded.
        limit = 5000

    channels = _request(YOUTUBE_CHANNELS_URL, {"part": "contentDetails", "mine": True}, log_fn=log_fn)
    items = channels.get("items") or []
    if not items:
        raise RuntimeError("No se encontró ningún canal activo.")
    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids: list[str] = []
    page_token: str | None = None
    while len(video_ids) < limit:
        batch = min(50, limit - len(video_ids))
        params: dict[str, Any] = {"part": "snippet", "playlistId": uploads_id, "maxResults": batch}
        if page_token:
            params["pageToken"] = page_token
        playlist_items = _request(YOUTUBE_PLAYLIST_ITEMS_URL, params, log_fn=log_fn)
        for item in playlist_items.get("items", []) or []:
            vid = (((item.get("snippet") or {}).get("resourceId") or {}).get("videoId")) or None
            if vid:
                video_ids.append(str(vid))
                if len(video_ids) >= limit:
                    break
        page_token = playlist_items.get("nextPageToken")
        if not page_token:
            break

    if not video_ids:
        return []

    # Fetch video details in batches of 50 (API limit).
    assets: list[dict[str, Any]] = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        videos = _request(
            YOUTUBE_VIDEOS_URL,
            {"part": "snippet,contentDetails,status", "id": ",".join(chunk)},
            log_fn=log_fn,
        )
        for video in videos.get("items", []) or []:
            privacy = (video.get("status", {}) or {}).get("privacyStatus") or ""
            if only_public and privacy != "public":
                continue
            duration_seconds = _parse_duration(video.get("contentDetails", {}).get("duration", ""))
            assets.append(
                {
                    "video_id": video.get("id"),
                    "title": video.get("snippet", {}).get("title", ""),
                    "duration_seconds": duration_seconds,
                    "duration_formatted": f"{int(duration_seconds // 60):02d}:{int(duration_seconds % 60):02d}",
                    "is_short": duration_seconds <= 60,
                    "published_at": video.get("snippet", {}).get("publishedAt"),
                    "privacy_status": privacy,
                }
            )

    return assets


def obtener_analitica_videos(
    *,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    ids: str = "channel==MINE",
    metrics: tuple[str, ...] = DEFAULT_ANALYTICS_METRICS,
    dimension: str = "video",
    filters: str | None = None,
    max_results: int = 50,
    sort: str = "-views",
    log_fn=None,
) -> list[dict[str, Any]]:
    """
    Llama al endpoint de YouTube Analytics Reports y devuelve cada fila como dict.
    """
    if not metrics:
        raise ValueError("Debe especificarse al menos una métrica para el reporte.")
    today = date.today()
    params = {
        "startDate": _to_iso_date(start_date) or (today - timedelta(days=30)).isoformat(),
        "endDate": _to_iso_date(end_date) or today.isoformat(),
        "ids": ids,
        "metrics": ",".join(metrics),
        "dimensions": dimension,
        "maxResults": max_results,
        "sort": sort,
    }
    if filters:
        params["filters"] = filters
    response = _request(YOUTUBE_ANALYTICS_REPORTS_URL, params, log_fn=log_fn)
    headers = response.get("columnHeaders") or []
    rows = response.get("rows") or []
    column_names = [
        header.get("name") or f"column_{idx}"
        for idx, header in enumerate(headers)
    ]
    return [dict(zip(column_names, row)) for row in rows]


def obtener_analitica_videos_y_shorts(
    *,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    metrics: tuple[str, ...] | None = None,
    max_results: int = 50,
    filters: str | None = None,
    log_fn=None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Devuelve una estructura con los datos analíticos de los videos subidos,
    separando en listas para shorts (<=60s) y videos largos.
    """
    all_metrics = metrics or DEFAULT_ANALYTICS_METRICS
    analytics_rows = obtener_analitica_videos(
        start_date=start_date,
        end_date=end_date,
        metrics=all_metrics,
        filters=filters,
        max_results=max_results,
        log_fn=log_fn,
    )
    uploads = listar_videos_subidos(max_results=max_results, log_fn=log_fn)
    lookup = {asset["video_id"]: asset for asset in uploads}
    enriched: list[dict[str, Any]] = []
    for row in analytics_rows:
        video_id = _parse_video_dimension(row.get("video"))
        asset = lookup.get(video_id)
        duration = asset["duration_seconds"] if asset else None
        enriched_row = {
            **row,
            "video_id": video_id,
            "video_title": asset["title"] if asset else row.get("videoTitle"),
            "duration_seconds": duration,
            "is_short": isinstance(duration, (int, float)) and duration <= 60,
        }
        enriched.append(enriched_row)
    return {
        "all": enriched,
        "shorts": [row for row in enriched if row.get("is_short")],
        "videos": [row for row in enriched if not row.get("is_short")],
    }


def obtener_estadisticas_video(video_id: str, log_fn=None) -> dict[str, Any]:
    """
    Obtiene estadísticas básicas del video mediante YouTube Data API.

    Devuelve: title, published_at, view_count, like_count, comment_count.
    """
    video_id = (video_id or "").strip()
    if not video_id:
        raise ValueError("video_id requerido.")
    payload = _request(
        YOUTUBE_VIDEOS_URL,
        {"part": "snippet,statistics", "id": video_id},
        log_fn=log_fn,
    )
    items = payload.get("items") or []
    if not items:
        raise RuntimeError("Video no encontrado en YouTube Data API.")
    video = items[0]
    snippet = video.get("snippet") or {}
    stats = video.get("statistics") or {}

    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    return {
        "video_id": video_id,
        "title": snippet.get("title") or "",
        "published_at": snippet.get("publishedAt"),
        "view_count": _to_int(stats.get("viewCount")),
        "like_count": _to_int(stats.get("likeCount")),
        "comment_count": _to_int(stats.get("commentCount")),
    }


def obtener_vistas_por_pais(
    *,
    video_id: str,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    ids: str = "channel==MINE",
    max_results: int = 10,
    log_fn=None,
) -> list[dict[str, Any]]:
    """
    Reporte de Analytics: vistas por país para un video.
    """
    video_id = (video_id or "").strip()
    if not video_id:
        raise ValueError("video_id requerido.")
    today = date.today()
    params = {
        "startDate": _to_iso_date(start_date) or (today - timedelta(days=30)).isoformat(),
        "endDate": _to_iso_date(end_date) or today.isoformat(),
        "ids": ids,
        "metrics": "views",
        "dimensions": "country",
        "filters": f"video=={video_id}",
        "maxResults": max_results,
        "sort": "-views",
    }
    response = _request(YOUTUBE_ANALYTICS_REPORTS_URL, params, log_fn=log_fn)
    rows = response.get("rows") or []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        out.append({"country": row[0], "views": row[1]})
    return out


def listar_comentarios_video(
    *,
    video_id: str,
    max_results: int = 20,
    order: str = "time",
    include_replies: bool = False,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    log_fn=None,
) -> list[dict[str, Any]]:
    """
    Lista comentarios (top-level) de un video (YouTube Data API).

    Limitaciones:
    - Si los comentarios están deshabilitados, la API devuelve error.
    - No incluye comentarios "held for review" / moderados.
    - Por defecto devuelve solo top-level; `include_replies=True` añade respuestas cuando existan.
    """
    video_id = (video_id or "").strip()
    if not video_id:
        raise ValueError("video_id requerido.")
    limit = int(max_results)
    if limit <= 0:
        # "Todos" con guardrail para evitar UI/requests infinitos.
        limit = 5000
    else:
        limit = min(limit, 5000)

    results: list[dict[str, Any]] = []
    page_token: str | None = None
    part = "snippet,replies" if include_replies else "snippet"

    def _extract_comment(comment: dict[str, Any]) -> dict[str, Any]:
        snippet = comment.get("snippet") or {}
        return {
            "comment_id": comment.get("id"),
            "author": snippet.get("authorDisplayName") or "",
            "text": snippet.get("textDisplay") or snippet.get("textOriginal") or "",
            "like_count": snippet.get("likeCount") or 0,
            "published_at": snippet.get("publishedAt"),
            "updated_at": snippet.get("updatedAt"),
        }

    start_iso = _to_iso_date(start_date)
    end_iso = _to_iso_date(end_date)
    start_cut = date.fromisoformat(start_iso) if start_iso else None
    end_cut = date.fromisoformat(end_iso) if end_iso else None

    def _published_date(value: Any) -> date | None:
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        # Typical: 2026-02-03T12:34:56Z
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            return datetime.fromisoformat(text).date()
        except Exception:
            try:
                return date.fromisoformat(text[:10])
            except Exception:
                return None

    while len(results) < limit:
        batch = min(100, limit - len(results))
        params: dict[str, Any] = {
            "part": part,
            "videoId": video_id,
            "maxResults": batch,
            "order": order,
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token
        payload = _request(YOUTUBE_COMMENT_THREADS_URL, params, log_fn=log_fn)
        stop_early = False
        for item in payload.get("items") or []:
            top = (((item.get("snippet") or {}).get("topLevelComment")) or {})
            if top:
                entry = _extract_comment(top)
                published = _published_date(entry.get("published_at"))
                if start_cut and published and published < start_cut:
                    stop_early = True
                if (start_cut and published and published < start_cut) or (end_cut and published and published > end_cut):
                    pass
                else:
                    results.append(entry)
                if len(results) >= limit:
                    break
            if include_replies:
                replies = ((item.get("replies") or {}).get("comments")) or []
                for reply in replies:
                    entry = _extract_comment(reply)
                    published = _published_date(entry.get("published_at"))
                    if start_cut and published and published < start_cut:
                        stop_early = True
                    if (start_cut and published and published < start_cut) or (end_cut and published and published > end_cut):
                        continue
                    results.append(entry)
                    if len(results) >= limit:
                        break
        if stop_early and order == "time":
            break
        page_token = payload.get("nextPageToken")
        if not page_token:
            break
    return results


def obtener_videos_mas_comentados(
    *,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    ids: str = "channel==MINE",
    max_results: int = 50,
    only_public: bool = True,
    log_fn=None,
) -> list[dict[str, Any]]:
    """
    Devuelve una lista de videos ordenados por cantidad de comentarios (periodo filtrado por fecha),
    del más comentado al menos comentado.

    Nota: requiere YouTube Analytics scope. El campo `comments_period` es la métrica del rango.
    """
    limit = int(max_results)
    return_all = limit <= 0
    if return_all:
        limit = 5000
    limit = min(limit, 5000)

    try:
        rows = obtener_analitica_videos(
            start_date=start_date,
            end_date=end_date,
            ids=ids,
            metrics=("comments",),
            dimension="video",
            max_results=limit,
            sort="-comments",
            log_fn=log_fn,
        )
    except HTTPError as exc:
        # Some channels/projects can't query "comments" via Analytics reports (400).
        # Fall back to lifetime commentCount via Data API so the UI can still rank content.
        if log_fn:
            log_fn(f"Analytics no devolvió métrica 'comments' (usando commentCount total). Detalle: {exc}")
        # For ranking we must consider the whole library, not just the first page.
        # We fetch all uploads (guardrailed inside) and then slice after sorting.
        videos = listar_videos_subidos(max_results=0, only_public=only_public, log_fn=log_fn)
        if not videos:
            return []
        ids_list = [str(v.get("video_id") or "") for v in videos if v.get("video_id")]
        comment_counts: dict[str, int] = {}
        for i in range(0, len(ids_list), 50):
            chunk = ids_list[i : i + 50]
            payload = _request(
                YOUTUBE_VIDEOS_URL,
                {"part": "statistics", "id": ",".join(chunk)},
                log_fn=log_fn,
            )
            for item in payload.get("items", []) or []:
                vid = item.get("id")
                if not vid:
                    continue
                try:
                    comment_counts[str(vid)] = int((item.get("statistics") or {}).get("commentCount") or 0)
                except Exception:
                    comment_counts[str(vid)] = 0
        ranked: list[dict[str, Any]] = []
        for v in videos:
            vid = str(v.get("video_id") or "")
            total = comment_counts.get(vid, 0)
            if total <= 0:
                continue
            ranked.append({**v, "comments_total": total})
        ranked.sort(key=lambda r: int(r.get("comments_total") or 0), reverse=True)
        if return_all:
            return ranked
        return ranked[:limit]
    items: list[dict[str, Any]] = []
    video_ids: list[str] = []
    for row in rows:
        vid = _parse_video_dimension(row.get("video"))
        if not vid:
            continue
        try:
            count = int(row.get("comments") or 0)
        except Exception:
            count = 0
        if count <= 0:
            continue
        items.append({"video_id": vid, "comments_period": count})
        video_ids.append(vid)

    if not video_ids:
        return []

    # Fetch title/duration/privacy in batches using Data API.
    meta: dict[str, dict[str, Any]] = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        payload = _request(
            YOUTUBE_VIDEOS_URL,
            {"part": "snippet,contentDetails,status", "id": ",".join(chunk)},
            log_fn=log_fn,
        )
        for video in payload.get("items", []) or []:
            vid = video.get("id")
            if not vid:
                continue
            privacy = (video.get("status", {}) or {}).get("privacyStatus") or ""
            duration_seconds = _parse_duration(video.get("contentDetails", {}).get("duration", ""))
            meta[str(vid)] = {
                "title": video.get("snippet", {}).get("title", "") or "",
                "published_at": video.get("snippet", {}).get("publishedAt"),
                "duration_seconds": duration_seconds,
                "duration_formatted": f"{int(duration_seconds // 60):02d}:{int(duration_seconds % 60):02d}",
                "is_short": duration_seconds <= 60,
                "privacy_status": privacy,
            }

    out: list[dict[str, Any]] = []
    for item in items:
        vid = item["video_id"]
        info = meta.get(vid) or {}
        privacy = info.get("privacy_status") or ""
        if only_public and privacy and privacy != "public":
            continue
        out.append({**item, **info})

    out.sort(key=lambda r: int(r.get("comments_period") or 0), reverse=True)
    return out
