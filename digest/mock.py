"""--mock 用のサンプルデータ(レイアウト確認用の架空の論文。実在しません)."""
from __future__ import annotations

from .pubmed import parse_efetch

_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
{articles}
</PubmedArticleSet>"""

_ART = """<PubmedArticle><MedlineCitation><PMID>{pmid}</PMID><Article>
<Journal><JournalIssue><PubDate><Year>2026</Year><Month>Nov</Month></PubDate></JournalIssue>
<Title>{jfull}</Title><ISOAbbreviation>{j}</ISOAbbreviation></Journal>
<ArticleTitle>{title}</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND">Sample background text.</AbstractText>
<AbstractText Label="RESULTS">Sample results text.</AbstractText></Abstract>
<AuthorList><Author><LastName>Sample</LastName><Initials>A</Initials></Author>
<Author><LastName>Example</LastName><Initials>B</Initials></Author>
<Author><LastName>Demo</LastName><Initials>C</Initials></Author>
<Author><LastName>Test</LastName><Initials>D</Initials></Author></AuthorList>
<PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
</Article></MedlineCitation>
<PubmedData><ArticleIdList><ArticleId IdType="doi">10.0000/sample.{pmid}</ArticleId></ArticleIdList></PubmedData>
</PubmedArticle>"""

_ROWS = [
    ("90000001", "Resuscitation", "Resuscitation", "[SAMPLE] Bystander CPR by patient sex in out-of-hospital cardiac arrest", "all",
     ["BLS・バイスタンダーCPR", "心停止・蘇生"], "コホート研究", True),
    ("90000002", "Prehosp Emerg Care", "Prehospital emergency care", "[SAMPLE] Prehospital cooling for exertional heat stroke", "all",
     ["熱中症", "病院前救急・EMS体制"], "RCT", True),
    ("90000003", "JAMA Netw Open", "JAMA network open", "[SAMPLE] Machine learning to recognise cardiac arrest during emergency calls", "filtered",
     ["AI・デジタル", "通報・指令"], "診断・予測モデル", True),
    ("90000004", "Crit Care Med", "Critical care medicine", "[SAMPLE] Unrelated EMS abbreviation study (should be dropped)", "filtered",
     ["その他"], "その他", False),
    ("90000005", "Resusc Plus", "Resuscitation plus", "[SAMPLE] Public-access AED coverage and drone delivery", "all",
     ["AED・除細動"], "横断研究", True),
]


def papers() -> list[dict]:
    xml = _XML.format(articles="\n".join(_ART.format(pmid=r[0], j=r[1], jfull=r[2], title=r[3]) for r in _ROWS))
    recs = parse_efetch(xml)
    tiers = {r[0]: r[4] for r in _ROWS}
    for r in recs:
        r["tier"] = tiers[r["pmid"]]
    return recs


def fake_summaries() -> list[dict]:
    """和訳のサンプル(最後の 1 本はわざと未訳のまま残す)."""
    out = []
    for r in _ROWS[:-1]:
        out.append({
            "pmid": r[0],
            "title_ja": "【サンプル】" + r[3].replace("[SAMPLE] ", "") + "(日本語タイトルがここに入ります)",
            "points": [
                "ここに「何を調べたか」が1文で入ります。",
                "ここに研究デザイン・対象・人数が入ります(例: 多施設コホート、n=12,345)。",
                "ここに主な結果が数値つきで入ります(例: 調整OR 1.23[95%CI 1.05–1.44])。",
            ],
            "abstract_ja": "【背景】ここにアブストラクトの全訳が入ります。\n【方法】……\n【結果】……\n【結論】……",
            "topics": r[5], "design": r[6], "relevant": r[7],
        })
    return out
