# 地銀トークナビ v3

GitHubにアップロードしてVercelでImportすれば動く、静的ニュースダッシュボードです。

## v3の改善点

### 1. 検索UIの修正

v2では入力のたびに画面全体を再描画していたため、日本語入力の変換中にinputが作り直され、1文字で入力が止まる問題がありました。

v3では以下に変更しています。

- 入力中は再描画しない
- 「検索」ボタンを押した時だけ検索実行
- Enterキーでも検索可能
- 「クリア」ボタンを追加
- 検索対象をタイトル、要約、営業トーク、質問、タグ、媒体名まで拡張

### 2. 同じネタの集約

`fetch_news.py` に、タイトル正規化＋類似度判定によるトピック集約を追加しました。

- 完全一致URL/ID重複を削除
- タイトルから媒体差分・記号・汎用語を除去
- 2〜4文字n-gramで類似度を計算
- 同じネタと判断した記事は1件に集約
- カードに「似た記事◯件を集約」と表示

### 3. 古い記事の上位表示を抑制

v3では基本的に直近2日以内の記事だけを表示対象にしています。

- `RECENT_DAYS = 2`
- 48時間超の記事は原則除外
- 重要度が高くても古い記事は上に出さない
- カードに「◯h前」を表示

## 構成

```txt
bank-news-buddy-v3-ops-ready/
├─ index.html
├─ style.css
├─ app.js
├─ assets/
│  └─ banker-buddy.svg
├─ data/
│  └─ news.json
├─ scripts/
│  └─ fetch_news.py
├─ requirements.txt
└─ .github/workflows/update-news.yml
```

## 更新時間

GitHub ActionsでJST 6:00 / 12:00 / 18:00に更新します。

```yaml
- cron: "0 21 * * *" # JST 06:00
- cron: "0 3 * * *"  # JST 12:00
- cron: "0 9 * * *"  # JST 18:00
```

## 公開方法

1. このフォルダの中身をGitHubリポジトリにアップロード
2. VercelでImport
3. GitHub ActionsのWorkflow permissionsをRead and writeにする
4. Actionsから `Update news` を手動実行して確認
