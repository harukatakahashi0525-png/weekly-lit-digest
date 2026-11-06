"""和訳データの形(分類の選択肢と、受け取った和訳の整形)."""
from __future__ import annotations

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


def normalize(d: dict) -> dict:
    """和訳 1 件を検証・整形する。必須キーがなければ ValueError."""
    if not d.get("pmid"):
        raise ValueError("pmid がありません")
    pts = [str(x) for x in (d.get("points") or [])][:3]
    if len(pts) < 3:
        raise ValueError(f"PMID {d['pmid']}: points は 3 つ必要です")
    return {
        "pmid": str(d["pmid"]),
        "title_ja": str(d.get("title_ja", "")).strip(),
        "points": pts,
        "abstract_ja": str(d.get("abstract_ja", "")).strip(),
        "topics": [t for t in (d.get("topics") or []) if t in TOPICS][:3] or ["その他"],
        "design": d.get("design") if d.get("design") in DESIGNS else "その他",
        "relevant": bool(d.get("relevant", True)),
    }
