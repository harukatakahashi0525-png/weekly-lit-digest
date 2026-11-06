"""週刊文献ダイジェスト(Claude API なし版).

  python -m digest.main fetch        # [GitHub Actions] PubMed から新着を取得 → inbox/pending.json
  python -m digest.main status       # [Claude] 未訳の件数
  python -m digest.main next 8       # [Claude] 次に和訳する論文を表示
  python -m digest.main save F.json  # [Claude] 和訳(JSON 配列)を保存
  python -m digest.main build        # [Claude] メール本文・ダッシュボードを作成し inbox を空にする
  python -m digest.main send         # [GitHub Actions] outbox/ のメールを Gmail で送信
  python -m digest.main selftest     # ネットなしでサンプルを使った通しテスト
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from .schema import TOPICS, normalize

ROOT = Path(__file__).resolve().parent.parent
BASE = Path(os.getenv("DIGEST_BASE", ROOT))  # selftest 時は一時フォルダ
JST = timezone(timedelta(hours=9))
TIER_ORDER = {"all": 0, "filtered": 1, "any": 2}


def P(rel: str) -> Path:
    return BASE / rel


def load(rel: str, default):
    p = P(rel)
    return json.loads(p.read_text("utf-8")) if p.exists() else default


def dump(rel: str, obj) -> None:
    p = P(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), "utf-8")


def cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text("utf-8"))


def today():
    return datetime.now(JST).date()


# ------------------------------------------------------------------ fetch
def cmd_fetch(mock: bool = False) -> None:
    c = cfg()
    db = load("docs/data/papers.json", {"papers": []})
    pending = load("inbox/pending.json", [])
    seen = set(load("state/seen.json", [])) | {p["pmid"] for p in db["papers"]} | {p["pmid"] for p in pending}

    if mock:
        from . import mock as mk
        new = [p for p in mk.papers() if p["pmid"] not in seen]
    else:
        from . import pubmed
        new = pubmed.fetch_new(c, seen, today())

    new.sort(key=lambda p: TIER_ORDER.get(p["tier"], 9))
    anys = [p for p in new if p["tier"] == "any"]
    cap = int(c.get("any_journal_max", 40))
    if len(anys) > cap:
        drop = {p["pmid"] for p in anys[cap:]}
        new = [p for p in new if p["pmid"] not in drop]

    pending += new
    pending.sort(key=lambda p: TIER_ORDER.get(p["tier"], 9))
    dump("inbox/pending.json", pending)
    print(f"新着 {len(new)} 本を追加(未処理 計 {len(pending)} 本)")


# ------------------------------------------------------------------ translate helpers
def _todo() -> list[dict]:
    c = cfg()
    pending = load("inbox/pending.json", [])
    done = load("inbox/summaries.json", {})
    limit = int(c.get("max_translate_per_week", 60))
    return [p for p in pending[:limit] if p["pmid"] not in done]


def cmd_status() -> None:
    pending = load("inbox/pending.json", [])
    done = load("inbox/summaries.json", {})
    todo = _todo()
    print(f"取得済み {len(pending)} 本 / 和訳済み {len(done)} 本 / 残り {len(todo)} 本"
          f"(上限 {cfg().get('max_translate_per_week', 60)} 本)")


def cmd_next(n: int) -> None:
    todo = _todo()
    if not todo:
        print("残り 0 本。build に進んでください。")
        return
    for p in todo[:n]:
        print(json.dumps({
            "pmid": p["pmid"], "tier": p["tier"], "journal": p["journal"],
            "pub_types": p.get("pub_types", []), "title": p["title"],
            "abstract": p["abstract"] or "(no abstract)",
        }, ensure_ascii=False))
        print()
    print(f"--- 表示 {min(n, len(todo))} 本 / 残り {len(todo)} 本 ---")


def cmd_save(path: str) -> None:
    raw = json.loads(Path(path).read_text("utf-8"))
    if isinstance(raw, dict):
        raw = [raw]
    done = load("inbox/summaries.json", {})
    ok, errs = 0, []
    for d in raw:
        try:
            s = normalize(d)
            done[s["pmid"]] = s
            ok += 1
        except ValueError as e:
            errs.append(str(e))
    dump("inbox/summaries.json", done)
    print(f"保存 {ok} 本。残り {len(_todo())} 本")
    for e in errs:
        print("  エラー:", e)
    if errs:
        sys.exit(1)


# ------------------------------------------------------------------ build
def _authors_short(a: list[str]) -> str:
    return ", ".join(a[:3]) + (" et al." if len(a) > 3 else "") if a else ""


def cmd_build() -> None:
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    c = cfg()
    week = today().isoformat()
    pending = load("inbox/pending.json", [])
    done = load("inbox/summaries.json", {})

    papers, dropped = [], 0
    for p in pending:
        s = done.get(p["pmid"])
        if s:
            if c.get("drop_irrelevant", True) and p["tier"] != "all" and not s["relevant"]:
                dropped += 1
                continue
            p.update(s)
        else:  # 上限超えなどで未訳
            p.update({"title_ja": "", "points": [], "abstract_ja": "", "topics": ["未翻訳(タイトルのみ)"],
                      "design": "未翻訳"})
        p["authors_short"] = _authors_short(p.get("authors", []))
        p["week"] = week
        papers.append(p)

    groups = []
    for t in TOPICS + ["未翻訳(タイトルのみ)"]:
        ps = [p for p in papers if p["topics"][0] == t]
        if ps:
            ps.sort(key=lambda p: (TIER_ORDER.get(p["tier"], 9), p["journal"]))
            groups.append({"topic": t, "papers": ps})

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html", "j2"]))
    html = env.get_template("email.html.j2").render(
        week=week, total=len(papers), groups=groups,
        since=(today() - timedelta(days=int(c.get("lookback_days", 8)))).isoformat(), until=week,
        dashboard_url=c.get("dashboard_url", ""),
    )
    P("outbox").mkdir(parents=True, exist_ok=True)
    P("outbox/email.html").write_text(html, "utf-8")
    P("outbox/subject.txt").write_text(f"{c.get('mail_subject_prefix', '')}{week} 新着 {len(papers)} 本", "utf-8")

    keep_full = bool(c.get("publish_full_abstract", False))
    fields = ["pmid", "week", "tier", "journal", "journal_full", "pubdate", "title", "title_ja",
              "points", "topics", "design", "authors_short", "doi"] + (["abstract_ja"] if keep_full else [])
    db = load("docs/data/papers.json", {"papers": []})
    db["papers"] = [{k: p.get(k) for k in fields} for p in papers] + db["papers"]
    db["updated"] = datetime.now(JST).isoformat(timespec="minutes")
    db["weeks"] = sorted({p["week"] for p in db["papers"]}, reverse=True)
    dump("docs/data/papers.json", db)

    seen = set(load("state/seen.json", [])) | {p["pmid"] for p in pending}
    dump("state/seen.json", sorted(seen))
    dump("inbox/pending.json", [])
    dump("inbox/summaries.json", {})
    print(f"メール本文を作成: {len(papers)} 本(無関係として除外 {dropped} 本)。ダッシュボード累計 {len(db['papers'])} 本")


# ------------------------------------------------------------------ send
def cmd_send() -> None:
    if not (os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD")):
        print("GMAIL_ADDRESS / GMAIL_APP_PASSWORD が未設定のため、メール送信をスキップします")
        return
    from .mailer import send
    subject = P("outbox/subject.txt").read_text("utf-8").strip()
    html = P("outbox/email.html").read_text("utf-8")
    send(subject, html, "HTML 対応のメールソフトでご覧ください。")
    print("送信しました:", subject)


# ------------------------------------------------------------------ selftest
def cmd_selftest() -> None:
    import shutil
    import subprocess
    import tempfile

    from . import mock as mk
    tmp = Path(tempfile.mkdtemp())
    env = {**os.environ, "DIGEST_BASE": str(tmp)}
    run = lambda *a: subprocess.run([sys.executable, "-m", "digest.main", *a], env=env, cwd=ROOT, check=True)  # noqa: E731
    run("fetch", "--mock")
    run("next", "3")
    batch = tmp / "batch.json"
    batch.write_text(json.dumps(mk.fake_summaries(), ensure_ascii=False), "utf-8")
    run("save", str(batch))
    run("status")
    run("build")
    run("fetch", "--mock")  # 2 回目は重複なしで 0 本になるはず
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    shutil.copy(tmp / "outbox/email.html", out / "email.html")
    shutil.copy(tmp / "docs/data/papers.json", out / "papers.json")
    print("OK: output/email.html と output/papers.json を確認してください")


def main():
    a = sys.argv[1:] or ["status"]
    cmd = a[0]
    if cmd == "fetch":
        cmd_fetch(mock="--mock" in a)
    elif cmd == "status":
        cmd_status()
    elif cmd == "next":
        cmd_next(int(a[1]) if len(a) > 1 else 8)
    elif cmd == "save":
        cmd_save(a[1])
    elif cmd == "build":
        cmd_build()
    elif cmd == "send":
        cmd_send()
    elif cmd == "selftest":
        cmd_selftest()
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
