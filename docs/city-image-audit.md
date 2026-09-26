# 採用済み街の画像出典照合（2026-09-26）

PR #12採用版の383埋め込み画像のうち、382件を公式PLATEAUの配信ファイルに対応付けました。214件は符号化された画像bytesが一致し、168件は公式画像をBlender 4.5.1で縮小した後の8ビットRGBAが全画素一致しました。出典が未解決の画像は `facade_atlas.png` の1件です。

**これは画像の同一性の検査です。街全体の配布承認ではありません。** 個別データの条件、加工・出典表示、形状やOSM由来道路、全依存関係、配布先の確認は残っています。

## 固定した入力と結果

採用版blendのSHA-256：`98a3932e6dc972d4ae702d264c1e894d77765a9a3a5e57c8a75591eafd42e926`。保存や材質変更を行わず、検査の前後で入力hashが一致しました。

| 検査対象 | 結果 |
|---|---|
| Image datablock | 384件。埋め込み画像383件＋使用先のない `Render Result` 1件 |
| 旧画像台帳との差 | 画像名とpacked hashは全件同じ |
| 公式データ取得 | 港区LOD3 196件、千代田区LOD2 53件、中央区LOD2 1件、計250ファイル |
| 取得容量 | 424,425,812 bytes。新しく取得し、その後は固定したhashでオフライン再照合 |
| 符号化bytesの一致 | WebP 214画像 |
| 縮小後の画素の一致 | PNG 168画像。Blenderの `Image.scale` とRGBA8への丸めを適用し、差分は全チャンネル0 |
| 出典未解決 | `facade_atlas.png`。`wall0`〜`wall7` の8オブジェクトで使用 |

[画像ごとの照合結果](../sources/city-pr12-image-audit.json) / [取得元の固定版一覧](../sources/city-pr12-image-source-lock.json) / [旧画像台帳](../sources/image-inventory.json)

RGBA8の一致は、浮動小数点画素やPNG/WebPファイル全体の一致ではありません。縮小処理を再現できることを確認したもので、過去に実際に使った処理を特定したという意味でもありません。近似一致や誤差の許容値による合格は設けていません。

各画像について、記録された参照先の少なくとも1つとの一致を確認しています。同じ画像を複数objectで使っている場合に、すべてのobjectの出典URLや形状が正しいことまで証明するものではありません。

## 再確認する

PR #12の固定版を保持していることを前提にします。[共通city基準版の更新](city-baseline-pr40.md)後も、この照合は `manifests/mori-plaza-edge-accepted.json` のPR #12 hashに固定します。現行cityや別の版のinventoryは受け入れません。現在のモデルの画像調査には、その版に対応した別の入力・出典lock・検証記録が必要です。以下の出力先は毎回新しい名前にしてください。Blenderは4.5.1 LTSを使います。

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
$python = 'C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe'

& $blender --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/audit_image_sources.py -- data/local/audits/image-inventory-new.json

& $python scripts/verify_city_images.py --inventory data/local/audits/image-inventory-new.json --cache data/local/sources/image-audit --source-lock sources/city-pr12-image-source-lock.json --output data/local/audits/image-bytes-new --download

& $blender --factory-startup --disable-autoexec --background data/local/assets/tokyo-city-pr12/city.blend --python-exit-code 1 --python scripts/check_city_image_pixels.py -- --report data/local/audits/image-bytes-new/report.json --cache data/local/sources/image-audit --output data/local/audits/image-pixels-new
```

取得済みの正しいcacheで再確認するときは `--download` を外せます。出典URLを命令として扱わず、コードで列挙した3つの公式dataset内の `data/data数字.b3dm` だけを許可します。HTTP・query・別host・redirectは受け入れません。取得は1ファイル64MiB、1回の合計1GiBに制限しています。壊れたcacheや版の異なる配信は上書きせず失敗させます。

`verify_city_images.py` は終了コード0でも未解決画像が残ることがあります。全取得元の検査を実行できたという意味で、配布許可や全画像の一致を意味しません。`report.json` の分類を確認してください。画像bytesをJSONへ出力しません。画素検査のため一時的に取り出した公式画像は、その検査用の新規フォルダー内で処理後に削除します。

## 残る画像と配布条件

続く作業で、未確認の1枚を参照しない[数式材質の比較候補](city-facades-v1.md)を作成しました。候補では画像の除去を保存後に確認しました。ここに記録した採用版・画像監査結果は変更していません。

`facade_atlas.png` のpacked SHA-256は `6f7991ed6d5a1c19d55d7d3dd95821f5cfa11040e2ff065a1531aacb7ea2424c` です。既存の文書にはAI生成の外壁アトラスとの記載がありますが、利用可能な旧作業フォルダー内に `work/sky_detail/atlas_finish.py` や対応する生成記録は見つかりませんでした。生成者、参照入力、生成物の採用条件を示す記録を復元するか、公開候補の8オブジェクトだけを出典の明確な材質へ差し替える必要があります。

[PLATEAUサイトポリシー](https://www.mlit.go.jp/plateau/site-policy/)は2026-09-26に再確認しました。対象コンテンツには条件と例外があり、出典・加工の表示が必要です。[港区の個別resourceページ](https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025/resource/08755b94-7b2e-4c9c-bf35-6c4d0768a463)は今回の取得ではHTTP 403でした。以前の確認記録は保持しますが、全datasetの個別条件を再確認できたとは扱いません。

この変更で公開するのは検査コード、URL・hash・判定のmetadataです。取得した約424MBのデータ、旧blend、画像bytesはローカルに保持します。全体の進捗は[資産の配布準備状況](asset-distribution-readiness.md)を参照してください。

形式の参照：[Khronos glTF 2.0](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#glb-file-format-specification)、[Cesium 3D Tiles b3dm](https://github.com/CesiumGS/3d-tiles/tree/main/specification/TileFormats/Batched3DModel)。このreaderは今回の埋め込み画像構成に限定し、一般的な3D Tiles全形式の検証器ではありません。
