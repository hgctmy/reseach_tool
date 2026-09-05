"""arXiv APIから新着論文を取得するクライアント。"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


@dataclass
class Paper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    published: str
    pdf_url: str

    @property
    def abs_url(self) -> str:
        return f"https://arxiv.org/abs/{self.arxiv_id}"


def _parse_entry(entry: ET.Element) -> Paper:
    raw_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
    arxiv_id = raw_id.rsplit("/", 1)[-1]
    title = " ".join(entry.findtext("atom:title", default="", namespaces=ATOM_NS).split())
    abstract = " ".join(entry.findtext("atom:summary", default="", namespaces=ATOM_NS).split())
    authors = [
        a.findtext("atom:name", default="", namespaces=ATOM_NS)
        for a in entry.findall("atom:author", ATOM_NS)
    ]
    categories = [c.attrib.get("term", "") for c in entry.findall("atom:category", ATOM_NS)]
    published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
    pdf_url = ""
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("title") == "pdf":
            pdf_url = link.attrib.get("href", "")
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        abstract=abstract,
        authors=authors,
        categories=categories,
        published=published,
        pdf_url=pdf_url,
    )


def fetch_recent_papers(
    categories: list[str],
    max_results: int = 50,
    retries: int = 3,
) -> list[Paper]:
    """指定カテゴリの新着論文をarXiv APIから取得する（更新日時の降順）。"""
    category_query = " OR ".join(f"cat:{c.strip()}" for c in categories if c.strip())
    params = {
        "search_query": category_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(ARXIV_API_URL, params=params, timeout=30)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            return [_parse_entry(e) for e in root.findall("atom:entry", ATOM_NS)]
        except (requests.RequestException, ET.ParseError) as exc:
            last_error = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"arXiv APIの取得に失敗しました: {last_error}") from last_error
