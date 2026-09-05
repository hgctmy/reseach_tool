"""Hugging Face Daily Papers（コミュニティの注目度でキュレーションされた論文一覧）から
トレンド論文を取得する。認証不要の公開APIを使用。

参考: https://huggingface.co/papers （このAPIはHugging Face公式フロントエンドが
内部的に使用している非公式に文書化されたエンドポイント。レスポンス構造が変わった
場合はこのモジュールの調整が必要になる可能性があります）。
"""
from __future__ import annotations

import datetime as dt

import requests

from .arxiv_client import Paper

DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


def fetch_trending_papers(date: str | None = None, limit: int = 30) -> list[Paper]:
    """指定日（省略時は今日、UTC）のHugging Face Daily Papersを取得する。"""
    target_date = date or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    resp = requests.get(
        DAILY_PAPERS_URL, params={"date": target_date, "limit": limit}, timeout=30
    )
    resp.raise_for_status()
    items = resp.json()

    papers: list[Paper] = []
    for item in items:
        paper = item.get("paper", item)
        arxiv_id = paper.get("id", "")
        if not arxiv_id:
            continue
        authors = [a.get("name", "") for a in paper.get("authors", []) if a.get("name")]
        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=paper.get("title", item.get("title", "")),
                abstract=paper.get("summary", ""),
                authors=authors,
                categories=[],
                published=paper.get("publishedAt", item.get("publishedAt", "")),
                pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
            )
        )
    return papers
