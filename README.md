# 週刊 文献ダイジェスト(Claude API なし版)

関連ジャーナルの新着論文を毎週集め、**日本語タイトル・3行要点(目的/方法/結果)・アブストラクト全訳** を付けて
メールとダッシュボードで届けます。和訳は Claude のプラン内(スケジュールタスク)で行うので、API キーは不要です。

```
日曜 22:00  GitHub が PubMed から新着を取得 → inbox/pending.json   (.github/workflows/fetch.yml)
月曜 朝     Claude のスケジュールタスクが和訳 → ダッシュボード更新 → push   (TRANSLATE.md の手順)
            push をきっかけに GitHub が Gmail でメール送信          (.github/workflows/send.yml)
```

ダッシュボード: https://harukatakahashi0525-png.github.io/weekly-lit-digest/

## 拾う論文(config.yaml で変更可)

| 区分 | 対象 | 取り方 |
|---|---|---|
| ① 全件 | Resuscitation, Resuscitation Plus, Prehospital Emergency Care, Scand J Trauma Resusc Emerg Med, Emerg Med J, Acute Medicine & Surgery | 新着をすべて |
| ② キーワード | JAMA, JAMA Netw Open, Circulation, Critical Care, Crit Care Med, Ann Emerg Med, NEJM, Lancet | 心停止・CPR・AED・バイスタンダー・熱中症・EMS・救急救命士・病院前・救急車・指令 など |
| ③ 全誌 | 上記以外のすべての雑誌 | タイトルに OHCA・バイスタンダーCPR・熱中症・EMS・paramedic(週 40 本まで) |

- 和訳は週 60 本まで(①→②→③の順)。超えた分はタイトルとリンクだけ載ります(`max_translate_per_week`)
- ②③で「キーワードが偶然一致しただけ」のものは除外します
- 訂正記事・コメント・エディトリアル・ニュースは除外します

## GitHub 側の設定(1 回だけ)

1. **Settings → Actions → General → Workflow permissions** を **Read and write permissions** にして Save
2. **Settings → Pages** で Branch を **main** / **/docs** にして Save
3. メールも受け取る場合: Gmail の **アプリパスワード**(https://myaccount.google.com/apppasswords、2 段階認証が必要)を作り、
   **Settings → Secrets and variables → Actions → New repository secret** で
   `GMAIL_ADDRESS`(Gmail アドレス)と `GMAIL_APP_PASSWORD`(16 文字)を登録。
   未登録ならメールは送らず、ダッシュボードだけ更新されます

## よくある変更

`config.yaml` を編集するだけです(Claude にチャットで頼めば直接直します)。

- ジャーナル: `journals_all` / `journals_filtered`(PubMed 略誌名)
- キーワード: `keywords`(②)、`title_keywords_any_journal`(③、不要なら `[]`)
- 和訳の上限: `max_translate_per_week`
- 取得の曜日・時刻: `.github/workflows/fetch.yml` の `cron`(UTC。日本時間 −9 時間)

## 手動で動かす

- 今すぐ取得: **Actions → ① 新着論文を取得 → Run workflow**
- メール再送: **Actions → ② メールを送信 → Run workflow**
- 手元でのテスト: `pip install -r requirements.txt && python -m digest.main selftest`

※ 要約・翻訳は Claude による自動生成です。数値や結論は必ず原文で確認してください。
