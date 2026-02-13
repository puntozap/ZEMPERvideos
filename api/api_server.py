import os
import sys
from fastapi import FastAPI

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from api.api_youtube import router as youtube_router


app = FastAPI(title="Transcriptor Video API")


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(youtube_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
