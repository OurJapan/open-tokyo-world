# 頂部の透けを抑える材質候補

ユーザーが四隅の位置を確認した後、「薄い／透明っぽい」と指摘したため、頂部の材質を分離する。形状はcrown v2を保持する。

## 根拠と推定

- source: 設計事務所 Pelli Clarke & Partners、Azabudai Hills。
- source URL: https://pcparch.com/work/azabudai-hills
- reference image: https://pcparch.com/media/pages/work/azabudai-hills/164af9059b-1737998450/azabudai-hills-tower-crown-960x-q80.jpg
- 写真クレジット: Jason O'Rear（公式ページ記載）。撮影日・公開日は未確認。last verified: 2026-09-07。
- 公式説明はpearl-gray glass、4枚の曲面ガラスの花びら。写真では頂部まで反射性の外装と横帯が続き、現モデルのような屋上設備の強い透けは見られない。
- 写真は夕景で、本レビューは既存の昼光環境。写真から光学定数や隠れた裏打ち構造は確定できない。今回のシェーダー数値はAIによる外観調整の推定であり、実測ではない。生成区分: AI実装、人間レビュー待ち。

旧材質を実シーンから読み出すとTransmission Weight=0.9、Metallic=0.12、Roughness=0.055、Alpha=1だった。Alphaによる透明化ではなく、屈折透過の寄与が強い。頂部の露出面1,280面（256パネル×5面）だけに複製材質を割り当て、Transmission Weight=0.12、Metallic=0.45、Roughness=0.16とする。ガラス部のBase Colorは(0.30,0.43,0.48)、帯・縦枠は(0.075,0.115,0.14)とし、IORは保持する。専用UVで高さ方向を3分割した曲線の帯とパネル境界を表現する。位置・幅は写真に基づく推定で、構造部材の実寸再現ではない。値は物理的透過率の百分率ではない。

既存の底面と下部壁面は元の材質を保持する。新しいテクスチャ、裏壁、屋上設備の削除は追加しない。公式写真は参照のみで同梱しない。

## 再現と検証

`patches/mori-crown-material-v1.json`は固定原本にcrown v2と従来の仮基壇非表示を適用後、対象のmeshと材質の両SHA-256を照合し、限定材質adapterを実行する。

```sh
python scripts/review.py --blender BLENDER --input LEGACY_BLEND --lock manifests/legacy-baseline.json --cameras areas/tokyo-tower/mori-shape-cameras.json --features areas/tokyo-tower/features.json --patch patches/mori-crown-material-v1.json --output runs/mori-crown-material --device OPTIX --width 960 --height 540 --samples 16 --timeout 1200
```

検証記録は [run](mori-crown-material-run.json) と [保存後の形状比較](mori-crown-material-geometry.json)。ローカル比較の左は位置確認済みのcrown v2、右は今回。共通runnerの数値Beforeは固定原本である。

写真にある頂部の帯間隔・細部の精密な再現、および足元の実物形状は残課題。外観の一致を自動検証だけで確定しない。

Pythonテスト14件、Blender統合テスト2ケース（正常系・画像欠落の検出）が成功。保存済み形状の比較で全頂点・接続関係・下部材質が一致。前回候補とのobject比較では対象ガラス1objectのみ変化した。

最終実データ実行は保存14.860秒、再open検証34.203／40.297秒、4視点render28.735／26.578秒。原本SHA-256は不変。比較は単発測定であり性能保証ではない。
