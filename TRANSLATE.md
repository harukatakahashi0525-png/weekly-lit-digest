# 和訳の手順(毎週月曜朝、Claude のスケジュールタスクが読む)

GitHub Actions が日曜夜に PubMed から新着を取得し、`inbox/pending.json` に入れています。
これを和訳・要約してダッシュボードを更新し、push するとメールが自動送信されます。

## 手順

```bash
pip install --break-system-packages -q -r requirements.txt
python -m digest.main status          # 未訳の件数を確認。0 件なら build へ
python -m digest.main next 8          # 次の 8 本を表示(英語のタイトル・抄録)
```

表示された論文それぞれについて、下の「和訳のルール」どおりの JSON を作り、
**8 本分を JSON 配列にしてファイルに書き**、保存する:

```bash
python -m digest.main save /tmp/batch.json   # 検証して inbox/summaries.json に追記。残り件数が出る
```

`next` → 和訳 → `save` を残り 0 件になるまで繰り返す(途中で止まっても、保存済みの分は残る)。
最後に:

```bash
python -m digest.main build           # メール本文とダッシュボードを作り、inbox を空にする
git add -A && git commit -m "digest: 和訳 $(date +%F)" && git push
```

push すると `outbox/` の変更をきっかけに GitHub がメールを送ります。

## 和訳のルール

あなたは病院前救急医療・蘇生科学・熱中症・集中治療を専門とする医学研究者として、
日本の救急救命士・研究者向けに正確な日本語でまとめる。

1 本につき次の形(キーはすべて必須):

```json
{
  "pmid": "12345678",
  "title_ja": "日本語タイトル",
  "points": ["目的: 何を調べたか(1文)", "方法: デザイン・対象・n", "結果: 主な結果を数値つきで"],
  "abstract_ja": "抄録の全訳。見出しがあれば【背景】【方法】【結果】【結論】のように残す",
  "topics": ["下の一覧から1〜3個"],
  "design": "下の一覧から1つ",
  "relevant": true
}
```

- points の各文頭に「目的:」などは付けない(表示側で付く)
- topics: 心停止・蘇生 / BLS・バイスタンダーCPR / AED・除細動 / 熱中症 / 病院前救急・EMS体制 / 通報・指令 / AI・デジタル / 集中治療 / 外傷 / その他
- design: RCT / コホート研究 / 症例対照研究 / 横断研究 / SR・メタ解析 / レビュー / 質的研究 / 診断・予測モデル / 経済評価 / ガイドライン・声明 / その他
- relevant: 院外心停止・蘇生・BLS・AED・熱中症・病院前救急/EMS・救急指令・病院前の AI/デジタル・救急/集中治療の研究者に関係があれば true。
  キーワードが偶然一致しただけ(別分野の略語 EMS、心臓手術中の心停止のみ 等)なら false。迷ったら true
- 抄録がない論文は、points をタイトルから分かる範囲で書き、abstract_ja は「(抄録なし)」

訳語:
- out-of-hospital cardiac arrest (OHCA) → 院外心停止(OHCA)
- return of spontaneous circulation (ROSC) → 自己心拍再開(ROSC)
- bystander CPR → バイスタンダーCPR / dispatcher-assisted CPR → 口頭指導CPR
- emergency medical services (EMS) → 救急医療サービス(EMS) / paramedic → 救急救命士(パラメディック)
- favorable neurological outcome → 神経学的転帰良好 / exertional heat stroke → 労作性熱中症
- 数値・信頼区間・P 値・略語は原文どおり残す。推測で情報を足さない
