# 週刊 文献ダイジェスト

毎週月曜 8:00(日本時間)に、指定ジャーナル・テーマの新着論文を PubMed から集め、
**日本語タイトル・3行要点(目的/方法/結果)・アブストラクト全訳** を付けてメールで届けます。
同じ内容が、検索・ブックマークできる **ダッシュボード(Web ページ)** にも毎週たまっていきます。

```
PubMed 検索 → Claude で要約・翻訳 → Gmail で送信
                                  └→ ダッシュボード(GitHub Pages)を更新
```

すべて GitHub 上で自動実行されるので、PC の電源が切れていても届きます。

---

## 拾う論文(config.yaml で変更可)

| 区分 | 対象 | 取り方 |
|---|---|---|
| ① 全件 | Resuscitation, Resuscitation Plus, Prehospital Emergency Care, Scand J Trauma Resusc Emerg Med, Emerg Med J, Acute Medicine & Surgery | 新着をすべて |
| ② キーワード | JAMA, JAMA Netw Open, Circulation, Critical Care, Crit Care Med, Ann Emerg Med, NEJM, Lancet | 心停止・CPR・AED・バイスタンダー・熱中症・EMS・救急救命士・病院前・救急車・指令 などがタイトル/抄録にあるもの |
| ③ 全誌 | 上記以外のすべての雑誌 | タイトルに OHCA・バイスタンダーCPR・熱中症・EMS・paramedic を含むもの(週 40 本まで) |

- ②③は、Claude が「キーワードが偶然一致しただけ」と判断したものを自動で外します。
- 訂正記事・コメント・エディトリアル・ニュースは除外します。
- 「AI in prehospital」の論文は ②③ で拾い、「AI・デジタル」タグを付けます。

---

## 初回の設定(30 分ほど・1 回だけ)

### 1. 必要なものを用意する

| 必要なもの | 取得先 | 備考 |
|---|---|---|
| GitHub アカウント | https://github.com | 無料 |
| Anthropic API キー | https://console.anthropic.com → API Keys | 従量課金。事前にクレジット購入が必要 |
| Gmail のアプリパスワード | https://myaccount.google.com/apppasswords | Google アカウントの **2 段階認証をオン** にしてから作成。16 桁 |
| (任意)NCBI API キー | https://www.ncbi.nlm.nih.gov/account/settings/ | なくても動きます。あると PubMed 取得が速く安定 |

### 2. GitHub にリポジトリを作ってファイルを入れる

1. GitHub 右上「+」→ **New repository**
   - 名前: 例 `weekly-lit-digest`
   - **Public** を選ぶ(無料プランでダッシュボードを公開するため。下の「公開範囲」参照)
2. 作成後の画面で **uploading an existing file** をクリック。zip を解凍してできた `weekly-lit-digest` フォルダを開き、**その中身をすべて**(`weekly-lit-digest` フォルダそのものではなく)ドラッグ&ドロップ → **Commit changes**
   - ⚠️ `.github` フォルダは「隠しフォルダ」です。Mac の Finder では **⌘ + Shift + .(ピリオド)** で表示させてから一緒にドラッグしてください
   - うまく入らない場合: **Add file → Create new file** でファイル名に `.github/workflows/weekly.yml` と入力し、同名ファイルの中身を貼り付け

### 3. 鍵(Secrets)を登録する

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で、次を 1 つずつ登録:

| Name | 値 |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic の API キー |
| `GMAIL_ADDRESS` | 送信元の Gmail アドレス |
| `GMAIL_APP_PASSWORD` | 16 桁のアプリパスワード(スペースなし) |
| `MAIL_TO` | (任意)送信先。複数ならカンマ区切り。省略すると自分宛て |
| `NCBI_API_KEY` | (任意)NCBI の API キー |

### 4. 書き込み権限をオンにする

**Settings → Actions → General → Workflow permissions** で **Read and write permissions** を選び **Save**。
(ダッシュボードのデータを毎週自動で更新するため)

### 5. ダッシュボードを公開する

1. **Settings → Pages** → Source を **Deploy from a branch**、Branch を **main** / **/docs** にして **Save**
2. 数分後に表示される URL(`https://ユーザー名.github.io/weekly-lit-digest/`)をコピー
3. `config.yaml` の `dashboard_url: ""` にその URL を貼って保存(GitHub 上で鉛筆アイコンから編集できます)
   → メール冒頭に「ダッシュボードで見る」ボタンが付きます

### 6. 試しに動かす

1. **Actions** タブ → 左の **週刊文献ダイジェスト** → 右の **Run workflow**
2. まず **「メールを送らずに試す」にチェック** して実行 → 完了後、実行結果ページ下部の **email-preview** をダウンロードして中身を確認
3. 問題なければ、チェックを外してもう一度実行 → メールが届けば完了

以降は毎週月曜 8:00 に自動で届きます(GitHub の混雑で数十分遅れることがあります)。

---

## よくある変更

すべて `config.yaml` を編集して保存するだけです。

- **ジャーナルを増やす/減らす**: `journals_all` か `journals_filtered` に PubMed の略誌名を追加/削除
  (略誌名は https://www.ncbi.nlm.nih.gov/nlmcatalog/journals で確認)
- **キーワードを変える**: `keywords`(②用)、`title_keywords_any_journal`(③用)
- **③をやめる**: `title_keywords_any_journal: []`
- **費用を抑える**: `claude_model: claude-haiku-5-5`(精度はやや下がります)
- **配信曜日・時刻を変える**: `.github/workflows/weekly.yml` の `cron`(UTC 表記。日本時間 −9 時間)

---

## 公開範囲について

- 無料プランの GitHub Pages は **リポジトリを Public にする必要があります**。URL を知っていれば誰でも見られます(検索エンジンには載らない設定にしてあります)。
- 抄録は出版社の著作物なので、初期設定では **ダッシュボードには「日本語タイトル・3行要点・リンク」だけ** を載せ、**アブストラクト全訳はメールだけ** に載せています。
  自分専用と割り切って全訳もページに載せたい場合は `publish_full_abstract: true`。
- API キーやパスワードは Secrets に入れているので、Public でも外からは見えません。

---

## 困ったとき

| 症状 | 確認すること |
|---|---|
| メールが来ない | Actions タブで赤い ✗ がないか。`GMAIL_APP_PASSWORD` が通常のパスワードになっていないか |
| `authentication_error` | `ANTHROPIC_API_KEY` の貼り間違い、クレジット残高 |
| ダッシュボードが空 | 手順 4(書き込み権限)と手順 5(Pages)の設定 |
| 自動実行が止まった | 長期間リポジトリに動きがないと GitHub が自動実行を止めることがあります。Actions タブで **Enable workflow** |
| 論文が多すぎる/少なすぎる | `keywords` を絞る/増やす、`any_journal_max` を調整 |

手元(Python 3.10 以上)での確認:

```bash
pip install -r requirements.txt
python -m digest.main --mock      # ネットも API も使わずサンプルで動作確認 → output/email.html
python -m digest.main --dry-run   # 本番データで実行、メールは送らない(要 ANTHROPIC_API_KEY)
```

---

※ 要約・翻訳は Claude による自動生成です。数値や結論は必ず原文で確認してください。
