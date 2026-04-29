#!/usr/bin/env python3
"""Fetch banking / AI / NTT DATA topics and add free rule-based AI-style sales analysis.

No external LLM API is used. This script uses RSS + keyword signals + templates.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List, Any
from urllib.parse import quote_plus

import feedparser

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "news.json"
JST = timezone(timedelta(hours=9))
RECENT_DAYS = 2
MAX_AGE_HOURS = RECENT_DAYS * 24


QUERIES = {
    "メガバンク": [
        "メガバンク AI OR 生成AI OR DX OR 勘定系",
        "三菱UFJ OR みずほ OR 三井住友 AI 金融",
    ],
    "地銀": [
        "地方銀行 AI OR 生成AI OR DX OR 事務効率化",
        "地域金融機関 デジタル OR システム OR サイバー",
    ],
    "最新AI技術": [
        "生成AI 金融 業務効率化",
        "AI エージェント 企業 活用 日本",
    ],
    "NTTデータ": [
        "NTTデータ 金融 AI OR 生成AI OR 銀行",
        "NTT DATA 金融 AI 銀行",
    ],
    "その他": [
        "金融庁 AI 金融機関 サイバー",
        "日本銀行 金融機関 システム サイバー",
    ],
}

SIGNAL_RULES = {
    "generative_ai": {
        "words": ["生成AI", "生成 ai", "generative ai", "chatgpt", "LLM", "大規模言語", "AIエージェント", "エージェント"],
        "tags": ["生成AI", "AI活用"],
        "score": 18,
    },
    "regional_bank": {
        "words": ["地方銀行", "地銀", "地域金融", "信金", "信用金庫", "地域銀行"],
        "tags": ["地銀", "地域金融"],
        "score": 20,
    },
    "megabank": {
        "words": ["メガバンク", "三菱UFJ", "MUFG", "みずほ", "三井住友", "SMBC"],
        "tags": ["メガバンク"],
        "score": 14,
    },
    "nttdata": {
        "words": ["NTTデータ", "NTT DATA", "エヌ・ティ・ティ・データ"],
        "tags": ["NTTデータ"],
        "score": 22,
    },
    "core_banking": {
        "words": ["勘定系", "基幹系", "共同センター", "更改", "モダナイゼーション", "クラウド移行"],
        "tags": ["勘定系", "システム更改"],
        "score": 16,
    },
    "cyber": {
        "words": ["サイバー", "セキュリティ", "不正送金", "フィッシング", "ランサム", "不正アクセス"],
        "tags": ["サイバー", "リスク管理"],
        "score": 16,
    },
    "operations": {
        "words": ["業務効率", "事務効率", "省力化", "自動化", "BPO", "生産性", "営業店", "バックオフィス"],
        "tags": ["業務効率化"],
        "score": 14,
    },
    "lending": {
        "words": ["融資", "与信", "審査", "法人営業", "事業承継", "中小企業", "取引先支援"],
        "tags": ["融資", "法人営業"],
        "score": 13,
    },
    "governance": {
        "words": ["ガバナンス", "金融庁", "日銀", "規制", "監督", "リスク管理", "個人情報", "コンプライアンス"],
        "tags": ["ガバナンス"],
        "score": 12,
    },
    "cashless": {
        "words": ["キャッシュレス", "決済", "デジタル通貨", "CBDC", "送金", "ウォレット"],
        "tags": ["決済"],
        "score": 9,
    },
}

DEFAULTS = {
    "why_matters": "地銀のお客様と、業務効率化・リスク管理・地域金融DXのどれかに接続して会話化できます。",
    "talk": "記事の結論だけでなく、『御行ならどの業務に置き換えられるか』に変換すると会話が広がります。",
    "question": "御行では、このテーマを検討する場合、営業店・本部・システム部門のどこが最初の論点になりそうですか？",
    "nttdata_angle": "NTTデータ文脈では、既存システムの安定運用と新しい技術活用をどう両立するかに接続できます。",
    "risk_note": "事実確認は元記事を確認し、導入可否ではなく論点整理として話すのが安全です。",
}


def google_news_rss(query: str) -> str:
    return "https://news.google.com/rss/search?q=" + quote_plus(query) + "&hl=ja&gl=JP&ceid=JP:ja"


def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_datetime(entry: Any) -> datetime | None:
    raw = getattr(entry, "published", "") or getattr(entry, "updated", "")
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw).astimezone(JST)
    except Exception:
        return None


def parse_date(entry: Any) -> str:
    dt = parse_datetime(entry)
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M")
    return getattr(entry, "published", "") or getattr(entry, "updated", "") or ""


def age_hours(dt: datetime | None, now: datetime | None = None) -> float | None:
    if not dt:
        return None
    now = now or datetime.now(JST)
    return max(0.0, (now - dt).total_seconds() / 3600)


def get_source(entry: Any) -> str:
    src = getattr(entry, "source", None)
    if isinstance(src, dict) and src.get("title"):
        return src["title"]
    return getattr(entry, "author", "") or "Google News"


def detect_signals(text: str) -> List[str]:
    low = text.lower()
    signals = []
    for key, rule in SIGNAL_RULES.items():
        for w in rule["words"]:
            if w.lower() in low:
                signals.append(key)
                break
    return signals


def unique_tags(signals: List[str], category: str) -> List[str]:
    tags = [category]
    for sig in signals:
        tags.extend(SIGNAL_RULES[sig]["tags"])
    seen = []
    for t in tags:
        if t not in seen:
            seen.append(t)
    return seen[:8]


def importance(signals: List[str], category: str) -> int:
    score = 35
    for sig in signals:
        score += SIGNAL_RULES[sig]["score"]
    if category in ["地銀", "NTTデータ"]:
        score += 8
    if "generative_ai" in signals and ("regional_bank" in signals or "nttdata" in signals):
        score += 12
    return max(0, min(100, score))


def confidence(signals: List[str]) -> str:
    if len(signals) >= 4:
        return "高"
    if len(signals) >= 2:
        return "中"
    return "低"


def build_analysis(signals: List[str], category: str) -> Dict[str, str]:
    s = set(signals)
    why = []
    talks = []
    questions = []
    risks = []

    if "generative_ai" in s:
        why.append("生成AIは、行内文書検索・稟議ドラフト・本部照会・営業資料作成など、地銀の人手不足対策に直結しやすいテーマです。")
        talks.append("生成AIを『全社導入』ではなく、まず低リスクな行内業務から試す話にすると現実感が出ます。")
        questions.append("生成AIを試すなら、営業店事務・本部照会・法人営業支援のどこが最初に効果が出そうですか？")
        risks.append("個人情報、機密情報、回答根拠、ログ管理、利用ルールの整備が論点です。")
    if "regional_bank" in s:
        why.append("地域金融機関ならではの営業店事務、取引先支援、少人数運営の効率化に接続しやすい話題です。")
        talks.append("地銀の文脈では、コスト削減だけでなく『地域企業への支援力をどう上げるか』に置き換えると会話が広がります。")
        questions.append("御行では、地域企業支援・営業店事務・本部業務のどこが一番ボトルネックになっていますか？")
    if "megabank" in s:
        why.append("メガバンクの先行事例は、地銀で真似しやすい領域と難しい領域を分けて話せます。")
        talks.append("『大手行だからできる』で終わらせず、地銀なら小さく始めるならどこか、という切り口が使えます。")
        questions.append("メガバンクの取り組みを見て、御行でまず横展開しやすい業務はどこだと思われますか？")
    if "nttdata" in s:
        why.append("NTTデータ関連の話題は、金融システムの安定運用と新技術活用の両立に接続しやすいです。")
        talks.append("新技術単体ではなく、既存システム・共同センター・運用保守とどうつなぐかを話すと刺さりやすいです。")
        questions.append("新しいAI活用を検討する際、既存システムとの接続や運用面で一番気になる点はどこですか？")
    if "core_banking" in s:
        why.append("勘定系・基幹系の話題は、安定運用、柔軟性、コスト、将来の拡張性をセットで話せます。")
        talks.append("基幹系は『変える/変えない』ではなく、周辺業務から柔軟性を高める選択肢として話せます。")
        questions.append("次期システム更改を考える場合、安定運用・コスト・柔軟性のうち、今一番重い論点はどれですか？")
        risks.append("基幹系は可用性、移行リスク、ベンダーロックイン、長期コストの確認が必要です。")
    if "cyber" in s:
        why.append("サイバーは地銀自身のリスクだけでなく、地域企業からの相談テーマにもなりやすいです。")
        talks.append("不正送金やフィッシング対策を、取引先支援・顧客保護・行員教育の話に広げられます。")
        questions.append("最近、取引先企業からセキュリティや不正送金に関する相談は増えていますか？")
        risks.append("不安を煽らず、体制整備・訓練・顧客周知の論点として話すのが安全です。")
    if "operations" in s:
        why.append("業務効率化は、営業店の人手不足や本部集中業務の負荷軽減に直結します。")
        talks.append("『何を自動化するか』より先に、行員の時間をどの顧客接点に戻すかを話すと営業向けになります。")
        questions.append("営業店の中で、行員の時間を一番奪っている事務は何だと感じますか？")
    if "lending" in s:
        why.append("融資・法人営業・取引先支援は、地銀の収益力と地域貢献の両面で会話しやすいテーマです。")
        talks.append("AIやデータ活用を、融資審査そのものではなく、企業理解・面談準備・提案精度向上から話すと入りやすいです。")
        questions.append("法人営業で、面談前の企業理解や提案準備にもっと時間を使えると効果が出そうですか？")
    if "governance" in s:
        why.append("金融庁・日銀・ガバナンスの話題は、AIやDXの前提条件として役員層にも話しやすいテーマです。")
        talks.append("便利さだけではなく、利用ルール・監査・説明責任まで含めて話すと信頼感が出ます。")
        questions.append("AIやデータ活用を進めるうえで、現場利用ルールと監査対応のどちらが先に課題になりそうですか？")
        risks.append("規制・監督の話は、断定せずに元資料確認を前提にするのが安全です。")
    if "cashless" in s:
        why.append("決済・キャッシュレスは、個人顧客接点と地域加盟店支援の両方につながります。")
        talks.append("地域店舗の決済データや顧客接点を、取引先支援やマーケティングにどう活かすかの会話にできます。")
        questions.append("地域の加盟店支援として、決済データ活用や販促支援のニーズはありますか？")

    ntt_angle = "NTTデータ文脈では、既存システムの安定運用を守りながら、AI・データ活用・業務効率化を段階導入する話に接続できます。"
    if "nttdata" in s:
        ntt_angle = "NTTデータ自身の取り組みとして、金融領域での実装力・運用力・AI活用支援の文脈に直接つなげられます。"
    elif "core_banking" in s:
        ntt_angle = "共同センター、勘定系周辺、クラウド/モダナイゼーションの論点としてNTTデータの金融基盤知見に接続できます。"
    elif "generative_ai" in s:
        ntt_angle = "生成AIを金融機関で安全に使うためのガバナンス、業務設計、システム連携の支援文脈に接続できます。"

    return {
        "why_matters": " ".join(why[:2]) or DEFAULTS["why_matters"],
        "talk": " ".join(talks[:2]) or DEFAULTS["talk"],
        "question": questions[0] if questions else DEFAULTS["question"],
        "nttdata_angle": ntt_angle,
        "risk_note": " ".join(risks[:2]) or DEFAULTS["risk_note"],
    }


def normalize_topic_title(title: str) -> str:
    text = title.lower()
    text = re.sub(r"（[^）]*）|\([^)]*\)|【[^】]*】|\"[^\"]*\"", " ", text)
    text = re.sub(r"[｜|].*$", " ", text)
    text = re.sub(r"(ニュース|速報|発表|開始|実証|導入|検討|提供|サービス|について|株式会社|銀行|日本|国内|向け)", " ", text)
    text = re.sub(r"[^0-9a-zぁ-んァ-ン一-龥]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def topic_tokens(title: str) -> set[str]:
    text = normalize_topic_title(title)
    tokens = {t for t in text.split() if len(t) >= 2}
    compact = text.replace(" ", "")
    for n in (2, 3, 4):
        for i in range(max(0, len(compact) - n + 1)):
            gram = compact[i:i+n]
            if re.search(r"[一-龥ァ-ンぁ-んa-z0-9]", gram):
                tokens.add(gram)
    return tokens


def similarity(a: str, b: str) -> float:
    ta, tb = topic_tokens(a), topic_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(1, len(ta | tb))


def item_datetime(item: Dict[str, Any]) -> datetime | None:
    raw = item.get("published") or ""
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=JST)
    except Exception:
        return None


def mark_and_keep_recent(item: Dict[str, Any], now: datetime) -> bool:
    dt = item_datetime(item)
    if dt is None:
        item["age_hours"] = None
        item["is_recent"] = True
        return True
    age = age_hours(dt, now)
    item["age_hours"] = round(age, 1)
    item["is_recent"] = age <= MAX_AGE_HOURS
    return item["is_recent"]


def merge_duplicate_topics(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: List[Dict[str, Any]] = []
    for item in items:
        norm = normalize_topic_title(item["title"])
        placed = False
        for group in groups:
            if norm == group["norm"] or similarity(item["title"], group["items"][0]["title"]) >= 0.42:
                group["items"].append(item)
                placed = True
                break
        if not placed:
            groups.append({"norm": norm, "items": [item]})

    merged = []
    for group in groups:
        candidates = group["items"]
        candidates.sort(key=lambda x: (x.get("published", ""), x.get("importance", 0)), reverse=True)
        main = candidates[0]
        if len(candidates) > 1:
            sources, tags, signals = [], [], []
            for c in candidates:
                if c.get("source") and c["source"] not in sources:
                    sources.append(c["source"])
                tags.extend(c.get("tags", []))
                signals.extend(c.get("signals", []))
            main["duplicate_count"] = len(candidates)
            main["related_sources"] = sources[:5]
            main["tags"] = list(dict.fromkeys(tags))[:8]
            main["signals"] = list(dict.fromkeys(signals))
            main["importance"] = max(c.get("importance", 0) for c in candidates)
        else:
            main["duplicate_count"] = 1
            main["related_sources"] = [main.get("source", "")] if main.get("source") else []
        merged.append(main)
    return merged



def item_id(title: str, url: str) -> str:
    return hashlib.sha1((title + url).encode("utf-8")).hexdigest()[:16]


def fetch_category(category: str, queries: List[str], limit_per_query: int = 8) -> List[Dict[str, Any]]:
    items = []
    for q in queries:
        feed = feedparser.parse(google_news_rss(q))
        for entry in feed.entries[:limit_per_query]:
            title = clean_html(getattr(entry, "title", ""))
            url = getattr(entry, "link", "")
            summary = clean_html(getattr(entry, "summary", ""))
            text = f"{title} {summary}"
            signals = detect_signals(text)
            analysis = build_analysis(signals, category)
            items.append({
                "id": item_id(title, url),
                "category": category,
                "title": title,
                "url": url,
                "source": get_source(entry),
                "published": parse_date(entry),
                "summary": summary[:280],
                "tags": unique_tags(signals, category),
                "signals": signals,
                "importance": importance(signals, category),
                "confidence": confidence(signals),
                **analysis,
            })
    return items


def main() -> None:
    all_items = []
    now = datetime.now(JST)
    for category, queries in QUERIES.items():
        all_items.extend(fetch_category(category, queries))

    # Exact duplicate removal by id first.
    by_id: Dict[str, Dict[str, Any]] = {}
    for item in all_items:
        old = by_id.get(item["id"])
        if old is None or item.get("published", "") > old.get("published", ""):
            by_id[item["id"]] = item

    # Only show recent topics. Important but old articles should not rise to the top.
    recent_items = [item for item in by_id.values() if mark_and_keep_recent(item, now)]

    # Merge near-duplicate topics from different sources / slightly different titles.
    items = merge_duplicate_topics(recent_items)

    # Freshness first, then publish time, then importance.
    items.sort(key=lambda x: (x.get("is_recent") is True, x.get("published", ""), x.get("importance", 0)), reverse=True)
    items = items[:60]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M JST"),
        "version": "v3-ops-ready-search-dedupe-freshness",
        "policy": {
            "recent_days": RECENT_DAYS,
            "dedupe": "similar-title topic clustering",
            "search": "button-based IME-safe search",
        },
        "items": items,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} with {len(items)} items")


if __name__ == "__main__":
    main()
