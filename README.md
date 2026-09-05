# 日本語版 Briefs（プロトタイプ）

alphaXivの「Briefs」（論文の音声要約フィード）に日本語版が無かったため、
自前で similar な体験を作るためのパイプライン。

- **おすすめ論文の取得**: alphaXiv公式API（`api.alphaxiv.org`）のホームページ
  フィード（Briefsのもとになっているのと同じ推薦フィード）を使用。
  APIキーが無い/取得できない場合のフォールバックとして、arXiv APIの新着論文
  （TF-IDFでいいね履歴に基づき再ランキング）や、Hugging Face Daily Papers
  （コミュニティの注目度に基づくトレンド論文）も選択可能。
- **日本語ナレーション原稿**: alphaXivが既に生成している日本語のAI概要
  （Overview/Blog）があればそれを音声用に要約して使用し、無ければClaude APIで
  論文の要旨から新規生成する。
- **音声合成**: [VOICEVOX](https://voicevox.hiroshiba.jp/) ENGINE（無料・ローカル）。
- **配信**: FastAPIのローカルサーバーで、スワイプ的に聞き流せるWebページを提供。
  「いいね/スキップ」で好みを記録し、次回生成時のランキングに反映する。

## セットアップ

```bash
pip install -r requirements.txt
```

### 1. VOICEVOX ENGINEを起動する

公式アプリを起動するか、Dockerで:

```bash
docker run -p 50021:50021 voicevox/voicevox_engine:cpu-latest
```

### 2. APIキーを環境変数に設定する

```bash
export ANTHROPIC_API_KEY="sk-ant-..."      # 台本生成・要約に使用
export ALPHAXIV_API_KEY="axv1_..."         # alphaxiv.org の Settings > API Keys で発行
```

`ALPHAXIV_API_KEY`が無い場合は `--source arxiv` または `--source trending` を使うと
alphaXivなしでも動作する（ただしおすすめの質はalphaXiv製フィードより落ちる）。

## 使い方

Briefsを生成してフィードに追加する:

```bash
python -m briefs.pipeline generate --source alphaxiv --top-n 5
```

主なオプション:

- `--source alphaxiv|arxiv|trending`（デフォルト: `alphaxiv`）
- `--top-n`: 1回で生成する件数（デフォルト: 5）
- `--max-fetch`: 候補として取得する件数（デフォルト: 50）
- `--categories`: `--source arxiv`時のarXivカテゴリ（カンマ区切り、例: `cs.CL,cs.LG`）

生成したフィードを聞く:

```bash
uvicorn briefs.app:app --reload
```

ブラウザで http://127.0.0.1:8000 を開くと、生成済みのBriefsが再生される。
「いいね」を押すとその論文の要旨が好み学習用のプロファイル
（`data/profile.json`）に保存され、`--source arxiv`利用時の次回生成の
ランキングに反映される。

### スマホから見る（同じWi-Fi内）

同じWi-Fiに繋いだスマホからも見られる。サーバー起動時にホストを開放し、

```bash
uvicorn briefs.app:app --host 0.0.0.0 --port 8000
```

PCのローカルIPアドレス（`ip a` / `ifconfig` / `ipconfig`で確認、例: `192.168.1.23`）
を使って、スマホのブラウザで `http://192.168.1.23:8000` を開く。
UIは幅480px程度のスマホ向けレイアウトになっている。

### 通勤中などオフラインで聴く（クラウドストレージ同期）

外出先で電波が悪い/PCと同じWi-Fiにいない場合は、生成したmp3をGoogle Drive等の
同期フォルダに置いておき、スマホの公式アプリで事前ダウンロードしておく方法が
手軽（サーバーを外部公開する必要が無い）。

1. [ffmpeg](https://ffmpeg.org/)をインストールする（`brew install ffmpeg` /
   `apt install ffmpeg` など。mp3変換とタイトル埋め込みに使用）
2. 同期フォルダのパスを環境変数で指定する:
   ```bash
   export BRIEFS_SYNC_DIR="$HOME/Google Drive/My Drive/briefs"
   ```
3. `python -m briefs.pipeline generate` を実行すると、`data/audio/`のwavに加えて
   タイトル・著者をID3タグに埋め込んだmp3が連番付きファイル名
   （例: `001_タイトル.mp3`）で同期フォルダにコピーされる
4. スマホ側でGoogle Driveアプリを開き、該当ファイルを「オフラインで使用可能」に
   設定しておけば、通勤中など電波が無い場所でも標準の音楽/ファイルアプリで
   ダウンロード済みファイルを再生できる

新しいBriefsを聴き終えたら生成済みmp3は不要なら手動で削除して問題ない
（フィード自体はこのプロトタイプでは削除操作を提供していない）。

## 定期実行

cronなどで定期的に`python -m briefs.pipeline generate`を実行すれば、
新しいBriefsが自動でフィードに追加されていく。

## 既知の制約

- alphaXiv公式APIは非公式ドキュメント（[petroslamb/alphaxiv-py](https://github.com/petroslamb/alphaxiv-py)）
  を参考に実装しており、フィードのフィールド名やAI概要生成のポーリング仕様の
  細部は実際のレスポンスで確認・調整が必要な場合がある。
- alphaXivの日本語Overview/Blogは論文によっては未生成・未対応の場合があり、
  その場合はClaude APIによる独自生成にフォールバックする。
