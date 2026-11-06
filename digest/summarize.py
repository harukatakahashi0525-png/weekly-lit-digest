"""Claude API で 日本語タイトル・3行要点・アブストラクト全訳・分類 を作る."""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

TOPICS = [
    "心停止・蘇生",
    "BLS・バイスタンダーCPR",
    "AED・除細動",
    "熱中症",
    "病院前救急・EMS体制",
    "通報・指令",
    "AI・デジタル",
    "集中治療",
    "外傷",
    "その他",
]

DESIGNS = [
    "RCT", "コホート研究", "症例対照研究", "横断研究", "SR・メタ解析", "レビュー",
    "質的研究", "診断・予測モデル", "経済評価", "ガイドライン・声明", "その他",
]

SYSTEM = f"""あなたは病院前救急医療・蘇生科学・熱中症・集中治療を専門とする医学研究者です。
英語の医学論文を、日本の救急救命士・研究者向けに正確な日本語へまとめます。

訳語のルール:
- out-of-hospital cardiac arrest (OHCA) → 院外心停止(OHCA)
- return of spontaneous circulation (ROSC) → 自己心拍再開(ROSC)
- bystander CPR → バイスタンダーCPR / dispatcher-assisted CPR → 口頭指導CPR
- emergency medical services (EMS) → 救急医療サービス(EMS) / paramedic → 救急救命士(パラメディック)
- favorable neurological outcome → 神経学的転帰良好 / exertional heat stroke → 労作性熱中症
- 数値・信頼区間・P値・略語は原文どおり残す。推測で情報を足さない。

必ず次の JSON だけを出力してください(前後に文章やコードブロックを付けない):
{{
  "title_ja": "日本語タイトル",
  "points": ["何を調べたか(目的)", "どう調べたか(デザイン・対象・n)", "何が分かったか(主な結果を数値つきで)"],
  "abstract_ja": "アブストラクトの全訳。見出し(背景/方法/結果/結論 など)があれば【背景】のように残す",
  "topics": ["次から1〜3個: {' / '.join(TOPICS)}"],
  "design": "次から1つ: {' / '.join(DESIGNS)}",
  "relevant": true
}}
"relevant" は、この論文が「院外心停止・蘇生・BLS・AED・熱中症・病院前救急/EMS・救急指令・病院前のAI/デジタル・救急/集中治療」の研究者にとって関係があれば true、キーワードが偶然一致しただけ(例: 別分野の略語 EMS、心臓手術中の心停止のみ等)なら false。
抄録がない場合は points をタイトルから分かる範囲で書き、abstract_ja は「(抄録なし)」とする。"""


def _user_msg(p: dict) -> str:
    return (
        f"Journal: {p['journal']}\n"
        f"Publication type: {', '.join(p.get('pub_types', []))}\n"
        f"Title: {p['title']}\n\n"
        f"Abstract:\n{p['abstract'] or '(no abstract)'}"
    )


def _parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("JSON not found")
    d = json.loads(m.group(0))
    d["topics"] = [t for t in d.get("topics", []) if t in TOPICS] or ["その他"]
    if d.get("design") not in DESIGNS:
        d["design"] = "その他"
    d["points"] = list(d.get("points", []))[:3]
    d["relevant"] = bool(d.get("relevant", True))
    return d


def _summarize_one(client, model: str, p: dict) -> dict:
    last_err = None
    for attempt in range(4):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=4000,
                system=SYSTEM,
                messages=[{"role": "user", "content": _user_msg(p)}],
            )
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            return _parse(text)
        except Exception as e:  # noqa: BLE001  通信・JSON 崩れはリトライ
            last_err = e
            time.sleep(5 * (attempt + 1))
    print(f"  [warn] 要約失敗 PMID {p['pmid']}: {last_err}")
    return {
        "title_ja": "", "points": ["(要約の生成に失敗しました。原文をご確認ください)"],
        "abstract_ja": "", "topics": ["その他"], "design": "その他", "relevant": True,
    }


def summarize_all(papers: list[dict], model: str, client=None, workers: int = 4) -> list[dict]:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY を環境変数から読む
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda p: _summarize_one(client, model, p), papers))
    for p, s in zip(papers, results):
        p.update(s)
    return papers
