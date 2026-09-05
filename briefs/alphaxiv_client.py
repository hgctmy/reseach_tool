"""alphaXiv公式API (api.alphaxiv.org) のうすいラッパー。

alphaXivのフィード（Briefs/おすすめの元になっているのと同じホームページフィード）
と、論文のAI概要（Overview/Blog。日本語への翻訳に対応）を取得する。

エンドポイント仕様は非公式ドキュメント
(https://github.com/petroslamb/alphaxiv-py の docs/api-inventory.md) に基づく。
alphaXiv側の仕様変更やレスポンス構造の細部（フィールド名など）は公式に文書化
されていないため、想定と異なる場合はこのモジュールの調整が必要になる可能性が
あります。

認証: Settings > API Keys で発行したAPIキーを ALPHAXIV_API_KEY 環境変数に設定する。
フィード取得・概要取得はpublicエンドポイントだが、AI概要の生成リクエスト
(request-ai) には認証が必要。
"""
from __future__ import annotations

import time

import requests

from . import config
from .arxiv_client import Paper


class AlphaXivAPIError(RuntimeError):
    pass


def _headers(api_key: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    key = api_key or config.ALPHAXIV_API_KEY
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _get(path: str, api_key: str | None = None, **params) -> dict | list:
    url = f"{config.ALPHAXIV_BASE_URL}{path}"
    resp = requests.get(url, headers=_headers(api_key), params=params, timeout=30)
    if resp.status_code == 401:
        raise AlphaXivAPIError(
            "alphaXiv APIの認証に失敗しました。ALPHAXIV_API_KEYを確認してください。"
        )
    resp.raise_for_status()
    return resp.json()


def get_feed(sort: str | None = None, limit: int = 30, api_key: str | None = None) -> list[dict]:
    """ホームページのフィードカード一覧を取得する（Briefsの元になっている推薦フィード）。"""
    data = _get(
        "/papers/v3/feed",
        api_key=api_key,
        sort=sort or config.ALPHAXIV_FEED_SORT,
        limit=limit,
    )
    if isinstance(data, dict):
        # レスポンスが {"cards": [...]} 等でラップされている場合に対応
        for key in ("cards", "items", "results", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        return []
    return data


def _first(card: dict, *keys: str, default=""):
    for key in keys:
        if key in card and card[key] not in (None, ""):
            return card[key]
    return default


def card_to_paper(card: dict) -> Paper:
    """フィードのカード1件をPaperに変換する（フィールド名が複数候補ある場合は総当たりで探す）。"""
    paper_obj = card.get("paper", card)
    arxiv_id = _first(paper_obj, "arxivId", "arxiv_id", "canonicalId", "id")
    version_id = _first(paper_obj, "paperVersionId", "versionId", "id", default=arxiv_id)
    authors_raw = paper_obj.get("authors", [])
    authors = [a.get("name", a) if isinstance(a, dict) else str(a) for a in authors_raw]
    return Paper(
        arxiv_id=arxiv_id,
        title=_first(paper_obj, "title"),
        abstract=_first(paper_obj, "abstract", "summary"),
        authors=authors,
        categories=paper_obj.get("categories", []),
        published=_first(paper_obj, "publishedAt", "published"),
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
        alphaxiv_version_id=version_id,
    )


def get_overview_status(paper_version_id: str, api_key: str | None = None) -> dict:
    return _get(f"/papers/v3/{paper_version_id}/overview/status", api_key=api_key)


def get_overview(paper_version_id: str, lang: str | None = None, api_key: str | None = None) -> dict:
    lang = lang or config.ALPHAXIV_OVERVIEW_LANG
    return _get(f"/papers/v3/{paper_version_id}/overview/{lang}", api_key=api_key)


def request_ai_overview(
    arxiv_id: str,
    version: int = 1,
    preferred_language: str | None = None,
    api_key: str | None = None,
) -> None:
    url = f"{config.ALPHAXIV_BASE_URL}/v2/papers/{arxiv_id}/versions/{version}/request-ai"
    resp = requests.post(
        url,
        headers=_headers(api_key),
        params={"preferredLanguage": preferred_language or config.ALPHAXIV_OVERVIEW_LANG},
        timeout=30,
    )
    if resp.status_code == 401:
        raise AlphaXivAPIError(
            "AI概要の生成にはAPIキーが必要です。ALPHAXIV_API_KEYを確認してください。"
        )
    resp.raise_for_status()


def _extract_overview_text(payload: dict) -> str:
    for key in ("content", "text", "body", "markdown", "html"):
        if payload.get(key):
            return payload[key]
    return ""


def _is_ready(status_payload: dict, lang: str) -> bool:
    # ステータスのレスポンス構造が不明なため、複数のパターンで「準備完了」を探す
    if status_payload.get("status") in ("ready", "completed", "done"):
        return True
    langs = status_payload.get("availableLanguages") or status_payload.get("languages") or []
    return lang in langs


def get_japanese_overview_text(
    paper: Paper,
    version: int = 1,
    poll_timeout: int | None = None,
    poll_interval: int | None = None,
    api_key: str | None = None,
) -> str | None:
    """alphaXivの日本語AI概要（Overview/Blog）を取得する。

    既に生成済みならそのまま返し、未生成なら生成をリクエストしてポーリングする。
    タイムアウトした場合や取得できない場合はNoneを返す（呼び出し側でフォールバック
    することを想定）。
    """
    if not paper.alphaxiv_version_id:
        return None
    lang = config.ALPHAXIV_OVERVIEW_LANG
    timeout = poll_timeout if poll_timeout is not None else config.ALPHAXIV_OVERVIEW_POLL_TIMEOUT
    interval = (
        poll_interval if poll_interval is not None else config.ALPHAXIV_OVERVIEW_POLL_INTERVAL
    )

    try:
        status = get_overview_status(paper.alphaxiv_version_id, api_key=api_key)
    except (AlphaXivAPIError, requests.RequestException):
        return None

    if not _is_ready(status, lang):
        try:
            request_ai_overview(
                paper.arxiv_id, version=version, preferred_language=lang, api_key=api_key
            )
        except (AlphaXivAPIError, requests.RequestException):
            return None

        waited = 0
        while waited < timeout:
            time.sleep(interval)
            waited += interval
            try:
                status = get_overview_status(paper.alphaxiv_version_id, api_key=api_key)
            except (AlphaXivAPIError, requests.RequestException):
                return None
            if _is_ready(status, lang):
                break
        else:
            return None

    try:
        overview = get_overview(paper.alphaxiv_version_id, lang=lang, api_key=api_key)
    except (AlphaXivAPIError, requests.RequestException):
        return None
    return _extract_overview_text(overview) or None
