# 街の制作コードと入力の対応

2026-09-27、元プロジェクトの固定コミット `defac576e076f40bf3bc4fddcdcefe30f9a009f7` に、植栽・車両・設備の生成コードが見つかりました。当初の22ファイル・96,714 bytesに後段の描画設定2本を加え、現在は23本のPythonと `.gitignore`、計24ファイル・102,969 bytesを[取得台帳](../manifests/legacy-production-sources.json)に固定しています。街路樹と低木は基本形状を再生成し、現行の2,647メッシュすべてで形状hashが一致しました。

その後、別の制作フォルダーから不足していた25入力を回収し、道路・配置の12出力を同じバイト列で再生成できました。2,647メッシュの位置・回転・拡縮も一致しています。[入力の取り込み・再実行手順](city-input-recovery.md)と、追加の[29メッシュ・材質の照合](city-component-verification.md)を参照してください。

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

この形状照合とは別に、回収した入力から位置・回転・拡縮を確認しました（[追加の記録](../sources/city-pr12-input-recovery.json)）。街路樹分類の残り2メッシュ（樹皮・土の集約部品）、旧樹冠4メッシュ、交通等14メッシュ、街灯1メッシュ、設備8メッシュも、[専用の比較](city-component-verification.md)で一致しました。31材質と2,676メッシュの材質割当も一致しています。9メッシュのBevel描画設定は、後段の `camera_options/render.py` に記録された無効化ルールを再現して比較しています。実在との精度や配布許諾は別の確認です。

固定コードを取得済みなら、照合を再実行できます。ソース全体のhashが変わっていれば実行前に停止します。旧コードのファイル入出力・外部プロセス・保存処理や、blend内のTextは実行対象に含めません。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/verify_tree_prototypes.py -- --output data/local/audits/tree-prototypes-new.json
```

## 初回調査で不足していた入力

元の `.gitignore` は `work/` のPython等を選んで保存し、XML・配置JSON・NPZ等を対象外にしています。固定コミットにも、初回に確認した旧フォルダーの対応パスにも、以下の入力はありませんでした。この初回調査の結果は監査記録に残し、別フォルダーからの回収を[追加記録](../sources/city-pr12-input-recovery.json)で補足しています。

| 回収したもの | 役割・今回の確認 |
|---|---|
| `work/osm.xml` | 初期の道路・植栽・土地利用。回収したファイルが過去の広場調査のhashと一致。取得日時は未確認 |
| `work/wide_detail/selected_tiles.json`、`roads.json` | 別の道路取得経路。選択範囲・応答hashとOSM基準時刻を固定 |
| `work/twin_towers/tower_surfaces.json`、`work/wide_detail/wide_roads.npz` | 旧 `outputs/Tokyo60/` の道路面と上記道路入力から統合した道路。`wide_detail/roads.py` に生成処理あり |
| `work/{detail_upgrade,wide_detail}/imported_features.json` | PLATEAU建物の範囲。植栽・車両・灯具の配置判定に使用 |
| `work/tower15_env/shrubs.json`、`work/tokyo_traffic/layout.json`、`work/street_detail/placements.json` 等 | 配置・中間データ。7段階・12出力の再生成で保存版とバイト単位一致 |
| 前段blend・依存ライブラリの版 | 前段blend5本をhash付きで取り込み、部品照合で3本を使用。道路・配置のデータ処理はPython 3.12、NumPy 2.3.5、Shapely 2.1.2、GEOS 3.13.1で一致 |

`work/osm.xml` と `wide_detail/roads.json` は別入力です。現在のOSMを取得して過去版と同一とは扱いません。配置用の乱数seedはコードにありますが、道路・建物の入力やライブラリの版が異なれば同じ配置になるとは限りません。

次に確認するのは、回収した建物範囲・道路面等の中間台帳と原資料の対応です。基本形状16部品・31材質への許諾は[別に確定](../assets/procedural-components/README.md)しました。簡易建物等を含む街全体の再構築と公開配布は未完了です。[森JP周辺の公開入力からの生成](contributor-workspace.md)は引き続き利用できます。

## シーン内の制作情報を再確認する

固定した街全体を登録済みの場合、Blender 4.5.1 LTSで次を実行します。出力先は新しいフォルダーを指定してください。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/audit_city_production.py -- data/local/audits/city-production-new
```

埋め込みText・propertiesを読み取るだけで、Textの実行やblendへの保存はしません。全文・ローカルパスを含み得る詳細出力はローカル調査用です。共有用の集計は内容を選んで別に記録します。
