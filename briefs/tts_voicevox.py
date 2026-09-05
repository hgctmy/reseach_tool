"""ローカルのVOICEVOX ENGINE (http://127.0.0.1:50021 等) を使った音声合成。

事前にVOICEVOX ENGINEを起動しておく必要があります。
- 公式アプリ: https://voicevox.hiroshiba.jp/
- Docker: docker run -p 50021:50021 voicevox/voicevox_engine:cpu-latest
"""
from __future__ import annotations

from pathlib import Path

import requests

from . import config


def synthesize(text: str, out_path: Path, speaker: int | None = None) -> Path:
    """textを音声合成し、wavファイルとしてout_pathに保存する。"""
    speaker_id = speaker if speaker is not None else config.VOICEVOX_SPEAKER_ID
    base_url = config.VOICEVOX_BASE_URL

    query_resp = requests.post(
        f"{base_url}/audio_query",
        params={"text": text, "speaker": speaker_id},
        timeout=30,
    )
    query_resp.raise_for_status()
    audio_query = query_resp.json()

    synth_resp = requests.post(
        f"{base_url}/synthesis",
        params={"speaker": speaker_id},
        json=audio_query,
        timeout=60,
    )
    synth_resp.raise_for_status()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(synth_resp.content)
    return out_path
