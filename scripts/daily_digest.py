#!/usr/bin/env python3
"""alphaXivの今日のトレンド/レコメンドフィードを取得し、NotebookLMに一括貼り付け
できるURLリストを出力する。

NotebookLMは2025年8月以降、Add Sources → URL欄にスペース/改行区切りで複数の
URLをまとめて貼り付けられる（1件ずつ登録する必要がない）。このスクリプトは
その貼り付け用テキストを作るだけで、ノートブックの作成やAudio Overviewの
生成自体は手動でNotebookLM上から行う。

使い方:
    python scripts/daily_digest.py
    python scripts/daily_digest.py --sort Hot --limit 8
    python scripts/daily_digest.py --full-text   # 要旨ではなくPDF本文まで読ませたい場合
    ALPHAXIV_API_KEY=axv1_... python scripts/daily_digest.py --sort ForYou

デフォルトはarxiv.org/abs/（要旨ページ）。デイリーニュース的にサッと聞き流す
用途なら要旨だけで十分な上、件数を増やしてもNotebookLMの「per-source sampling」
（ソースが多いと各ソースから読む量が間引かれる）の影響を受けにくい。
1本1本を深掘りしたい場合は`--full-text`でPDF直リンク（本文まで読み込まれる）
に切り替えられる。

--sortに指定できる値は Hot / Comments / Views / Likes / GitHub / Recommended /
ForYou / Recent のいずれか（実際にAPIが返したバリデーションエラーから判明した
正式なenum値）。RecommendedとForYouはおそらくログイン（ALPHAXIV_API_KEY）が
前提のパーソナライズされたフィード。
--intervalは 3 Days / 7 Days / 30 Days / 90 Days / All time のいずれか
（ランキング集計の対象期間）。

出力:
    - 標準エラー出力にタイトル付き一覧（内容の確認用）
    - data/daily/YYYY-MM-DD.txt にURLのみの一覧
      （NotebookLMのURL欄にそのまま貼り付ける）
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

API_BASE = os.environ.get("ALPHAXIV_BASE_URL", "https://api.alphaxiv.org")
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "daily"
# 実際のAPIバリデーションエラーで判明した正式なenum値
VALID_SORTS = ("Hot", "Comments", "Views", "Likes", "GitHub", "Recommended", "ForYou", "Recent")
VALID_INTERVALS = ("3 Days", "7 Days", "30 Days", "90 Days", "All time")


def fetch_feed(sort: str, page_size: int, interval: str, page_num: int = 1) -> list[dict]:
    headers = {"Accept": "application/json"}
    api_key = os.environ.get("ALPHAXIV_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(
        f"{API_BASE}/papers/v3/feed",
        headers=headers,
        params={
            "sort": sort,
            "interval": interval,
            "pageNum": str(page_num),
            "pageSize": str(page_size),
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"alphaXiv APIエラー ({resp.status_code}): {resp.text}", file=sys.stderr)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("papers", "cards", "items", "results", "data"):
            if isinstance(data.get(key), list):
                return data[key]
        print(
            "デバッグ: レスポンスがdictだが既知のキー(papers/cards/items/results/data)に"
            f"一覧が見つからない。トップレベルのキー: {list(data.keys())}",
            file=sys.stderr,
        )
        print(f"デバッグ: レスポンス全体: {json.dumps(data, ensure_ascii=False)[:3000]}", file=sys.stderr)
        return []
    return []


def _first(d: dict, *keys: str, default=""):
    for key in keys:
        if d.get(key):
            return d[key]
    return default


def card_to_entry(card: dict, full_text: bool) -> tuple[str, str] | None:
    paper = card.get("paper", card)
    # 注意: "id"はalphaXiv内部のUUIDでarXiv IDではないため候補に入れない
    arxiv_id = _first(
        paper,
        "arxivId",
        "arxiv_id",
        "arxiv_identifier",
        "canonicalId",
        "canonical_id",
        "external_id",
        "externalId",
    )
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
        default="Hot",
        choices=VALID_SORTS,
        help="フィードのソート指定",
    )
    parser.add_argument(
        "--interval",
        default="7 Days",
        choices=VALID_INTERVALS,
        help="ランキング集計の対象期間",
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

    cards = fetch_feed(args.sort, args.limit, args.interval)
    entries = [entry for card in cards if (entry := card_to_entry(card, args.full_text))]
    if not entries:
        if cards:
            first = cards[0].get("paper", cards[0])
            arxiv_like = {k: v for k, v in first.items() if "arxiv" in k.lower()}
            print(
                f"デバッグ: {len(cards)}件のカードは取得できたが、arxiv_idの抽出に"
                "全件失敗した。フィールド名の想定が違う可能性がある。",
                file=sys.stderr,
            )
            print(f"デバッグ: 1件目のキー一覧: {sorted(first.keys())}", file=sys.stderr)
            print(f"デバッグ: 'arxiv'を含むキー: {arxiv_like}", file=sys.stderr)
            print(
                "デバッグ: 1件目の中身(一部): "
                + json.dumps(first, ensure_ascii=False, indent=2)[:2000],
                file=sys.stderr,
            )
        else:
            print(
                "論文が取得できませんでした（0件）。--sort/--intervalの値や"
                "ALPHAXIV_API_KEYを確認してください。",
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
