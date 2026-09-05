"""日本語版Briefsのフィードを配信するローカルWebサーバー。

起動:
    uvicorn briefs.app:app --reload
"""
from __future__ import annotations

import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .profile import Profile

app = FastAPI(title="日本語版Briefs")
app.mount("/audio", StaticFiles(directory=str(config.AUDIO_DIR)), name="audio")


class FeedbackRequest(BaseModel):
    arxiv_id: str
    action: str  # "like" | "skip"


def _load_feed() -> list[dict]:
    if not config.FEED_PATH.exists():
        return []
    return json.loads(config.FEED_PATH.read_text(encoding="utf-8"))


def _find_item(feed: list[dict], arxiv_id: str) -> dict | None:
    return next((item for item in feed if item["arxiv_id"] == arxiv_id), None)


@app.get("/api/feed")
def get_feed() -> list[dict]:
    return _load_feed()


@app.post("/api/feedback")
def post_feedback(payload: FeedbackRequest) -> dict:
    if payload.action not in ("like", "skip"):
        raise HTTPException(status_code=400, detail="actionはlikeまたはskipを指定してください")

    feed = _load_feed()
    item = _find_item(feed, payload.arxiv_id)
    if item is None:
        raise HTTPException(status_code=404, detail="指定されたarxiv_idがフィードに見つかりません")

    profile = Profile.load()
    if payload.action == "like":
        profile.mark_liked(payload.arxiv_id, item["abstract"])
    else:
        profile.mark_skipped(payload.arxiv_id)

    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    web_dir = config.BASE_DIR / "web"
    return FileResponse(web_dir / "index.html")
