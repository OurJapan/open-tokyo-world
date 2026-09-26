# 中央広場を道路化した残存面の修正

PR #12採用版の中央広場には、芝生の前に浮いて見える道路面と縁石が残っていました。保存OSMの広場輪郭から生成された面を制作中間データに照合し、他の道路・歩道と重ならない寄与だけを除去します。7視点の同条件比較と保存後検査は完了しています。2026-09-27に人間が「マージして続ける」と採用を承認し、[PR #39](https://github.com/OurJapan/open-tokyo-world/pull/39)をmainへ取り込みました。採用commitは `66df406e9f6235698d3ab28d180b710a0238f343` です。実行時のJSONにある人間レビュー待ちの表示は履歴です。共通cityには、後続PR #40の芝生・園路とまとめて[反映しました](city-baseline-pr40.md)。

この確認済み出力から、[芝生・園路の修正](mori-plaza-landscape-v1.md)を別の増分として制作し、PR #40で採用しました。以下の検証結果と残課題は、道路面を除去した時点の記録です。

## 原因と帰属の証拠

保存OSMのway `1443867470`、version 4、更新日時 `2026-08-16T23:30:05Z` は `area=yes / highway=pedestrian / name=中央広場` です。[OSMの広場の記法](https://wiki.openstreetmap.org/wiki/Tag:highway%3Dpedestrian#Squares_and_plazas)は面を表しますが、旧 `work/tokyo60/build_city.py` はareaを区別せず、閉輪郭の111区間に幅9mのasphaltと全幅11.1mのpavementのboxを配置していました。

固定した旧commit `defac576e076f40bf3bc4fddcdcefe30f9a009f7` の生成式を再現すると、`work/twin_towers/tower_surfaces.json` に記録されたasphalt 111面・pavement 111面のfloat32 XYと上面Z（0.30m／0.23m）が一致します。距離だけに基づく帰属ではありません。一致した222レコードのSHA-256は `7550d4d3cf6e86d5c807bcb64723f32e81a5ce68bd06318664fba6cc14a9fff1`。同じ座標を持つ追加のレコードがある場合も、対象分を超えて消費せず保護します。

制作経路は `build_city.py → tower.blend → export_surfaces.py → tower_surfaces.json → wide_detail/roads.py → finish.py → tower15_env/surfaces.py → build_environment.py` です。この地区は旧core（XY各±1,100m）の内側にあり、`roads.py` が新たな `roads.json` の道路bufferをcore外へ切り取る経路とは区別します。今回は既存seedに含まれていた誤生成面が引き継がれています。historicalな `clean_surfaces.py` は未回収のため、その内容や実行を根拠にはしていません。

## 固定入力と変更範囲

| 入力 | SHA-256 |
|---|---|
| PR #12採用city（558,751,758 bytes） | `98a3932e6dc972d4ae702d264c1e894d77765a9a3a5e57c8a75591eafd42e926` |
| `work/osm.xml`（10,528,704 bytes） | `f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab` |
| `work/twin_towers/tower_surfaces.json`（4,429,925 bytes） | `184875e48426ba84b0dddb169f2dc2a414798ac42ee3b7c0047b572991013531` |

入力blendは [lock](../manifests/mori-plaza-edge-accepted.json) に固定します。[patch](../patches/mori-plaza-outline-v1.json) の変更対象は `asphalt 15s road detail`、`gutter 15s road detail`、`pavement_0 unified road` の3objectだけです。追加objectは0、道路のpaintと建物・入口・植栽・既存芝生・汎用地面は不変です。

一致したpavement上面の和集合を対象にし、周囲の非対象seed 67面（asphalt／pavement／paint）との重なりを保護します。桜麻通り、周囲のservice road・footway由来の面もこの保護に含まれます。旧処理の2mm丸めとfloat32を考慮して除去側に3mm、保護側に5mmの余裕を取り、保護を優先します。この数値は計算誤差への余裕で、測量精度ではありません。

道路の元頂点座標はすべて保持し、変更しない面は頂点index・材質番号・smooth設定まで保持します。水平面だけでなく対象内の縁石側面も切り分けます。原本を上書きせず、別のBefore／After blendへ保存します。

## 保存後の検証結果

Blender 4.5.1 LTSで再読み込みし、runnerの変更範囲・素材検査に加え、別validatorでShapelyによる独立した面の差分を検査しました。除去領域の作成に使う出典照合は共通ですが、面を切り分ける実装とは別の平面演算で確認しています。

| 道路部品 | 除去対象の上面積 m² | 保存面と期待値の対称差 m² | 対象外の完全一致面数 |
|---|---:|---:|---:|
| asphalt | 2,683.3416 | 0.002382 | 140,205 |
| gutter | 203.2769 | 0.000641 | 33,134 |
| pavement | 395.2798 | 0.000220 | 270,956 |

これらは道路上面の実測値です。除去領域自体は約3,761.80m²で、以前の修正済み部分など道路のない部分も含むため、上面積の合計とは一致しません。pavementの側面も含めた除去表面積は約590.2520m²です。

保存後の入口12点・周囲の道路60点でobjectと高さを維持しました。除去周辺8点には既存の地面が残っています。中心線のv=63.4mで芝生z=0.11m、v=63.5mで旧縁石z=0.46mだった35cmの上りは、修正後は後者が汎用地面z=0mになります。**既存芝生から地面への11cmの下りは残り、平坦な歩行面が完成したという意味ではありません。** 入口の通路末端は引き続きv=32m付近で、ここから先の園路は未制作です。

7視点×Before／After、1280×720、Cycles OptiX、32 samples、seed 0、frame 1で比較しました。入口・通路の見た目を保持し、広場に残る道路帯の除去を確認しています。道路と重なる部分の凹凸、尖った芝生輪郭、周囲の古い建物表現は残ります。カメラ候補の人間による受入は未完了です。

[実行記録](mori-plaza-outline-v1-run.json) / [検証集計](mori-plaza-outline-v1-validation.json)。公開記録にはgeometryやローカルの絶対パスを含めません。旧都市の画像・blend・OSM・中間geometryはローカルに保持します。

## 再実行

`ACCEPTED_BLEND` は上記lockと一致する街全体の原本、`ROAD_INPUTS` は[取り込み済み制作入力](city-input-recovery.md)のルートです。`ROAD_INPUTS/work/osm.xml` と `ROAD_INPUTS/work/twin_towers/tower_surfaces.json` が必要です。旧都市を含まない公開Moriスターターとは異なる入力であり、第三者がこの修正まで公開ファイルだけで再現できる状態ではありません。

出力先 `NEW_RUN` と `NEW_AUDIT` はそれぞれ未作成のディレクトリを指定します。PowerShellで引用した実行ファイルを起動するときは先頭に `&` を付けます。

```sh
python -m unittest discover -s tests
python scripts/review.py --help
python scripts/review.py --blender BLENDER --input ACCEPTED_BLEND --lock manifests/mori-plaza-edge-accepted.json --features areas/tokyo-tower/mori-plaza-outline-features.json --cameras areas/tokyo-tower/mori-plaza-outline-cameras.json --patch patches/mori-plaza-outline-v1.json --road-inputs ROAD_INPUTS --output NEW_RUN --device OPTIX --width 1280 --height 720 --samples 32 --timeout 1200
PRODUCTION_PYTHON scripts/validate_mori_plaza_outline.py --blender BLENDER --before NEW_RUN/before.blend --after NEW_RUN/after.blend --road-inputs ROAD_INPUTS --output NEW_AUDIT
```

runnerはPython 3.11/3.12の標準ライブラリ、`PRODUCTION_PYTHON` はPython 3.12・NumPy 2.3.5・Shapely 2.1.2・GEOS 3.13.1の固定環境を使います。導入は [requirements-production.txt](../requirements-production.txt) と [制作入力の再実行手順](city-input-recovery.md) を参照してください。OptiXがない場合は明示的に `--device CPU` を選択します。

## 残る制作課題

[公式平面図](https://www.azabudai-hills.com/floor_map/mori-jp_tower-plaza_1f.html)と[設計者資料](https://www.nihonsekkei.co.jp/projects/19811/)を参照し、芝生の輪郭、入口から先の園路、階段・段差、周囲の低層建物との位置関係を別の修正として詰めます。今回の取り除き処理から実在の舗装形状を推定したり、測量・ナビゲーション・バリアフリー適合を認定したりはしません。元の道路は薄い面であり、閉じた立体の保証もありません。
