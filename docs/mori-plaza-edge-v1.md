# 接続通路の両脇に残る道路面の修正

Issue #11。PR #10をマージした `278f2f1de2bf1cdbb0450463900aca2b899924d3` を起点とする。通路両脇の旧道路・縁石状の面を切り分け、下にある既存の芝生・汎用地面を露出させる。追加objectはなく、採用済みの建物、入口、テラス、地上6object、PLATEAU、既存芝生は変更しない。

## 根拠と範囲

[公式平面図](https://www.azabudai-hills.com/floor_map/mori-jp_tower-plaza_1f.html)と[設計者資料](https://www.nihonsekkei.co.jp/projects/19811/)を参照した前回の位置合わせを継承する。今回の原因調査は保存OSMと旧生成コードに基づく。保存way `1443867470` は `area=yes / highway=pedestrian / 中央広場`。旧 `work/tokyo60/build_city.py` の道路分岐はareaを区別せず、輪郭に幅9mの道路と全幅11.1mのpavementを生成する。

近隣wayを再抽出し、地下wayを除いた道路・歩道と対象面の距離を照合する。保存した元データのSHA-256は `f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab`。現在のOSMを取得した結果ではない。近隣の八幡通り・三年坂・別のfootwayは保持対象であり、道路object全体を削除しない。切り分けたfragment中心の距離を保存後検査に記録する。これは位置と生成経路による帰属確認で、元way IDが各mesh faceに残っているという意味ではない。

修正範囲は入口ローカル座標の2polygon、合計364m²。その中にある既存路面だけを除く。修正境界は推定で、実在の芝生輪郭の測量値ではない。

- 左：`(-16,22),(-7,22),(-5,32),(-5,38),(-16,38)`
- 右：`(7,22),(18,22),(18,38),(5,38),(5,32)`

前回の通路台形と面積的に重ならず、端で接する。原点 `(-419.80,290.82)`、u軸 `(2,-1)/sqrt(5)`、v軸 `(1,2)/sqrt(5)` は入口から継承。featureは `otw:jp:tokyo:minato:azabudai-mori-jp`。

## 残る課題

道路を除いた下には芝生だけでなく灰色の汎用地面（ground）もある。その形は今回変更していない。したがって、この候補を広場の完成形や正確な芝生境界とは扱わない。範囲外の道路表現、PLATEAU低層面との整合、現実の段差・階段・園路は今後の対象。新しい芝生や設備で不明点を覆い隠す変更は含まない。

## 検証と再実行

`manifests/mori-plaza-link-accepted.json` に前回の承認blendを固定。Blender 4.5.1を使用する。全ての出力先は新規にする。公開済みの元データgeometryではないため `SAVED_OSM` と `ACCEPTED_BLEND` は別途必要。

```sh
python -m unittest discover -s tests
python scripts/inspect_plaza_edge_source.py --osm SAVED_OSM --output LOCAL_SOURCE_RESEARCH.json
python scripts/review.py --blender BLENDER --input ACCEPTED_BLEND --lock manifests/mori-plaza-link-accepted.json --features areas/tokyo-tower/mori-plaza-edge-features.json --cameras areas/tokyo-tower/mori-plaza-edge-cameras.json --patch patches/mori-plaza-edge-v1.json --output NEW_RUN --device OPTIX --width 960 --height 540 --samples 24 --timeout 1200
BLENDER --factory-startup --background --disable-autoexec --python-exit-code 1 --python scripts/validate_mori_plaza_edge.py -- --before NEW_RUN/before.blend --after NEW_RUN/after.blend --source-research LOCAL_SOURCE_RESEARCH.json --output NEW_AUDIT.json
```

`LOCAL_SOURCE_RESEARCH.json`には保存OSMのgeometryを含むので公開しない。公開するのは出典hash、タグと距離集計。画像・blendも既存資産の配布権確認前のためPRに含めない。

review runnerは既存変更対象と素材の指紋を検査する。別processの保存後検査で元頂点、対象外の面・面積、道路除去範囲、元資料との距離、地表rayを確認する。元の道路は薄い面であり閉じた立体を保証しない。新規objectは0個。前回と同じ6視点・同じ設定で比較し、記録は `mori-plaza-edge-v1-run.json` と `mori-plaza-edge-v1-validation.json` に保存する。

