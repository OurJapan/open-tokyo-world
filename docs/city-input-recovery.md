# 街の入力データの復元と再実行

2026-09-27、過去の調査スクリプトに記録された別の制作フォルダーから、不足としていた25ファイルが見つかりました。地図・配置等の20ファイル（41,543,658 bytes）を共通のローカル保存先へ取り込みました。前段のBlenderファイル5本（計2,756,874,040 bytes）は、初回の回収時には所在・サイズ・SHA-256だけを固定しました。その後の[部品・材質の照合](city-component-verification.md)で5本も取り込み、うち3本を読み取っています。

道路から配置までの7段階を再実行し、12出力すべてが保存版とバイト単位で一致しました。街路樹・低木2,647メッシュは、基本形状に加えて位置・向き・大きさも採用済みの街と一致しました。[入力台帳](../manifests/legacy-production-inputs.json)と[検証記録](../sources/city-pr12-input-recovery.json)に範囲を固定しています。

## 同じ入力を取り込む

正当な提供元から受け取ったフォルダー内で、台帳にある `work/` と `outputs/` の相対パスを保ってください。リポジトリのルートで次を実行します。

```powershell
.\otw.ps1 import-production-inputs --input 'C:\Received\legacy-project'
```

`data/local/sources/legacy-production-inputs-v1/` に20ファイルをコピーします。全入力と既存のコピー先をサイズ・SHA-256で照合してから取り込み、変更済みのコピー先を上書きしません。元のフォルダーは読み取り専用の入力として扱います。約2.76GBの前段モデルも必要な場合だけ `--include-scenes` を追加します。取り込み時に旧コードやblend内のスクリプトは実行しません。

このコマンドは公開ダウンロードを提供するものではありません。元データの配布範囲・提供先は未確定です。取得したデータ、コピー元の絶対パスを含むローカル記録、再生成結果はGit対象外です。

## 道路・配置を再生成して照合する

先に[固定した制作コード](city-production-sources.md)を `fetch-production` で取得します。元リポジトリの閲覧権限が必要です。

データ処理の参照環境は **Python 3.12 / NumPy 2.3.5 / Shapely 2.1.2 / GEOS 3.13.1** です。通常の共通CLIと異なり、この再実行にはPython 3.12と追加パッケージが必要です。Windowsでは、Python 3.12とPython Launcherがある環境で次を実行します。

```powershell
py -3.12 -m venv data/local/runtime/production-venv
& '.\data\local\runtime\production-venv\Scripts\python.exe' -m pip install --only-binary=:all: -r requirements-production.txt
& '.\data\local\runtime\production-venv\Scripts\python.exe' -B scripts/replay_production_inputs.py --output data/local/replays/my-production-check
```

出力先は新しいフォルダーにします。20入力と確認済みの7スクリプトのhash、ライブラリ版を検査し、必要な8入力だけを複製してから実行します。照合対象の12出力は複製せず、各処理で実際に生成します。旧制作処理全体を一括実行するものではありません。再実行中のネットワーク取得やBlender起動はありません。

| 処理 | 照合する出力 |
|---|---|
| 広域道路 | `wide_roads.npz`、`road_checks.json` |
| 環境の道路面・低木 | `road_detail.npz`、`shrubs.json`、`surface_checks.json` |
| 土地利用 | `landuse.npz`、`landuse_areas.json` |
| 道路沿いの設備 | `placements.json` |
| 車両・街路樹の配置 | `layout.json`、`road_boundary.wkb.npy` |
| 旧樹木と道路の重なり判定 | `tree_keep.json` |
| 外壁の窓割り | `facade_layouts.json` |

`replay.json` に各段階の結果を保存します。JSONの値、配列の型・形・数値列と、ファイル全体のSHA-256を分けて比較します。内容の不一致は失敗とし、バイト単位の一致は別欄に記録します。今回のWindows / Python 3.12.14では、新規仮想環境への依存パッケージ導入後も12ファイルすべてのSHA-256が一致しました。同じPCでの確認であり、別PC・他OSでの実行は未検証です。

## 採用済みの街との配置照合

[共通環境](contributor-workspace.md)で街を登録済みなら、Blender 4.5.1 LTSで次を実行します。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/verify_city_tree_placements.py -- --output data/local/audits/tree-placements-new.json
```

街路樹657本の幹・葉1,314メッシュと低木1,333メッシュを、保存された配置、固定コードの変換式、照合済みの基本形状から確認します。Blenderのfloat32で位置・Euler回転・拡縮が全件一致し、親・制約・アニメーション等による追加の変換依存がないことも確認しました。元のblendへの保存は行いません。

## 入力の由来と、まだ確認していない範囲

保存OSM XMLは過去の広場調査のSHA-256と一致しました。ファイルに取得日時やスナップショット日時はありません。別系統のOverpass道路JSONには `timestamp_osm_base: 2026-09-05T18:00:49Z` があり、これはデータベースの基準時刻で、ダウンロード日時とは区別します。取得済み版を現在の地図で置き換えてはいません。

配置データには街路樹657本、低木1,333個、車両593台分があります。道路や建物範囲から推定した演出用配置であり、現地の実数・実測位置ではありません。建物範囲は2ファイルに計20,560レコードありますが、重複を除いた建物数とは扱いません。

このデータ再実行は、建物範囲・既存道路面・樹冠位置・外壁の入力記録を含む8ファイルを出発点とします。これらすべてを公式の原資料から作る工程、街全体の再構築は未検証です。29メッシュ・31材質と、樹冠・窓割りの中間記録は[別の照合手順](city-component-verification.md)で一致しました。表示状態、実物精度、各入力と独自部品の配布条件は技術的一致とは別に確認します。
