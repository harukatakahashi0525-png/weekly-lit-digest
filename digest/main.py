"""週刊文献ダイジェスト 本体.

  python -m digest.main              # 本番(PubMed 取得 → 要約 → メール送信 → ダッシュボード更新)
  python -m digest.main --dry-run    # メールを送らず output/email.html に書き出すだけ
  python -m digest.main --mock       # ネットも API も使わずサンプルデータで動作確認
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import pubmed
from .summarize import TOPICS, summarize_all

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data" / "papers.json"
SEEN = ROOT / "state" / "seen.json"
OUT = ROOT / "output"
JST = timezone(timedelta(hours=9))
TIER_ORDER = {"all": 0, "filtered": 1, "any": 2}


def load_json(path: Path, default):
    return json.loads(path.read_text("utf-8")) if path.exists() else default


def authors_short(authors: list[str]) -> str:
    if not authors:
        return ""
    return ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")


def group_by_topic(papers: list[dict]) -> list[dict]:
    groups = []
    for t in TOPICS:
        ps = [p for p in papers if p["topics"][0] == t]
        if ps:
            ps.sort(key=lambda p: (TIER_ORDER.get(p["tier"], 9), p["journal"]))
            groups.append({"topic": t, "papers": ps})
    return groups


def plain_text(week: str, groups: list[dict]) -> str:
    lines = [f"週刊 文献ダイジェスト {week}", ""]
    for g in groups:
        lines.append(f"■ {g['topic']}")
        for p in g["papers"]:
            lines += [f"- {p.get('title_ja') or p['title']}", f"  {p['journal']}  https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/"]
        lines.append("")
    return "\n".join(lines)


def run(dry_run: bool, mock: bool) -> None:
    global DATA, SEEN
    if mock:  # 本番データを汚さないよう、サンプル実行は output/ に書く
        DATA, SEEN = OUT / "mock" / "papers.json", OUT / "mock" / "seen.json"
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text("utf-8"))
    today = datetime.now(JST).date()
    week = today.isoformat()

    db = load_json(DATA, {"updated": "", "papers": []})
    seen = set(load_json(SEEN, []))
    seen |= {p["pmid"] for p in db["papers"]}

    # 1) 取得
    if mock:
        from . import mock as mk
        papers = [p for p in mk.papers() if p["pmid"] not in seen]
    else:
        papers = pubmed.fetch_new(cfg, seen, today)
    print(f"新着候補: {len(papers)} 本")

    # 2) 要約・翻訳
    if papers:
        client = None
        if mock:
            from . import mock as mk
            client = mk.FakeClient()
        summarize_all(papers, cfg.get("claude_model", "claude-sonnet-5-5"), client=client)

    # 3) 無関係なものを除外、③の上限
    fetched_ids = [p["pmid"] for p in papers]
    if cfg.get("drop_irrelevant", True):
        dropped = [p for p in papers if p["tier"] != "all" and not p["relevant"]]
        papers = [p for p in papers if p not in dropped]
        print(f"無関係として除外: {len(dropped)} 本")
    anys = [p for p in papers if p["tier"] == "any"]
    cap = int(cfg.get("any_journal_max", 40))
    if len(anys) > cap:
        drop = {p["pmid"] for p in anys[cap:]}
        papers = [p for p in papers if p["pmid"] not in drop]

    for p in papers:
        p["authors_short"] = authors_short(p["authors"])
        p["week"] = week

    # 4) メール
    groups = group_by_topic(papers)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html", "j2"]))
    html = env.get_template("email.html.j2").render(
        week=week, total=len(papers), groups=groups,
        since=(today - timedelta(days=int(cfg.get("lookback_days", 8)))).isoformat(), until=week,
        dashboard_url=cfg.get("dashboard_url", ""),
    )
    OUT.mkdir(exist_ok=True)
    (OUT / "email.html").write_text(html, "utf-8")
    subject = f"{cfg.get('mail_subject_prefix', '')}{week} 新着 {len(papers)} 本"
    if dry_run or mock:
        print(f"[dry-run] メールは送らず output/email.html に保存: {subject}")
    else:
        from .mailer import send
        send(subject, html, plain_text(week, groups))
        print(f"メール送信: {subject}")

    # 5) ダッシュボード用データ更新(公開されるので英文抄録は載せない)
    keep_full = bool(cfg.get("publish_full_abstract", False))
    fields = ["pmid", "week", "tier", "journal", "journal_full", "pubdate", "title", "title_ja",
              "points", "topics", "design", "authors_short", "doi"] + (["abstract_ja"] if keep_full else [])
    new_rows = [{k: p.get(k) for k in fields} for p in papers]
    db["papers"] = new_rows + db["papers"]
    db["updated"] = datetime.now(JST).isoformat(timespec="minutes")
    db["weeks"] = sorted({p["week"] for p in db["papers"]}, reverse=True)
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(db, ensure_ascii=False, indent=1), "utf-8")

    # 除外したものも「処理済み」にして、翌週また要約しないようにする
    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text(json.dumps(sorted(seen | set(fetched_ids)), indent=0), "utf-8")
    print(f"ダッシュボード: 累計 {len(db['papers'])} 本")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mock", action="store_true")
    a = ap.parse_args()
    run(a.dry_run, a.mock)


if __name__ == "__main__":
    main()
