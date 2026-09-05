"""日本語版Briefsパイプラインの設定。環境変数で上書き可能。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
PROFILE_PATH = DATA_DIR / "profile.json"
FEED_PATH = DATA_DIR / "feed.json"

# 取得対象のarXivカテゴリ（カンマ区切りで環境変数から上書き可能）
ARXIV_CATEGORIES = os.environ.get("BRIEFS_ARXIV_CATEGORIES", "cs.CL,cs.LG,cs.AI").split(",")

# VOICEVOX ENGINE（ローカル起動が前提。docker run 等で50021番ポートを公開しておく）
VOICEVOX_BASE_URL = os.environ.get("VOICEVOX_BASE_URL", "http://127.0.0.1:50021")
VOICEVOX_SPEAKER_ID = int(os.environ.get("VOICEVOX_SPEAKER_ID", "3"))  # ずんだもん(ノーマル)

# 台本生成に使うAnthropicモデル
ANTHROPIC_MODEL = os.environ.get("BRIEFS_ANTHROPIC_MODEL", "claude-sonnet-5")

# alphaXiv公式API（api.alphaxiv.org）。Settings > API Keysで発行したキーを設定する。
# 参考: https://github.com/petroslamb/alphaxiv-py (公開されているエンドポイント仕様)
ALPHAXIV_API_KEY = os.environ.get("ALPHAXIV_API_KEY")
ALPHAXIV_BASE_URL = os.environ.get("ALPHAXIV_BASE_URL", "https://api.alphaxiv.org")
# フィードのソート指定。有効な値は未公開のため、エラーになる場合は環境変数で調整してください。
ALPHAXIV_FEED_SORT = os.environ.get("ALPHAXIV_FEED_SORT", "trending")
ALPHAXIV_OVERVIEW_LANG = os.environ.get("ALPHAXIV_OVERVIEW_LANG", "ja")
# AI概要の生成待ちをポーリングする際の設定
ALPHAXIV_OVERVIEW_POLL_TIMEOUT = int(os.environ.get("ALPHAXIV_OVERVIEW_POLL_TIMEOUT", "90"))
ALPHAXIV_OVERVIEW_POLL_INTERVAL = int(os.environ.get("ALPHAXIV_OVERVIEW_POLL_INTERVAL", "5"))

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
