"""日本語版Briefs生成パイプライン: 取得 -> レコメンド -> 台本生成 -> 音声合成 -> フィード更新。

使い方:
    python -m briefs.pipeline generate --top-n 5
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config
from .alphaxiv_client import card_to_paper, get_feed, get_japanese_overview_text
from .arxiv_client import Paper, fetch_recent_papers
from .export import sync_to_folder
from .profile import Profile
from .recommend import rank_papers
from .script_writer import condense_overview_to_script, write_script
from .trending import fetch_trending_papers
from .tts_voicevox import synthesize


def _load_feed() -> list[dict]:
    if config.FEED_PATH.exists():
        return json.loads(config.FEED_PATH.read_text(encoding="utf-8"))
    return []


def _save_feed(items: list[dict]) -> None:
    config.FEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.FEED_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def generate(
    top_n: int,
    max_fetch: int,
    categories: list[str] | None,
    source: str = "arxiv",
) -> None:
    profile = Profile.load()

    if source == "alphaxiv":
        print("[1/4] alphaXivのおすすめフィードを取得中...", file=sys.stderr)
        cards = get_feed(limit=max_fetch)
        candidates: list[Paper] = [card_to_paper(c) for c in cards]
    elif source == "trending":
        print("[1/4] Hugging Face Daily Papersからトレンド取得中...", file=sys.stderr)
        candidates = fetch_trending_papers(limit=max_fetch)
    else:
        cats = categories or config.ARXIV_CATEGORIES
        print(f"[1/4] arXiv取得中... categories={cats}", file=sys.stderr)
        candidates = fetch_recent_papers(cats, max_results=max_fetch)

    print("[2/4] レコメンドをランキング中...", file=sys.stderr)
    top_papers = rank_papers(candidates, profile, top_n=top_n)
    if not top_papers:
        print("新着かつ未読の論文がありませんでした。", file=sys.stderr)
        return

    feed = _load_feed()
    for i, paper in enumerate(top_papers, start=1):
        print(
            f"[3/4] ({i}/{len(top_papers)}) 台本生成中: {paper.title[:40]}...",
            file=sys.stderr,
        )
        overview_text = get_japanese_overview_text(paper) if source == "alphaxiv" else None
        if overview_text:
            print("      alphaXivの日本語概要を音声用に要約します", file=sys.stderr)
            script = condense_overview_to_script(paper.title, overview_text)
        else:
            script = write_script(paper)

        print(f"[4/4] ({i}/{len(top_papers)}) 音声合成中...", file=sys.stderr)
        audio_path = config.AUDIO_DIR / f"{paper.arxiv_id}.wav"
        synthesize(script, audio_path)

        if config.SYNC_DIR:
            print(f"      クラウド同期フォルダへコピー中: {config.SYNC_DIR}", file=sys.stderr)
            sync_to_folder(audio_path, title=paper.title, authors=paper.authors)

        feed.insert(
            0,
            {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "script": script,
                "abs_url": paper.abs_url,
                "audio_url": f"/audio/{audio_path.name}",
                "published": paper.published,
            },
        )
        profile.mark_seen(paper.arxiv_id)

    profile.save()
    _save_feed(feed)
    print(f"完了: {len(top_papers)}件をフィードに追加しました。", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="日本語版Briefs生成パイプライン")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="新しいBriefsを生成してフィードに追加する")
    gen.add_argument("--top-n", type=int, default=5, help="生成する件数")
    gen.add_argument("--max-fetch", type=int, default=50, help="arXivから取得する候補数")
    gen.add_argument(
        "--categories",
        type=str,
        default=None,
        help="カンマ区切りのarXivカテゴリ（省略時は設定ファイルの値を使用。--source=trending時は無視）",
    )
    gen.add_argument(
        "--source",
        choices=["alphaxiv", "arxiv", "trending"],
        default="alphaxiv",
        help=(
            "論文の取得元。alphaxiv=alphaXiv公式APIのおすすめフィード（要ALPHAXIV_API_KEY）、"
            "arxiv=カテゴリ新着順、trending=Hugging Face Daily Papers"
        ),
    )

    args = parser.parse_args()
    if args.command == "generate":
        cats = args.categories.split(",") if args.categories else None
        generate(
            top_n=args.top_n,
            max_fetch=args.max_fetch,
            categories=cats,
            source=args.source,
        )


if __name__ == "__main__":
    main()
