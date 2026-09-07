# ガラスの明るさの追加調整

ユーザーの「ガラスはもうちょっと暗い」に対応する。直前の[外装統一候補](mori-facade-v2.md)に対し、胴体と頂部に共通するガラスのBase Colorだけを(0.30,0.43,0.48)から(0.16,0.25,0.30)へ下げる。値はBlender入力の線形RGBで、写真から測定した反射率ではない。

縦帯の銀灰色・発光量ゼロ、四隅の形、ガラスのMetallic=0.45・Roughness=0.16・Transmission Weight=0.12、カメラと照明は保持する。頂部と胴体のガラス部の設定は今回も同一である。

参照はユーザー指定の[PCPA頂部写真](https://pcparch.com/media/pages/work/azabudai-hills/164af9059b-1737998450/azabudai-hills-tower-crown-2880x-q60.webp)と[外苑東通り側写真](https://pcparch.com/media/pages/work/azabudai-hills/6bb1db96e1-1737998449/azabudai-hills-gaien-higashi-dori-2880x-q60.webp)。確認日2026-09-07、撮影日時は未確認。実写と既存シーンの光環境は一致していないため、画素値の一致は主張しない。

## 再現と版

`patches/mori-facade-v2.json`と`mori_facade_v2` adapterを使用する。今回のプリセットはadapter内のGLASS_COLORで固定し、実行コードhashを[実行記録](mori-facade-dark-run.json)に記録する。前回の明るいプリセットはcommit `d32ba0b189066dd06a7e1dcd65ba928fdea99740`で再現できる。

```sh
python scripts/review.py --blender BLENDER --input LEGACY_BLEND --lock manifests/legacy-baseline.json --cameras areas/tokyo-tower/mori-shape-cameras.json --features areas/tokyo-tower/features.json --patch patches/mori-facade-v2.json --output runs/mori-facade-dark --device OPTIX --width 960 --height 540 --samples 16 --timeout 1200
```

[保存後の形状・共通色・非発光検査](mori-facade-dark-validation.json)。比較画面の左は直前の外装統一候補、右は暗いプリセット。同一の4視点で比較する。共通runnerの数値Beforeは固定原本である。

色・縦帯の幅と細部はAIによる外観の推定。人間レビューと足元の形状修正は引き続き未完了。

実データの別process検査・4視点8枚のrenderが成功。原本hashは不変。直前候補との差分は対象ガラス1objectだけで、他のobject・画像依存は一致。Pythonテスト16件成功。
