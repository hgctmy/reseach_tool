# 日本語版 Briefs 的な運用手順（デイリーダイジェスト版）

alphaXivの「Briefs」（論文の音声要約フィード）に日本語版は無い。
自作の音声合成パイプラインも一度試作したが、結局は既存ツール（alphaXiv +
NotebookLM）を組み合わせる方が手軽で保守も不要という結論になった。

1論文1ノートブックではなく、**その日のトレンド/レコメンド論文をまとめて
1つのノートブックに入れ、1本の「デイリーニュース」的なAudio Overviewを
生成する**運用にしている。NotebookLMは複数ソースを横断した一本の音声解説を
作れるので、この使い方に向いている。

## セットアップ

```bash
pip install -r requirements.txt
```

APIキーは無くても`--sort hot`（公開フィード）は動く。自分のアカウント
向けのレコメンドを試したい場合は、alphaxiv.orgのSettings > API Keysで発行した
キーを設定する:

```bash
export ALPHAXIV_API_KEY="axv1_..."
```

## 毎日の手順

### 1. 今日の論文リストを取得する

**PCの場合:**
```bash
python scripts/daily_digest.py --sort hot --limit 8
```
`data/daily/YYYY-MM-DD.txt` にarXiv URLの一覧が書き出される
（標準エラー出力にタイトル付きの一覧も表示されるので中身を確認できる）。

**iPhoneの場合（GitHub Actions）:**
このリポジトリは公開リポジトリなのでGitHub Actionsが無料で使える。アプリの
追加インストールは不要で、Safari/ChromeやGitHub公式アプリからそのまま実行できる。

1. GitHubでこのリポジトリを開き、**Actions** タブ → **Daily alphaXiv digest**
   を選ぶ
2. **Run workflow** をタップ（対象ブランチを選び、必要なら`sort`/`limit`を入力）
3. 実行が終わったらその実行（run）を開くと、**Summary** に今日のURL一覧が
   コードブロックで表示される。全選択してコピーする
4. 結果は`data/daily/YYYY-MM-DD.txt`としてリポジトリにも自動コミットされるので、
   後から見返すこともできる

毎日決まった時間（デフォルトはUTC 22:00 = 日本時間 朝7:00）に自動実行する
スケジュールも設定済み（`.github/workflows/daily-digest.yml`）。時間や
`sort`/`limit`のデフォルト値を変えたい場合はこのファイルを編集する。

自分のアカウント向けのレコメンドを試したい場合は、GitHubリポジトリの
**Settings → Secrets and variables → Actions** で `ALPHAXIV_API_KEY` という
名前のSecretを追加する（alphaxiv.orgのSettings > API Keysで発行したキー）。

### 2. NotebookLMにまとめて貼り付ける

その日用の新しいノートブック（または使い回しの「デイリーダイジェスト」
ノートブックのソースを入れ替え）を開き、Add Sources → URL に、
1で取得したURL一覧をそのまま貼り付ける。NotebookLMは2025年8月以降、
スペース/改行区切りで複数URLを一括登録できる。

### 3. 出力言語を日本語にする（初回のみ）

右上の設定 → Output Language を「日本語」に変更する。

### 4. Audio Overviewを生成する

複数ソースをまとめた1本の日本語ポッドキャスト風音声ができる。

### 5. 通勤中などオフラインで聴きたい場合

生成された音声は「…」メニューからダウンロードできる。Google Drive等の
同期フォルダに置いておけば、スマホの公式アプリで事前ダウンロードしておき、
電波の無い場所でも標準の音楽/ファイルアプリで再生できる。

## メモ

- `--sort`に指定できる値は `hot` / `likes` / `github` / `twitter` /
  `most-stars` / `most-twitter-likes` のいずれか。それ以外の値（`trending`等）
  は400エラーになる。
- 出力するURLはデフォルトで`arxiv.org/abs/`（要旨のみ）。デイリーニュース的に
  サッと聞き流す用途なら要旨で十分な上、件数を増やしてもNotebookLMの
  「per-source sampling」（ソースが多いと各ソースから読む量が間引かれる）の
  影響を受けにくい。1本1本を深掘りしたい場合は`--full-text`を付けると
  `arxiv.org/pdf/`（PDF直リンク、NotebookLMがPDFソースとして本文まで読み込む）
  に切り替わる。
- alphaXiv非公開APIとの本格連携やVOICEVOXによる自前音声合成パイプラインも
  一度試作したが、セットアップ・保守コストに見合わないため削除した。
