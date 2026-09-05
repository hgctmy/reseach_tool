"""生成した音声をmp3化してクラウドストレージの同期フォルダにコピーする。

通勤中などオフラインで聞きたい場合、Google Drive/Dropbox/iCloud Driveなどの
同期フォルダに音声を置いておけば、スマホの公式アプリが自動でダウンロード
してくれるので、電波が無い場所でも標準の音楽/ファイルアプリで再生できる。

要 ffmpeg（`brew install ffmpeg` / `apt install ffmpeg` などで別途インストール）。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from . import config

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')
_SEQ_PATH = config.DATA_DIR / ".sync_seq"


def _sanitize(name: str, max_len: int = 60) -> str:
    cleaned = _INVALID_CHARS.sub("", name).strip()
    return cleaned[:max_len] if cleaned else "untitled"


def _next_seq() -> int:
    """スマホの音楽アプリでファイル名順に並べても再生順が保たれるよう、
    連番を永続化して払い出す。"""
    current = int(_SEQ_PATH.read_text()) if _SEQ_PATH.exists() else 0
    nxt = current + 1
    _SEQ_PATH.write_text(str(nxt))
    return nxt


def convert_to_mp3(
    wav_path: Path,
    mp3_path: Path,
    title: str,
    artist: str = "",
    track_num: int | None = None,
) -> Path:
    """wavをmp3に変換し、タイトル等をID3タグとして埋め込む（要ffmpeg）。"""
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-qscale:a",
        "4",
        "-metadata",
        f"title={title}",
        "-metadata",
        f"artist={artist or '日本語版Briefs'}",
        "-metadata",
        "album=日本語版Briefs",
    ]
    if track_num is not None:
        cmd += ["-metadata", f"track={track_num}"]
    cmd.append(str(mp3_path))

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpegが見つかりません。'brew install ffmpeg' 等でインストールしてください。"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpegでのmp3変換に失敗しました: {exc.stderr}") from exc
    return mp3_path


def sync_to_folder(
    wav_path: Path,
    title: str,
    authors: list[str] | None = None,
    seq: int | None = None,
    sync_dir: str | None = None,
) -> Path | None:
    """音声をmp3化し、クラウドストレージの同期フォルダにコピーする。

    BRIEFS_SYNC_DIR（またはsync_dir引数）が未設定の場合は何もしない。
    """
    target_dir = sync_dir or config.SYNC_DIR
    if not target_dir:
        return None

    seq = seq if seq is not None else _next_seq()
    artist = "、".join(authors or [])
    filename = f"{seq:03d}_{_sanitize(title)}.mp3"
    dest_path = Path(target_dir).expanduser() / filename

    mp3_path = convert_to_mp3(wav_path, dest_path, title=title, artist=artist, track_num=seq)
    return mp3_path
