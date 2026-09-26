# 外部協力者の制作環境

このページを、コード・データ・モデル・比較結果の共通入口にします。資産の版と取得可否は `manifests/contributor-workspace.json` で管理します。

地区・共通素材を選んで取得し、同じ構成を協力者と共有する場合は[地区ごとの取得手順](district-distribution.md)を使います。`otw.ps1 district` から構成の固定、取得、森JPの生成、検証、編集コピーを実行できます。以下の既存profileコマンドも引き続き利用できます。

**街全体の配布は未整備です。** リポジトリを取得しただけでは、採用済みの東京タワー周辺の街全体は開けません。次の2つを明示的に選びます。

| 対象 | 入手・実行方法 | 含むもの |
|---|---|---|
| `city`（既定） | 採用版を持つ方が `import-city` で登録 | PR #12採用の街全体。固定SHA-256で照合 |
| `mori` | `setup --profile mori` で公式入力を取得して生成 | 森JPタワー＋周囲23棟＋広場6部品。東京タワー・道路・地形は含まない |

`city` がない場合に `mori` へ自動的に切り替えません。街全体の一般公開を含む完了条件は [配布準備状況](asset-distribution-readiness.md) に残します。

## 1. コードとBlenderを用意する

GitHubからリポジトリをclone、または全体のZIPを展開します。参加者同士で同じ版を使うときは同じcommitまたはタグを指定し、比較結果に記録してください。`main` の更新前後で同じコードであるとは扱いません。

参照版は **Blender 4.5.1 LTS** です。[Blender公式の4.5配布一覧](https://download.blender.org/release/Blender4.5/)から4.5.1を選んでください。別バージョンのインストールをこのコマンドが変更することはありません。

通常の共通CLIには、WindowsでBlenderに付属するPythonを使う `otw.ps1` を用意しています。これにはPythonを別にインストールする必要はありません。旧制作の道路・配置を再実行する追加手順のみ、別途Python 3.12を使います。Blenderの既定のインストール先かPATHを確認します。別の場所へ展開した場合は、現在のPowerShellで指定します。

```powershell
$env:OTW_BLENDER = 'C:\Tools\Blender-4.5.1\blender.exe'
```

既定のインストール先であれば上の設定は不要です。リポジトリのルートから実行します。

```powershell
.\otw.ps1 doctor
.\otw.ps1 status
```

`doctor` はBlenderの完全な版番号、付属NumPy・Draco、自動スクリプト実行が無効であることを確認します。`status` はモデルの有無と記録済みファイルのハッシュを確認します。環境検査の成功は街全体を入手できたという意味ではありません。

PowerShellスクリプトを実行できない環境や、Pythonを自分で指定する場合は、Python 3.11/3.12から同じCLIを呼べます。追加のpipパッケージは不要です。

```powershell
python scripts/workspace.py doctor --blender 'C:\Tools\Blender-4.5.1\blender.exe'
```

共通CLIは他OSの実行ファイルパスも受け付けますが、現在の実機確認はWindowsです。新しいOS、別PC、初参加者による完了確認は別途必要です。

## 2. 対象を準備する

公開入力から森JP周辺を生成する場合：

```powershell
.\otw.ps1 setup --profile mori
```

公式PLATEAUの固定2ファイル（計1,658,929 bytes）を取得し、サイズとSHA-256を照合します。旧作業フォルダは探索しません。生成・保存後の別processでの再open・形状検査・4視点の比較描画を行います。失敗した生成を利用可能なモデルとして登録しません。初回はインターネット接続が必要です。既存の正しい入力は再利用し、壊れた入力は自動上書きしません。

明示的に取得済みの2ファイルを使う場合のみ `--inputs PATH` を付けます。`fetch` で入力取得だけを先に実行することもできます。

街全体の採用済みファイルを正当な提供元から受け取った場合：

```powershell
.\otw.ps1 import-city --input 'C:\Received\candidate.blend'
.\otw.ps1 setup --profile city
```

採用版は558,751,758 bytes、SHA-256 `98a3932e6dc972d4ae702d264c1e894d77765a9a3a5e57c8a75591eafd42e926` です。コピー前後の照合とBlender読み込みを行い、元ファイルは変更しません。これは新しい配布許諾を与える操作ではありません。

## 3. コピーを開いて改善する

```powershell
.\otw.ps1 verify --profile mori
.\otw.ps1 edit --profile mori --open
```

街全体なら `--profile city` に置き換えます。`edit` は毎回新しい編集用コピーを作ります。`--open` を省略するとコピーの保存先だけを表示します。基準モデルの検証記録は、その後の手編集の検証にはなりません。対象・根拠・変更範囲を決め、既存の [レビュー手順](review-harness.md) に従ってください。

登録した街全体から、現行の固定6視点で基準画像を生成する場合：

```powershell
.\otw.ps1 review
```

この処理は形状を変更しないbaseline-captureです。基準のhashに一致するlockと、既存5空メッシュを限定したfeature設定をローカルに作り、既存のレビューCLIを使用します。Gitが利用できるcloneで実行してください。CPUが既定で、時間がかかる場合があります。OptiX対応GPUを明示的に使う場合のみ `--device OPTIX` を指定します。次の実変更には対象を限定したpatchとその検証が必要です。

## ファイルの置き場所

```text
open-tokyo-world/
  scripts/・starter/・manifests/・docs/  コード・台帳・手順（Git）
  data/local/                           制作用データ（Git対象外）
    sources/                            固定した公式入力・出典
      legacy-production-defac576/        閲覧権限が必要な旧制作コード
      legacy-production-inputs-v1/       回収した地図・配置等の固定入力
    assets/tokyo-city-pr12/              採用済みの街全体
    builds/                             再生成した森JP周辺と比較画像
    edits/                              編集用コピー
    reviews/・review-configs/            街全体の比較結果と実行設定
    catalogs/                           画像付き部品一覧と出典照合結果
    replays/・runtime/                    道路・配置の再実行結果と専用Python環境
    checks/                             環境・読み込み確認
    workspace.json                      このPCで使えるモデルの台帳
```

出力先を独立させる検証では各コマンドに `--workspace PATH` を指定できます。ローカル台帳の絶対パスをGitに登録する必要はありません。配布可能なコード・出典・選別した証拠をPRへ提出し、ローカルフォルダ全体はアップロードしません。

## 出典の整理と材質の比較

[街の制作コードと入力の対応](city-production-sources.md)に、植栽・車両・設備と後段の描画設定に関係する固定コード24ファイルを整理しました。`.\otw.ps1 fetch-production` でコードを取得・hash検証できます。元リポジトリは非公開で閲覧権限が必要です。

[回収した入力の取り込み・再実行](city-input-recovery.md)を追加しました。`.\otw.ps1 import-production-inputs --input 'C:\Received\legacy-project'` で地図・配置20ファイルを登録できます。道路・配置の12出力と、街路樹・低木2,647メッシュの形状・変換を照合済みです。入力の公開配布先、街全体を最初から生成する工程は未整備です。

`--include-scenes` を付けると前段モデル5本も登録できます。そのうち3本を使い、[残る29メッシュ・31材質の照合](city-component-verification.md)を完了しました。基本形状16部品と31材質には[CC BY 4.0を適用し、配布用ZIPを公開](../assets/procedural-components/README.md)しました。cloneにはモデルを同梱せず、`.\otw.ps1 district setup --common procedural-components` で公開版を取得できます。

[画像付き部品一覧](city-catalog.md)で、既存の街の3,255メッシュを13分類から確認できます。非表示の部品も含めて部品名・出典記録を調べ、制作元メモを書き出せます。元のblendには保存しません。

[画像の出典照合](city-image-audit.md)、[外壁画像を使わない比較候補](city-facades-v1.md)、[形状・道路等の配布準備](city-distribution-plan.md)を用意しています。材質の比較候補は別のblendへ保存し、登録済みの街を変更しません。候補を外部へ配布できる状態かは、共通環境の読み込み検査とは別に確認します。

## 確認できること・残ること

同じ入力のバイト列、Blender版、実行コードのハッシュ、生成後の検査を記録できます。生成されたblendには保存パス等が入るため、別環境のblend全体やレンダー画像のバイト単位一致は保証しません。対応OSとデータ・形状・検証条件を揃えることが、この入口の目的です。

`verify` はハッシュとBlenderでの読み込み・画像/library参照を確認します。全トポロジー・全外部依存・現実の精度の検査ではありません。森JPの生成時は既存runnerの形状検査も行います。全都市のゼロからの再構築、全体モデルの一般向け配布、別PCでの利用確認は未完了です。

2026-09-26に、Gitで共有するソースだけを新しいフォルダーへコピーし、公式入力の新規取得→森JP生成→再読み込み→編集コピー作成を確認しました。同じPCでの確認です。手元の採用版の街については登録・原本hash不変・6視点の比較と変更objectゼロを確認しました。森JP生成の出力は約36MB、街全体の比較実行は1回につきBefore/After等で約1.13GBを使用しました。編集コピーには別途、森JP約19MB／街全体約559MBが必要です。これらは今回の出力実測で、インストール容量・一時領域・メモリ要件を含みません。[機械可読の検証記録](contributor-workspace-verification.json)
