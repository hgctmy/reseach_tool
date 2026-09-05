#!/usr/bin/env python3
"""alphaXivの今日のトレンド/レコメンドフィードを取得し、NotebookLMに一括貼り付け
できるURLリストを出力する。

NotebookLMは2025年8月以降、Add Sources → URL欄にスペース/改行区切りで複数の
URLをまとめて貼り付けられる（1件ずつ登録する必要がない）。このスクリプトは
その貼り付け用テキストを作るだけで、ノートブックの作成やAudio Overviewの
生成自体は手動でNotebookLM上から行う。

使い方:
    python scripts/daily_digest.py
    python scripts/daily_digest.py --sort hot --limit 8
    python scripts/daily_digest.py --full-text   # 要旨ではなくPDF本文まで読ませたい場合
    ALPHAXIV_API_KEY=axv1_... python scripts/daily_digest.py --sort likes

デフォルトはarxiv.org/abs/（要旨ページ）。デイリーニュース的にサッと聞き流す
用途なら要旨だけで十分な上、件数を増やしてもNotebookLMの「per-source sampling」
（ソースが多いと各ソースから読む量が間引かれる）の影響を受けにくい。
1本1本を深掘りしたい場合は`--full-text`でPDF直リンク（本文まで読み込まれる）
に切り替えられる。

--sortに指定できる値は hot / likes / github / twitter / most-stars /
most-twitter-likes のいずれか（alphaXiv側の定義に基づく。trendingのような
値は存在せず400エラーになる）。ALPHAXIV_API_KEYを設定すると、対応していれば
自分のアカウント向けの結果が返る可能性がある（未設定でも動く）。

出力:
    - 標準エラー出力にタイトル付き一覧（内容の確認用）
    - data/daily/YYYY-MM-DD.txt にURLのみの一覧
      （NotebookLMのURL欄にそのまま貼り付ける）
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import requests

API_BASE = os.environ.get("ALPHAXIV_BASE_URL", "https://api.alphaxiv.org")
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "daily"
VALID_SORTS = ("hot", "likes", "github", "twitter", "most-stars", "most-twitter-likes")


def fetch_feed(sort: str, limit: int) -> list[dict]:
    headers = {"Accept": "application/json"}
    api_key = os.environ.get("ALPHAXIV_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(
        f"{API_BASE}/papers/v3/feed",
        headers=headers,
        params={"sort": sort, "limit": limit},
        timeout=30,
    )
    if not resp.ok:
        print(f"alphaXiv APIエラー ({resp.status_code}): {resp.text}", file=sys.stderr)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        for key in ("cards", "items", "results", "data"):
            if isinstance(data.get(key), list):
                return data[key]
        return []
    return data


def _first(d: dict, *keys: str, default=""):
    for key in keys:
        if d.get(key):
            return d[key]
    return default


def card_to_entry(card: dict, full_text: bool) -> tuple[str, str] | None:
    paper = card.get("paper", card)
    arxiv_id = _first(paper, "arxivId", "arxiv_id", "canonicalId", "id")
    if not arxiv_id:
        return None
    title = _first(paper, "title", default=arxiv_id)
    # full_text=Trueならpdf直リンク（NotebookLMがPDFソースとして本文まで読む）、
    # Falseならabs（要旨のみのページ）。デイリーニュース用途では要旨で十分な
    # ことが多く、件数を増やしてもNotebookLMのper-source samplingの影響を
    # 受けにくい。
    path = "pdf" if full_text else "abs"
    return title, f"https://arxiv.org/{path}/{arxiv_id}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="alphaXivの今日のフィードをNotebookLM貼り付け用URLリストに変換する"
    )
    parser.add_argument(
        "--sort",
        default="hot",
        choices=VALID_SORTS,
        help="フィードのソート指定",
    )
    parser.add_argument("--limit", type=int, default=8, help="取得件数")
    parser.add_argument(
        "--out", type=Path, default=None, help="出力ファイルパス（省略時は data/daily/日付.txt）"
    )
    parser.add_argument(
        "--full-text",
        action="store_true",
        help="要旨ページ(abs)ではなくPDF直リンクにする（NotebookLMが本文まで読む）",
    )
    args = parser.parse_args()

    cards = fetch_feed(args.sort, args.limit)
    entries = [entry for card in cards if (entry := card_to_entry(card, args.full_text))]
    if not entries:
        print(
            "論文が取得できませんでした。--sortの値やALPHAXIV_API_KEYを確認してください。",
            file=sys.stderr,
        )
        sys.exit(1)

    today = dt.date.today().isoformat()
    out_path = args.out or (OUT_DIR / f"{today}.txt")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(url for _, url in entries) + "\n", encoding="utf-8")

    print(f"{len(entries)}件取得しました（sort={args.sort}）:\n", file=sys.stderr)
    for title, url in entries:
        print(f"- {title}\n  {url}", file=sys.stderr)
    print(f"\nURL一覧を書き出しました: {out_path}", file=sys.stderr)
    print(
        "NotebookLMの Add Sources → URL に、このファイルの中身をそのまま貼り付けてください。",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
