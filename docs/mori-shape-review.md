# 森JPタワー頂部・低層部の形状候補 v1

対象: [Issue #3](https://github.com/OurJapan/open-tokyo-world/issues/3)。ユーザーが「上の部分と地面付近の形状が違う」と報告したことを起点とする。**これは未承認の形状仮説であり、精度を確定した復元モデルではない。**

## 根拠

- [Pelli Clarke & Partners](https://pcparch.com/work/azabudai-hills): 頂部は4枚の曲面ガラスの花びらという設計説明。掲載のtower-crown写真では、頂部だけでなく、その下の外装帯にも曲線が見える。village-green写真、main-entrance写真、敷地配置図も参照した。確認日2026-09-07、撮影日不明、主な写真クレジットJason O'Rear。画像の転載・素材利用は行っていない。
- [森ビル施設概要](https://www.mori.co.jp/en/projects/azabudaihills/facilities/): 低層部の用途と中央広場、屋根The Cloudの存在を確認。The Cloudとタワー入口の庇を混同しない。The Cloudそのものは今回の対象外。
- 旧 `work/interior_walk/glass_return.py`: 表示される外装は `Mori continuous pearl glass`。`Mori JP curtain wall` は非表示だった。上端のみ `323.4 + 7.7*sin(2*theta)^2`、その下は水平な外装帯。
- 旧 `work/landmark_rebuild/build.py`: podiumは128×132mの同じ丸角平面を高さ31.3mまで繰り返していた。これは低層部の高さや配置の違いを表さない。

## 今回の候補

頂部は実際に表示される外装4objectを変更する。高さ205m以下と頂部上端は保持し、その間の外装帯を4方向の曲面へ連続的に変形する。最大変位8m、開始高205m、移行高318.32mは写真からの視覚的推定で、実測値ではない。内部床、屋上設備は変更しないため、外装と内部階構成の整合は追加調査が必要。

低層部9objectは、一様な6段の仮設モデルをrenderから除外する。geometryは削除せず保持する。周辺のPLATEAU由来objectを変更しない。低層部を推定寸法の3つの箱へ置換した試行は、既存データと重なったため不採用にした。これにより過大な白い基壇は除けるが、実物の低層部形状を再現できたことにはならない。入口庇、道路接続、学校・店舗棟の個別地物ID、敷地境界と観測時点の照合は未完了。地面付近の指摘は未解決として残す。

近傍には PLATEAU_data217/219/221/223 があり、各tileは複数の建物を含む。bbox重なりだけでtile全体を削除すると周辺建物も失うため、自動削除しない。次はtile内の地物単位に分解して対象を照合する。

## 再現と検証

`mori_shape_v1` は任意Pythonを受け取らない、版を固定した限定adapter。対象feature ID、object名、変更前mesh hash、単独使用mesh、identity transform、animation／parent／constraint無しを確認する。異なるbaselineや再適用は停止する。地物IDには表示中の外装collectionを追加し、Before／Afterの双方へ同じmappingを設定する。

```sh
python scripts/review.py --blender BLENDER --input LEGACY_BLEND --lock manifests/legacy-baseline.json --cameras areas/tokyo-tower/mori-shape-cameras.json --features areas/tokyo-tower/features.json --patch patches/mori-shape-v1.json --output runs/mori-shape-v1 --device OPTIX --width 960 --height 540 --samples 16 --timeout 1200
```

原本は保存変更しない。全景、展望台、頂部詳細、低層部詳細をBefore／After同条件で比較する。外部写真からテクスチャは生成しない。今回も実都市画像はローカルレビューのみ。

受入は、数値検証に加え、人間が「形状が実物に近づいた」と確認すること。頂部の細部・低層部配置の追加資料が必要で、Issueは閉じない。

## 実行結果

[候補v1の検証記録](mori-shape-run.json)。原本hash不変、変更は指定した13objectのみ。外装4objectはmesh変更、基壇9objectはhide_renderのみでmeshを保持し、その他objectと画像依存は一致。4視点8枚を960×540、16 samplesで生成した。Pythonテスト9件成功。既存Blenderの正常変更・素材欠落検出の2ケースも再確認済み。

頂部と全景を目視確認したが、精度の受入は保留。足元は既存都市データによる遮蔽があり、正しい建物単位への分解と追加資料が必要である。
