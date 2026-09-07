# 頂部の四隅を合わせる修正 v2

ユーザーの追加指摘「四隅の角に高い頂点が来る」を受け、頂部輪郭の位相を修正する。前案の横帯の波打ちは今回の候補から取り除く。

## 原因と根拠

[設計者の説明と写真](https://pcparch.com/work/azabudai-hills)の4枚の曲面ガラスの花びらを参照。旧モデルは `sin(2*theta)^2` を使い、45°、135°、225°、315°を頂点としていた。しかし既存の外形はその方向へ整列していなかった。

旧 `work/landmark_rebuild/profiles.json` の第3断面を、表示中の外装生成 `work/interior_walk/glass_return.py` と同じ3回の平滑化・256分割で処理し、半径の局所最大を四隅の代表点とした。角度はローカルXYの+Xから反時計回り。結果は18.28125°、109.6875°、198.28125°、286.875°で、旧頂点から約25〜28°ずれていた。丸角の代表点であり、測量による角点の確定ではない。

## 変更

`mori_crown_v2` は高さ318.32mより上の頂部だけを変更する。各四隅の代表点で高く、隣り合う四隅の角度の中間で低くなる滑らかな曲線を用いる。谷323.4m・峰331.1mは旧モデルの値を保持した推定値であり、実物の高さを新たに確定したものではない。

境界318.32mを固定し、各方向の旧上端から新上端へ正の倍率で写像する。XY、頂部より下の頂点、内部床、屋上設備、材質は変更しない。前案v1の横帯変形を重ねず、固定原本から作り直す。仮基壇の非表示は前案を継続するが、地面付近の実物再現は引き続き未解決。

## 再現

```sh
python scripts/review.py --blender BLENDER --input LEGACY_BLEND --lock manifests/legacy-baseline.json --cameras areas/tokyo-tower/mori-shape-cameras.json --features areas/tokyo-tower/features.json --patch patches/mori-crown-v2.json --output runs/mori-crown-v2 --device OPTIX --width 960 --height 540 --samples 16 --timeout 1200
```

v1 adapterとpatchは過去の候補を再現するため保持する。最新候補は上記v2。入力mesh hashの照合、別process再open、対象外変更・素材依存検査は共通基盤を使う。

Pythonテストは12件。四つの最大点・中間の最小点、旧上端から新上端への写像、境界以下の不変、上下順序の保持を検証する。見た目の受入はユーザーによる確認を待つ。

## 実データ結果

[実行記録](mori-crown-v2-run.json)。Blender 4.5.1、OptiX、960×540・16 samplesで4視点8枚を生成し、保存・別process再open・検証が成功した。原本hashは不変、変更は指定範囲内の12objectのみ（頂部を含む外装3objectのmeshと仮基壇9objectの表示）。他のobjectと画像依存は一致。前案の同じカメラの画像もローカル比較画面に並べ、数値検証のBeforeが固定原本であることを明記している。

保存済みBefore／Afterのガラスmeshを再読み込みした[頂点座標の検査](mori-crown-v2-vertices.json)でも、XYと318.32m以下の全頂点は完全一致。四つの最高点は18.28126°、109.68748°、198.28125°、286.87506°となり、四隅の代表方向と一致した。
