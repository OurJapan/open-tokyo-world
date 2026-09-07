# 初めての参加：試すところから投稿準備まで

最初からコードを書く必要はありません。画像を見て「分かりにくい」「ここが違う」と伝えることも貢献です。自分のAIに生成を頼みたい人は、以下の手順で小さく試せます。

## 1. 参加方法を選ぶ

| やりたいこと | 最初の行動 | 必要なもの |
|---|---|---|
| 画像を見て気づきを伝える | [比較画像](README.md#検証済みの表示例)を見る | ブラウザ。GitHubで投稿する際はアカウント |
| 自分のAIと生成・変更を試す | 以下の手順でスターターを実行 | Python、Blender、ファイルとコマンドを扱えるAIまたは本人 |
| コード変更を提案する | 自分のfork・作業ブランチからPRを作る | GitHubアカウント、Gitの操作（AIに依頼可） |

GitHubを使わない一般向け受付サイトはまだありません。読む・ダウンロードする段階ではログイン不要ですが、IssueやPRの投稿にはログインが必要です。運営に直接伝える既存の連絡手段がある場合は、運営が本人の公開意向を確認して代理記録できます。専用の窓口や自動転送は未実装です。

## 2. ファイルと実行環境を用意する

[リポジトリ](https://github.com/OurJapan/open-tokyo-world)の **Code → Download ZIP** で全体を取得し、ZIPを展開します。Gitを使う人はcloneでも構いません。`README.md`、`scripts`、`starter`が並んでいるフォルダが「リポジトリのルート」です。ZIPの中や`starter/plaza`だけを切り出した状態では実行しません。

検証した環境はWindows、Python 3.12、Blender 4.5.1 LTSです。[Python公式](https://www.python.org/downloads/)から入手できます。Blenderは[公式サイト](https://www.blender.org/)で4.5 LTSの配布を確認してください。異なる版を使った場合は投稿に版を記載してください。追加のpipパッケージ、都市データ、GPU専用設定は不要です。

PowerShellを開き、展開先に移動して確認します。パスは自分のPCに合わせて置き換えます。

```powershell
Set-Location 'C:/自分の展開先/open-tokyo-world-main'
Test-Path 'starter/plaza/run.py'
python --version
& 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --version
```

`Test-Path`が`True`になれば場所は合っています。`python`が見つからない場合は、インストール済みなら`py --version`を試すか、Python実行ファイルの絶対パスを使います。PowerShellでは次のように先頭に`&`を付けます。Pythonが未導入の場合はまず導入してください。

```powershell
& 'C:/自分のPythonの場所/python.exe' --version
```

## 3. AIに小さな変更を頼む

次の文を、取得したフォルダを扱えるAIに渡せます。

> AGENTS.md、README.md、docs/review-harness.md、starter/plaza/README.mdとライセンスを読んでください。PythonとBlenderの実行ファイルを確認し、スターターの舗装の明るさを0.9にした比較を新しい出力先に生成してください。形状と既存ソースは変えず、run.jsonと両方のvalidation.jsonを確認して比較画像を見せてください。これは練習です。実物を修正したとは説明しないでください。結果を紹介したい場合に使える投稿下書きを作り、送信前に私に見せてください。

自分で実行する場合は、リポジトリのルートで次を使います。`python`を別の起動方法にした人は、同じように置き換えます。

```powershell
python starter/plaza/run.py --blender 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe' --output build/plaza-first --paving-brightness 0.9
```

この一回の実行で、基準の明るさ1.0と変更後0.9の両方を生成します。再実行する場合は`build/plaza-second`など新しい出力先にします。

## 4. 結果を確認する

出力先の`review.html`をブラウザで開き、画像が2枚表示されるか確認します。HTMLと`before`・`after`フォルダは一緒に置いてください。

AIには`run.json`の最上位の`ok`と、`before/validation.json`、`after/validation.json`の`ok`が全て`true`かを確認してもらいます。舗装の明るさだけが変わり、形状が変わっていないことを画像でも見ます。JSONが成功でも現実の正しさを証明したことにはなりません。

`after/scene.blend`はBlenderで開いて編集できます。ただし、その手作業の編集は既存の比較画像や検証結果には反映されません。このCLIは材質パラメータ用なので、一般的な形状変更の検証は別途設計します。

## 5. 投稿を準備する

練習が成功しただけなら投稿は任意です。つまずきや共有したい発見があれば、[成果物・外部の改善を紹介する](https://github.com/OurJapan/open-tokyo-world/issues/new?template=contribution.yml)を使います。Issueは相談・報告の投稿、PRはリポジトリに入れる具体的な変更の提案です。ZIPで取得した人も、最初からforkやPRを作る必要はありません。

フォームへの記入例です。自分の実行結果に合わせて書き換えてください。

| フォームの項目 | 記入例 |
|---|---|
| 何を紹介しますか？ | 自分または自分のAIが作ったモデル・素材（操作で困った場合は「その他・まだ分からない」） |
| どんな改善ですか？ | スターターの練習です。舗装の明るさを1.0から0.9にしました。現実との差分修正ではありません。画像は表示できましたが、○○の説明で迷いました。 |
| 成果物のURLや入手方法 | 下にBefore/After画像を添付。blendは未共有です。 |
| 作者・利用条件 | 元モデル：ark4ez / OurJapan、CC BY 4.0。変更：自分の表示名、AI使用、明るさ変更。出典とライセンスを添付。追加素材なし。 |
| 編集・再現に役立つ情報 | OS、Python/Blenderの版、取得commitまたはZIP取得日、実行コマンド、検証結果を記入。 |

投稿には `before/preview.png` と `after/preview.png` を**Before／Afterと区別して**添付し、`run.json`、両方の`validation.json`、`ASSET-LICENSE.md`、`provenance.json`をまとめた小さいZIPも添付できます。ZIPはその5ファイルだけを選び、validation.json同士は`before`・`after`のフォルダを保って区別してください。ライセンスと出典のリンクを本文に記載する方法でも構いません。

自分の追加素材・変更にはその作者・条件も追記します。実行フォルダ全体や`.blend`、ログはそのまま添付せず、共有が必要な場合に運営と相談します。失敗報告では、エラー名と発生した段階を記載し、個人情報やPC内パスを含む長いログを丸ごと貼る必要はありません。

コードを変更した人は、変更を保存した自分のforkの作業ブランチからOurJapanのmain宛てにPRを作成します。[PRテンプレート](../../.github/PULL_REQUEST_TEMPLATE.md)に再現手順・根拠・比較・許諾範囲を記載します。今回のパラメータ練習だけならソース差分はないので、空のPRを作る必要はありません。

送信すると公開される内容を本人が確認します。その後は「運営が確認 → 必要なら追加情報・再修正 → 人間がレビュー → 採用または理由を添えて保留」の順です。送信だけで利用許諾や採用が自動確定するわけではありません。[参加ルール](../../CONTRIBUTING.md)

## 困ったとき

| 表示・症状 | 確認すること |
|---|---|
| pythonが見つからない | 上記の`py`またはPythonの絶対パス。Blender用と通常Python用の実行ファイルを混同しない |
| run.pyが見つからない | ZIPを展開したか、ルートで実行しているか |
| Blender executable not found | `--blender`が実行ファイルを指しているか |
| FileExistsError | 出力先の名前を変える。既存の結果を削除する必要はない |
| CalledProcessError / okがfalse | 出力先の該当ログでエラーの要点を確認。成功した結果として提出しない |
| 画像が出ない | 処理が成功したか、HTMLと画像の相対配置を保っているか |

この手順は既存のWindows環境で公開版を新しいフォルダに取得して確認しました。新しいPCへのインストール、他OS、ITに不慣れな第三者による利用テストは未実施です。[検証記録](first-contribution-check.json)
