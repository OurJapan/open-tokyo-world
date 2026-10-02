# 東京タワー上部の塗装帯 — ローカル制作候補

この文書は独立モデルの制作時点の記録です。最新mainへの統合と公開レビューは[都市統合記録](tokyo-tower-city-repairs-v1.md)を参照してください。

既存の上部鉄骨は部材の中点で塗装色を選んでいたため、斜材全体が境界の反対側の帯へ同じ色ではみ出していました。固定ID `tokyo-tower-part-005`・`006` の表面を6本の水平境界で分割し、既存のオレンジ／白を面ごとに割り当てました。新しい実測寸法、設備や意匠の追加はありません。共通city・通常Blender登録・PR #49は変更していません。push・PR・mergeは未実施です。

## 根拠と範囲

- [東京タワー公式「タワペディア」塗装編](https://www.tokyotower.co.jp/plan/towerpedia/)を2026-10-02に確認。上部はオレンジと白の7等分であるとの説明があります。写真の取得・再配布・テクスチャ利用はしていません。
- [保持された旧生成コード](../assets/tokyo-tower/legacy-source/tower-base.fragment.py.txt)の `color(z)` は154〜333mを7等分し、上部鉄骨では部材中点の色を一括適用しています。その既存設計を表面の塗り分けに反映しました。
- **154mの下端と正確な境界標高は既存モデルの推定値**です。公式資料だけでこれらの数値を実測値と認定していません。塗料の正確な色・実物の断面・アンテナ設備の正確さも今回の認定範囲外です。
- [固定入力・範囲・根拠](../assets/tokyo-tower/paint-bands-v1.json)。main `234b163210ac19d61f33e86b6920b8b26f9d453a` 起点。PR #44の77部品IDをそのまま使用し、過去のID付与変更を再適用していません。
- 既存の許諾記録・作者表示を保持。原作モデルは ark4ez / OurJapan、CC BY 4.0。許諾範囲や共通ライセンス文書は変更していません。

## 実装

[限定スクリプト](../scripts/tokyo_tower_paint_bands.py)は固定した独立blendだけを受け付けます。原本上書き・既存出力への生成・候補モデルへの二重適用を拒否します。部品005・006を表示名ではなく固定IDで選び、元の材質をもう一つのスロットへ参照します。既存の材質ノード自体は変更せず、他75部品の材質への影響を防ぎます。IDと `source_object` は履歴上の部品識別を引き継ぎます。

境界をまたぐ面だけを、Blenderの元の表示用三角形に沿って分割します。これは細いアンテナの旧ベベル四角面に約0.2mmの非平面性があったためです。共有辺の交点を再利用して開放辺を作らず、元頂点の座標・番号を保持します。対象2部品には元からUV層・カスタム法線がありません。変更対象以外はUV・属性・コーナー法線も含めたハッシュで保護します。

## 確認結果

Windows、Blender 4.5.1 LTS、付属Python 3.11.11で検証。元入力 SHA-256は `8413d9cce5f0cfa6d27428d4315b5516768a46c018065f5787607ed6ec138da9`、候補は `361f45888ca17db9cee112bf76a55d21f2e9820f4d385f575101ffc152400f5f`。

| 部品 | 頂点 Before → After | 面 Before → After | 分割した元面 |
|---|---:|---:|---:|
| 005 / orange | 519,880 → 521,944 | 500,038 → 503,134 | 1,032 |
| 006 / white | 116,352 → 119,856 | 111,644 → 116,900 | 1,752 |

- 別のBlenderプロセスで保存候補を開いて検査。77固定ID、対象外75 mesh、カメラ・照明、全材質定義、World、元636,232頂点を保持。
- 各分割面を元の表示用三角形へ対応付け、面の被覆、向き、平面、境界内包含、面積、塗装割当を検査。最大平面偏差は `6.014e-6 m`、元三角形ごとの最大面積差は `3.049e-6 m²`。float32の丸めを含む数値検査です。
- 対象2 meshとも、開放辺・孤立辺・3面以上に接する辺はBefore/Afterとも0。新たな完全トポロジー認証や自己交差・構造安全性の検証ではありません。
- 全景、230.714m付近、205.143m付近、下部の4視点をCycles CPU・4 threads・16 samples・seed 0、同じカメラ／照明／色管理で描画し、8枚を目視確認。近景で斜材・柱の帯が揃い、全景の輪郭を保っています。
- 下部画像の50画素に最大4/255の微小差があります。下部オブジェクトのデータは不変ですが、画素の完全一致とは扱いません。差の個別原因は未特定です。
- portable tests：237件、230成功、7任意依存スキップ。別途、小さな閉じたねじれメッシュのBlender試験で、表面保持と頂点移動／誤色／面反転／誤対応の拒否を検査。

[検証記録](tokyo-tower-paint-bands-v1-verification.json)。出力はGit対象外の `data/local/tower-paint-bands-03/` に保存しています。`review.html`、`after.blend`、Before/After PNG、形状対応表、各検証JSONを含みます。ログは `data/local/tower-body-probe/` にあります。01・02は検査中の候補で、03がレビュー対象です。

## 再実行

PR #44で保持したID付き独立入力が必要です。公開リポジトリだけでモデルを再取得できるという意味ではありません。旧exporterの出力を別環境で作り直した場合、blendのバイトハッシュが一致する保証はなく、その入力への対応は別レビューが必要です。

```powershell
$blenderPath = 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe'
$towerInput = 'RECEIVED_FIXED_ID_TOWER.blend'
$towerOutput = 'data/local/tower-paint-bands-new'
foreach ($phase in @('build','validate','render-before','render-after','compare')) {
  & $blenderPath --background --factory-startup --threads 4 --disable-autoexec --python-exit-code 1 --python scripts/tokyo_tower_paint_bands.py -- --phase $phase --input $towerInput --output $towerOutput
  if ($LASTEXITCODE -ne 0) { throw "Tower phase failed: $phase" }
}
python -m unittest discover -s tests
& $blenderPath --background --factory-startup --threads 2 --disable-autoexec --python-exit-code 1 --python tests/blender_tower_paint_bands_smoke.py
```

次は親レビューで帯の見え方と推定境界の扱いを確認し、採用する場合に現行cityの同じ2部品との一致・配置を検査して置換パッチを準備します。現行cityへの統合、全都市での材質／周辺取り合い、GPU描画、公開配布は未検証です。既存独立モデルの補助植栽や不明な実物ディテールはそのまま保持しています。
