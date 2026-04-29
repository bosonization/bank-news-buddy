# 地銀トークナビ v2 - 無料ロジックAI判定版

地銀営業マン向けに、メガバンク・地銀・最新AI技術・NTTデータ・その他のニュースを集め、ニュースごとに営業トークへ変換する静的ダッシュボードです。

## v2のポイント

- 外部LLM APIなし
- APIキー不要
- GitHub Actionsだけで無料運用しやすい
- ニュースごとにタイトル・RSS要約を判定
- キーワードシグナルから重要度・営業トーク・お客様質問を生成
- JST 6:00 / 12:00 / 18:00 に自動更新

## ファイル構成

```text
bank-news-buddy-v2-free-ai/
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

## 使い方

1. このフォルダの中身をGitHubリポジトリにアップロード
2. GitHubの Actions を有効化
3. Settings → Actions → General → Workflow permissions を `Read and write permissions` にする
4. Actions → Update news → Run workflow で手動実行
5. VercelでGitHubリポジトリをImport

## 判定ロジック

`scripts/fetch_news.py` がニュースごとに以下のシグナルを判定します。

- generative_ai
- regional_bank
- megabank
- nttdata
- core_banking
- cyber
- operations
- lending
- governance
- cashless

その組み合わせから、以下を生成します。

- なぜ地銀営業に関係あるか
- 営業トーク
- お客様に聞くなら
- NTTデータ文脈
- 注意点
- 重要度
- 判定信頼度
- タグ

## 注意

ニュース本文は転載せず、RSSから取得できるタイトル・概要・リンクを表示します。重要な事実確認は必ず元記事で行ってください。
