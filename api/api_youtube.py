from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

from core.youtube_downloader import descargar_video_youtube_mp4


router = APIRouter()


class YouTubeDownloadRequest(BaseModel):
    url: HttpUrl


@router.post("/youtube/download")
def youtube_download(payload: YouTubeDownloadRequest):
    url = str(payload.url)
    try:
        out_path = descargar_video_youtube_mp4(url)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"ok": True, "path": out_path}
