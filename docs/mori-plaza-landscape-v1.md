# 中央広場の芝生輪郭と園路の修正候補

[道路輪郭の修正（PR #39）](mori-plaza-outline-v1.md)後に残る芝生の切り欠きを復元し、地図に記録された広場の舗装と、入口から左側の園路へ曲がる接続を追加します。変更対象は既存の芝生1objectと新しい舗装1objectです。**今回の景観案は人間の画像レビュー待ちです。PR #39の道路修正は人間が採用を承認していますが、mainへのマージは保留中です。** 共通cityプロファイルは変更していません。

## 原因と資料

旧 `work/tower15_env/landuse.py` はOSMの芝生・庭などの面から `wide_roads.npz` の道路・歩道を差し引き、z=0.11mで三角形化していました。中央広場の閉輪郭を道路として生成した誤りが、芝生・庭にも大きな切り欠きを作っています。元の建物形状の差し引きはこの処理に含まれません。

固定OSMの芝生2区画・庭5区画を使い、PR #39で除去した道路の寄与と重なる部分だけを復元します。周囲の正当な道路67面、採用済み入口、既存芝生を保護します。庭は既存と同じ草地材質の平面として戻すため、樹木や植え込みの再現ではありません。

| 用途 | 保存OSMのway | 版・更新時刻 |
|---|---|---|
| 中央広場の舗装範囲 | `1443867470` | v4、2026-08-16T23:30:05Z |
| 芝生 | `1443867471`, `1443867472` | v1、2025-10-22T06:30:02Z |
| 庭 | `1443867473`, `1443867474`, `1443867475`, `1443867476`, `1443867479` | v1、2025-10-22T06:30:02Z |

[公式平面図](https://www.azabudai-hills.com/floor_map/mori-jp_tower-plaza_1f.html)と[設計者資料](https://www.nihonsekkei.co.jp/projects/19811/)も参照しています。ただし、この修正は保存地図の平面輪郭の復元です。写真から高さを測定したものではなく、現地の階段・傾斜・建物の位置合わせは未解決です。

## 推定した接続と高さ

採用済み入口通路の末端（入口ローカルv=32m）から左側の地図上の園路へ、幅7mから3.6mへ絞る約121.45m²の曲線通路を追加します。中心線はローカル制御点 `(0,32), (0,45), (-15,41), (-20,46)` の三次曲線を24区間に分割したものです。これは現存する園路の実測形状ではありません。

最初の試作では接続先が旧PLATEAU建物に重なり、保存後の検査で失敗しました。接続先を広場側へ移し、中心24点と幅方向96点を地表・上空の両方から検査します。この120測点は通路全域や街全体の衝突保証ではありません。

芝生と新しい舗装の上面は、旧芝生と入口通路の末端に合わせたz=0.11mです。舗装は底面z=-0.01mの閉じた薄い立体です。周囲の高い道路との全接続、旧建物と地図の不一致、実際の階段・起伏はこの案に含めません。

## 固定入力

| 入力 | SHA-256 |
|---|---|
| PR #39の画像確認済み出力（558,818,952 bytes） | `1141a1408727d04860d5f722681e92fa63c363efe8da67b9c5e12f4b12d8f9a8` |
| `work/osm.xml` | `f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab` |
| `work/twin_towers/tower_surfaces.json` | `184875e48426ba84b0dddb169f2dc2a414798ac42ee3b7c0047b572991013531` |
| `work/tower15_env/landuse.npz` | `8aed717b555ac8593146afd9d8a7fd4ba3a93c51c60ab05e982ab866878434a8` |
| 生成するローカルplan JSON | `b1b6776b7cf60c9e5e4a342bac5a27624b0c743dd950358af8607fb3b5c589a8` |

[入力lock](../manifests/mori-plaza-outline-reviewed.json)と[patch](../patches/mori-plaza-landscape-v1.json)で版を固定します。plan生成にはPython 3.12、NumPy 2.3.5、Shapely 2.1.2、GEOS 3.13.1が必要です。OSMを毎回取得せず、[回収済み制作入力](city-input-recovery.md)を使います。plan内のPython版は3.12系列で固定し、パッチ版だけの違いでhashが変わらないようにしています。

既存芝生の元頂点はすべて保持し、推定通路と交差しない面はindex・材質番号・smooth設定まで保持します。新しい舗装には既存の手続き型 `pavement` 材質を使い、画像素材を追加しません。原本は上書きしません。

## 保存後の検証

同じ7視点、1280×720、Cycles OptiX、32 samples、seed 0、frame 1でBefore／Afterを比較しました。runnerが変更対象・材質・画像の不変性を確認し、別processで保存モデルを開くvalidatorが面の差分、舗装の閉形状、入口と通路の地表の検査に成功しています。

| 検査項目 | 結果 |
|---|---:|
| 復元した芝生・庭の平面積 | 1,070.0642 m² |
| 推定接続のため切り取る既存芝生 | 約82.6907 m² |
| 新しい舗装の平面積（接続を含む） | 1,188.4320 m² |
| 保存芝生と期待値の対称差 | 0.0003404 m² |
| 保存舗装とplanの対称差 | 0 m² |
| 保存芝生・舗装の重なり | 0.00000544 m² |
| 新規面と保護道路の重なり | 0 m² |
| 変更範囲外で完全一致した芝生面 | 6,427面 |
| 舗装の閉形状・面の向き | 全edgeが2面に共有され、向きが対向 |
| 新規の面積ゼロ面 | 0面 |
| 既存入口のobject・高さを維持 | 9測点 |
| 通路の中心・幅と上方の遮蔽 | 24＋96測点で検査成功 |

以前の中心線v=63.4m／63.5mの芝生と汎用地面の境界は、両方がz=0.11mになり、この測点間の11cmの下りを解消しました。採用済み入口のタイル細部には約3mmの凹凸が残り、全周囲の段差を解消したという意味ではありません。

portableテスト195件（190成功・5省略）、Blender統合テスト2ケース、compileallが成功しました。比較画像7組はAIが確認済みで、人間の景観判断は未完了です。

既存芝生には固定した制作入力と一致する面積ゼロの面が34枚あります。元頂点・面index・材質・smoothと枚数が完全一致する場合だけ、面積の和集合から除外します。新規の不正な面は許可しません。これは既存の5つの空メッシュに対するrunnerの例外とは別の検査です。

検証値は[実行記録](mori-plaza-landscape-v1-run.json)と[検証集計](mori-plaza-landscape-v1-validation.json)に記録します。公開記録はコードとmetadataのみです。旧都市blend・画像・OSM・中間geometry・planはローカルに保持します。

## 再実行

`OUTLINE_BLEND` は上記lockと一致するPR #39出力、`PRODUCTION_INPUTS` は回収済み制作入力のルートです。旧都市を含まない公開Moriスターターとは別の入力です。第三者が公開ファイルだけでこの景観案を再生成できる状態ではありません。

`NEW_PLAN` は未作成のローカルJSONファイル、`NEW_RUN` と `NEW_AUDIT` はそれぞれ未作成のディレクトリです。PowerShellで引用した実行ファイルを起動する際は先頭に `&` を付けます。

```sh
python -m unittest discover -s tests
python scripts/review.py --help
PRODUCTION_PYTHON scripts/prepare_mori_plaza_landscape.py --inputs PRODUCTION_INPUTS --output NEW_PLAN
python scripts/review.py --blender BLENDER --input OUTLINE_BLEND --lock manifests/mori-plaza-outline-reviewed.json --features areas/tokyo-tower/mori-plaza-landscape-features.json --cameras areas/tokyo-tower/mori-plaza-outline-cameras.json --patch patches/mori-plaza-landscape-v1.json --landscape-plan NEW_PLAN --output NEW_RUN --device OPTIX --width 1280 --height 720 --samples 32 --timeout 1200
PRODUCTION_PYTHON scripts/validate_mori_plaza_landscape.py --blender BLENDER --before NEW_RUN/before.blend --after NEW_RUN/after.blend --inputs PRODUCTION_INPUTS --plan NEW_PLAN --output NEW_AUDIT
```

runnerは標準ライブラリだけで動きます。`PRODUCTION_PYTHON` の導入は [requirements-production.txt](../requirements-production.txt) と[制作入力の再実行手順](city-input-recovery.md)を参照してください。Blenderは4.5.1 LTSを指定し、OptiXがない環境では明示的に `--device CPU` を選びます。
