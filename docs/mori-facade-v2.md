# 森JPタワー：外装の色の連続性と中央の縦帯

ユーザーから「胴体の中央に縦線がある」「頂部は胴体と同じ色」「昼間は発光していない」と指摘されたため、頂部のみの材質修正を外装全体の整合へ進める。

## 参照

- 設計事務所 Pelli Clarke & Partners: https://pcparch.com/work/azabudai-hills
- ユーザー指定の頂部写真: https://pcparch.com/media/pages/work/azabudai-hills/164af9059b-1737998450/azabudai-hills-tower-crown-2880x-q60.webp
- ユーザー追加の外苑東通り側写真: https://pcparch.com/media/pages/work/azabudai-hills/6bb1db96e1-1737998449/azabudai-hills-gaien-higashi-dori-2880x-q60.webp
- 確認日: 2026-09-07。撮影日・正確な撮影時刻は未確認。写真は参照のみで再配布しない。

写真ではガラス外装が頂部へ連続し、面の中央付近に細い縦帯がある。夕景写真の帯の明るさを昼光用の自己発光に置き換えない。縦帯の実際の構成や寸法を写真だけで確定したものではない。

## 変更範囲

`mori_facade_v2` は表示中の外装4objectに限って材質を複製する。前回のcrown v2形状と、crown material v1の帯用UVを用いる。

胴体・頂部のガラス部に同一のBase Color=(0.30,0.43,0.48)、Metallic=0.45、Roughness=0.16、Transmission Weight=0.12を適用する。反射する方向、背後の構造、横帯の有無で画素色には差が生じるが、別色の頂部材質にはしない。

縦帯はガラス、横帯、目地、細い枠の材質をまたいで連続させる。中立的な銀灰色、Metallic=0.7、Roughness=0.23、Emission Strength=0で外光の反射のみを表現する。追加の照明や夜景の点灯は実装しない。

帯の方向は既存の四隅の中間（63.984375°、153.984375°、242.578125°、332.578125°）に推定配置。幅約1.3m相当も推定値である。厚み・溝の実形状ではなく材質マスクによる近似。担当はAI実装、人間の外観レビュー待ち。

## 再現

```sh
python scripts/review.py --blender BLENDER --input LEGACY_BLEND --lock manifests/legacy-baseline.json --cameras areas/tokyo-tower/mori-shape-cameras.json --features areas/tokyo-tower/features.json --patch patches/mori-facade-v2.json --output runs/mori-facade-v2 --device OPTIX --width 960 --height 540 --samples 16 --timeout 1200
```

patchはcrown v2の形状適用後に各対象mesh・材質のhashを照合する。旧patchは過去候補の再現用として維持する。今回のpatchの参照ページには両写真が掲載され、追加写真と日中の非発光条件は本書に記録する。

## 検証と残課題

Pythonテスト16件。保存後の別process検査で、外装4objectの全頂点と接続関係が前回と一致、胴体・頂部のガラス数値が一致、全Principled shaderのEmission Strengthが0であることを確認した。

[実行記録](mori-facade-v2-run.json) / [保存後の形状・材質・非発光検査](mori-facade-v2-validation.json)。表示する比較画像の左は前回の頂部材質候補、右は今回。共通runnerの数値Beforeは固定原本である。

帯の正確な寸法・ディテール、実写と同じ照明での比較、地面付近の形状再現は残課題。自動検証は現実との完全一致を保証しない。
