"""ユーザーの「いいね/スキップ」履歴を保存するプロファイル。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import config


@dataclass
class Profile:
    liked: dict[str, str] = field(default_factory=dict)  # arxiv_id -> abstract
    skipped: set[str] = field(default_factory=set)
    seen: set[str] = field(default_factory=set)

    @classmethod
    def load(cls) -> "Profile":
        if not config.PROFILE_PATH.exists():
            return cls()
        data = json.loads(config.PROFILE_PATH.read_text(encoding="utf-8"))
        return cls(
            liked=data.get("liked", {}),
            skipped=set(data.get("skipped", [])),
            seen=set(data.get("seen", [])),
        )

    def save(self) -> None:
        config.PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "liked": self.liked,
            "skipped": sorted(self.skipped),
            "seen": sorted(self.seen),
        }
        config.PROFILE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def mark_liked(self, arxiv_id: str, abstract: str) -> None:
        self.liked[arxiv_id] = abstract
        self.seen.add(arxiv_id)
        self.save()

    def mark_skipped(self, arxiv_id: str) -> None:
        self.skipped.add(arxiv_id)
        self.seen.add(arxiv_id)
        self.save()

    def mark_seen(self, arxiv_id: str) -> None:
        self.seen.add(arxiv_id)
