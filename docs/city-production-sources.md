# 街の制作コードと不足入力

2026-09-27、元プロジェクトの固定コミット `defac576e076f40bf3bc4fddcdcefe30f9a009f7` に、植栽・車両・設備の生成コードが見つかりました。21本のPythonと `.gitignore`、計22ファイル・96,714 bytesを[取得台帳](../manifests/legacy-production-sources.json)に固定しました。街路樹と低木は基本形状を再生成し、現行の2,647メッシュすべてで形状hashが一致しました。配置・材質と、残る29メッシュの再生成照合は未完了です。

元URL `DoiTakayoshi/tokyo-tower-blender` は、現在 [ark4ez/tokyo-tower-blender](https://github.com/ark4ez/tokyo-tower-blender) に転送されます。GitHub APIで確認した公開範囲は **private** です。通常の匿名ダウンロードは404となりました。外部協力者が全員取得できる入口ではありません。

## 同じ制作コードを取得する

元リポジトリの閲覧権限を持ち、GitHub CLI `gh` で認証済みの場合、リポジトリのルートで実行します。

```powershell
.\otw.ps1 fetch-production
```

`data/local/sources/legacy-production-defac576/` に元の相対パスを保って取得し、サイズ・SHA-256・Git blob hashを照合します。取得するのは調査用のコードです。旧コードの実行や街の生成は行いません。既存ファイルが変更されていれば上書きせず停止します。コマンドは認証設定・リポジトリの公開設定を変更しません。

権限に従って取得済みの同じファイルを使う場合は、元の相対パスを保ったフォルダーを指定できます。

```powershell
.\otw.ps1 fetch-production --inputs 'C:\Received\production-sources'
```

通常のPython 3.11/3.12では `python scripts/workspace.py fetch-production` も使用できます。取得コードと `source-record.json` はGit対象外です。このリポジトリにはURL・hash・対応表と新しい取得／監査用コードのみを追加し、旧コードの利用許諾を一括変更しません。

## 部品との対応

以下の `work/` は、取得フォルダー内の相対パスです。[機械可読の照合記録](../sources/city-pr12-production-audit.json)に、固定したソースの行番号・入力・現行部品の集計を残しました。

| 現行の分類 | 見つかった制作処理 | 配置・前段への依存 |
|---|---|---|
| 公園等の樹冠 4メッシュ | `tokyo60/build_city.py` が `leaf0..3` を作成。`tower15_env/refine_canopies.py` が樹冠を作り直す | `work/osm.xml`、前段blendの樹木形状・位置。制作メモに3,313本の記載 |
| 低木・下草 1,333メッシュ | `tower15_env/build_environment.py` が4種類のicosphereを配置 | `tower15_env/surfaces.py` がOSMの公園領域から道路・PLATEAU建物範囲を避け、`shrubs.json` を生成 |
| 街路樹・植樹帯 1,316メッシュ | `tokyo_traffic/build.py` がイチョウ・ケヤキの幹と葉を生成 | `layout.py` によるOSM道路と建物範囲からの配置。現在は657組の幹・葉と、樹皮・土の集約部品2個 |
| 車両等 14メッシュ | 同じ `build.py` が箱・車輪等から車種を作り、材質別に統合 | `layout.py` が一方通行・左側通行等から車種・位置・向きを生成。14は台数ではない |
| 街灯 1メッシュ | `detail_upgrade/finish_detail.py` が灯具を生成 | OSM道路に35m間隔を基本として配置。シーン内に308灯の記録。実測灯具位置ではない |
| 近景設備 8メッシュ | `street_detail/build.py` が蓋・排水口・車止め・点字ブロック等と窓枠を生成 | `prepare.py` の道路配置、前段PLATEAU形状・画像から推定した窓割り |

確認した該当生成処理では、外部の樹木・車両・設備モデルを読み込む処理は見つかりませんでした。一方、前段blendの形状・材質、地図・建物データへの依存があります。特に近景の窓割りは既存建物の写真も参照するため、「材質に画像がない」ことだけで入力から独立した制作物とは判定しません。

原版を別プロセスで読み、6分類2,676メッシュのcustom propertiesが空、library参照がゼロ、Text datablock 3件が制作メモであることを確認しました。部品ごとの制作コードhashやOSM way IDは見つかりませんでした。原本のSHA-256は不変です。制作元についての[ご本人の記憶](../sources/city-pr12-authorship-notes.json)は補足する記録として保持します。

### 街路樹・低木の形状照合

固定した3ファイルのうち、確認済みの形状生成部分だけを別のBlenderプロセスで実行しました。街路樹の12種類の幹・葉、低木の4種類の基本形状を生成し、元の1,314＋1,333メッシュと照合しています。頂点のローカル座標、面の構成、面の材質番号、UVを含むhashが全件一致しました。低木の基本形状はそれぞれ42頂点・80面です。

位置・回転・拡縮、材質ノード、実在との精度、配布許諾を確認したものではありません。街路樹分類の残り2メッシュ（樹皮・土の集約部品）、旧樹冠4メッシュ、車両14メッシュ、街灯1メッシュ、設備8メッシュは生成処理との静的対応に留まります。

固定コードを取得済みなら、照合を再実行できます。ソース全体のhashが変わっていれば実行前に停止します。旧コードのファイル入出力・外部プロセス・保存処理や、blend内のTextは実行対象に含めません。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/verify_tree_prototypes.py -- --output data/local/audits/tree-prototypes-new.json
```

## まだ不足している入力

元の `.gitignore` は `work/` のPython等を選んで保存し、XML・配置JSON・NPZ等を対象外にしています。固定コミットにも、確認した旧フォルダーの対応パスにも、以下の入力はありませんでした。

| 復元するもの | 役割・生成元 |
|---|---|
| `work/osm.xml` | 初期の道路・植栽・土地利用。過去の広場調査には保存OSMのhashがあるが、今回そのファイル本体との対応を検証できていない |
| `work/wide_detail/selected_tiles.json`、`roads.json` | 別の道路取得経路。範囲を指定してOverpassから取得する。固定日時・応答hashが不足 |
| `work/twin_towers/tower_surfaces.json`、`work/wide_detail/wide_roads.npz` | 旧 `outputs/Tokyo60/` の道路面と上記道路入力から統合した道路。`wide_detail/roads.py` に生成処理あり |
| `work/{detail_upgrade,wide_detail}/imported_features.json` | PLATEAU建物の範囲。植栽・車両・灯具の配置判定に使用 |
| `work/tower15_env/shrubs.json`、`work/tokyo_traffic/layout.json`、`work/street_detail/placements.json` 等 | 元入力から生成する配置・中間データ。生成コードはあるが、過去の出力と再生成結果の照合が必要 |
| 前段blend・依存ライブラリの版 | 生成処理が読む途中段階の街、Shapely等の環境。現行の街を前段の代用品として実行しない |

`work/osm.xml` と `wide_detail/roads.json` は別入力です。現在のOSMを取得して過去版と同一とは扱いません。配置用の乱数seedはコードにありますが、道路・建物の入力やライブラリの版が異なれば同じ配置になるとは限りません。

次の復元対象は、上記2系統の保存OSMとPLATEAU建物の中間台帳です。入手できれば固定hashを付け、道路→配置→部品の順で別の作業フォルダーに再生成して現行版と照合します。元データを復元できない場合は、新しい入力から生成する版を別候補として管理します。[森JP周辺の公開入力からの生成](contributor-workspace.md)は引き続き利用できます。

## シーン内の制作情報を再確認する

固定した街全体を登録済みの場合、Blender 4.5.1 LTSで次を実行します。出力先は新しいフォルダーを指定してください。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/audit_city_production.py -- data/local/audits/city-production-new
```

埋め込みText・propertiesを読み取るだけで、Textの実行やblendへの保存はしません。全文・ローカルパスを含み得る詳細出力はローカル調査用です。共有用の集計は内容を選んで別に記録します。
