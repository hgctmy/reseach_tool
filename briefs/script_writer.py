"""Claude APIで論文をポッドキャスト風の短い日本語ナレーション原稿に変換する。"""
from __future__ import annotations

import anthropic

from . import config
from .arxiv_client import Paper

_SYSTEM_PROMPT = (
    "あなたは学術論文を紹介するポッドキャストのナレーターです。"
    "与えられた論文のタイトルと要旨をもとに、リスナーが聞き流すだけで"
    "研究の要点（背景・課題・提案手法・結果）を理解できる、"
    "自然で口語的な日本語のナレーション原稿を書いてください。"
    "専門用語は必要に応じてかみ砕いて説明し、原稿だけを出力してください"
    "（見出しや箇条書き、記号による装飾は不要です）。"
)

_USER_TEMPLATE = (
    "タイトル: {title}\n"
    "著者: {authors}\n"
    "要旨: {abstract}\n\n"
    "上記の論文について、{duration_hint}程度で読み上げられる長さの"
    "日本語ナレーション原稿を作成してください。"
)


def write_script(paper: Paper, duration_hint: str = "60〜90秒") -> str:
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": _USER_TEMPLATE.format(
                    title=paper.title,
                    authors="、".join(paper.authors) or "不明",
                    abstract=paper.abstract,
                    duration_hint=duration_hint,
                ),
            }
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()


_CONDENSE_SYSTEM_PROMPT = (
    "あなたは学術論文を紹介するポッドキャストのナレーターです。"
    "与えられた日本語の論文解説記事をもとに、リスナーが聞き流すだけで"
    "研究の要点を理解できる、自然で口語的な日本語のナレーション原稿に"
    "要約してください。専門用語はかみ砕いて説明し、原稿だけを出力してください"
    "（見出しや箇条書き、記号による装飾は不要です）。"
)


def condense_overview_to_script(
    paper_title: str, overview_text: str, duration_hint: str = "60〜90秒"
) -> str:
    """alphaXivの日本語概要（Overview/Blog）記事を、音声で聞き流せる短い台本に要約する。"""
    client = anthropic.Anthropic()
    # 記事が長い場合に備えてトークン量を抑える
    truncated = overview_text[:8000]
    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=_CONDENSE_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    f"タイトル: {paper_title}\n\n解説記事:\n{truncated}\n\n"
                    f"上記を、{duration_hint}程度で読み上げられる長さの"
                    "日本語ナレーション原稿に要約してください。"
                ),
            }
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()
