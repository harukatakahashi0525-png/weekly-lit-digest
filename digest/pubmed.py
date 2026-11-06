"""PubMed (NCBI E-utilities) から新着論文を検索・取得する."""
from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET
from datetime import date, timedelta

import requests

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
_session = requests.Session()


def _common_params() -> dict:
    p = {"tool": "weekly-lit-digest"}
    if os.getenv("NCBI_EMAIL"):
        p["email"] = os.environ["NCBI_EMAIL"]
    if os.getenv("NCBI_API_KEY"):
        p["api_key"] = os.environ["NCBI_API_KEY"]
    return p


def _sleep():
    # API キーなし: 3 件/秒、あり: 10 件/秒
    time.sleep(0.12 if os.getenv("NCBI_API_KEY") else 0.4)


def _or(terms: list[str], field: str) -> str:
    return "(" + " OR ".join(f'"{t}"[{field}]' for t in terms) + ")"


def build_queries(cfg: dict) -> dict[str, str]:
    """tier 名 -> PubMed 検索式."""
    q = {}
    if cfg.get("journals_all"):
        q["all"] = _or(cfg["journals_all"], "ta")
    if cfg.get("journals_filtered") and cfg.get("keywords"):
        q["filtered"] = f'{_or(cfg["journals_filtered"], "ta")} AND {_or(cfg["keywords"], "tiab")}'
    if cfg.get("title_keywords_any_journal"):
        q["any"] = f'{_or(cfg["title_keywords_any_journal"], "ti")} AND english[lang]'
    return q


def esearch(term: str, mindate: date, maxdate: date) -> list[str]:
    params = {
        **_common_params(),
        "db": "pubmed",
        "term": term,
        "datetype": "edat",  # PubMed に登録された日(早期公開も拾える)
        "mindate": mindate.strftime("%Y/%m/%d"),
        "maxdate": maxdate.strftime("%Y/%m/%d"),
        "retmax": 2000,
        "retmode": "json",
        "sort": "pub_date",
    }
    r = _session.get(f"{EUTILS}/esearch.fcgi", params=params, timeout=60)
    r.raise_for_status()
    _sleep()
    return r.json()["esearchresult"].get("idlist", [])


def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def parse_efetch(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    out = []
    for art in root.findall(".//PubmedArticle"):
        mc = art.find("MedlineCitation")
        a = mc.find("Article")
        pmid = _text(mc.find("PMID"))

        parts = []
        for at in a.findall("Abstract/AbstractText"):
            label = at.get("Label")
            txt = _text(at)
            if txt:
                parts.append(f"{label}: {txt}" if label else txt)
        abstract = "\n".join(parts)

        authors = []
        for au in a.findall("AuthorList/Author"):
            last, ini = _text(au.find("LastName")), _text(au.find("Initials"))
            coll = _text(au.find("CollectiveName"))
            if last:
                authors.append(f"{last} {ini}".strip())
            elif coll:
                authors.append(coll)

        doi = ""
        for aid in art.findall("PubmedData/ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = _text(aid)
        if not doi:
            for el in a.findall("ELocationID"):
                if el.get("EIdType") == "doi":
                    doi = _text(el)

        pd = a.find("Journal/JournalIssue/PubDate")
        pubdate = " ".join(
            x for x in (_text(pd.find("Year")), _text(pd.find("Month")), _text(pd.find("Day"))) if x
        ) or _text(pd.find("MedlineDate")) if pd is not None else ""

        out.append({
            "pmid": pmid,
            "title": _text(a.find("ArticleTitle")),
            "abstract": abstract,
            "authors": authors,
            "journal": _text(a.find("Journal/ISOAbbreviation")) or _text(mc.find("MedlineJournalInfo/MedlineTA")),
            "journal_full": _text(a.find("Journal/Title")),
            "pubdate": pubdate,
            "doi": doi,
            "pub_types": [_text(p) for p in a.findall("PublicationTypeList/PublicationType")],
        })
    return out


def efetch(pmids: list[str]) -> list[dict]:
    records = []
    for i in range(0, len(pmids), 200):
        chunk = pmids[i:i + 200]
        data = {**_common_params(), "db": "pubmed", "id": ",".join(chunk), "retmode": "xml"}
        r = _session.post(f"{EUTILS}/efetch.fcgi", data=data, timeout=120)
        r.raise_for_status()
        records.extend(parse_efetch(r.text))
        _sleep()
    return records


def fetch_new(cfg: dict, seen: set[str], today: date) -> list[dict]:
    """全 tier を検索し、未掲載・除外対象外の論文を返す(tier 付き)."""
    mindate = today - timedelta(days=int(cfg.get("lookback_days", 8)))
    tier_of: dict[str, str] = {}
    for tier, term in build_queries(cfg).items():
        for pmid in esearch(term, mindate, today):
            # 先に当たった tier を優先(all > filtered > any)
            tier_of.setdefault(pmid, tier)

    new_ids = [p for p in tier_of if p not in seen]
    if not new_ids:
        return []

    excl = set(cfg.get("exclude_publication_types") or [])
    papers = []
    for rec in efetch(new_ids):
        if excl & set(rec["pub_types"]):
            continue
        rec["tier"] = tier_of.get(rec["pmid"], "any")
        papers.append(rec)
    return papers
