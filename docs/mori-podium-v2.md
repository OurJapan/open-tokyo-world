# 森JPタワー低層部の形状復元

暗いガラスと頂部形状をユーザーが確認した後、足元の修正へ進む。低層部を一様な箱として再推定するのではなく、旧制作工程が除去した元データの部分形状を復元する。

## 原因と出典

旧 `work/landmark_rebuild/build.py` は `PLATEAU_data221` の `_BATCHID=5` を全て除去してタワーを作り直した。このbatchには低層部も含まれていた。代わりの128×132m・6段の仮基壇は過大だったため、先行候補では非表示にしていた。

旧 `work/landmark_rebuild/export_source.py` は制作前の `Tokyo_Tower_Morning_15s.blend` 内の同objectを `source_mori.npz` に抽出している。本復元はこのローカルarchiveを使用する。元sceneのmetadataはPLATEAU港区2025由来と記録するが、本作業で配信元データを再取得して同一性・観測時点まで独立検証したわけではない。

- source archive: `source_mori.npz`、79,561 bytes。
- SHA-256: `786c370507eeb819fe004be256d02a995cb08a2cc301bf742e057b1e89b5ed3d`。
- 地物: archive内のbatch 5（森JPタワー）。隣接batchやtileは除去しない。
- 形状: batch 5のうち全頂点がローカルz≤40mの667三角形。実際の選択部分の上端は約38.99m。切断面を補間して作る処理ではなく、既存の三角形を選択する。
- 確認日: 2026-09-07。生成区分: 都市データからAIが部分復元。材質はAIによる推定。

配置・段差・入口まわりの比較に[PCPA公式ページ](https://pcparch.com/work/azabudai-hills)、同ページの[敷地図](https://pcparch.com/media/pages/work/azabudai-hills/b6d9153697-1737998458/cross-section-plan-en-remake-03-1440x-q80.jpg)・[入口写真](https://pcparch.com/media/pages/work/azabudai-hills/a7d08d332d-1737998439/azabudai-hills-main-entrance-crop-960x-q80.jpg)、[日本設計のプロジェクト紹介](https://www.nihonsekkei.co.jp/projects/19811/)を参照。画像は転載・テクスチャ化しない。

## 実装

`mori_podium_v2`は非表示の旧 `Mori JP podium / stone` のmeshを選択した元形状へ置換し、表示を戻す。元の名称とfeature IDを維持する。他8つの仮基壇objectは非表示を継続し、全周辺objectと確認済みタワー外装は保持する。

復元部にはガラス、テラス、舗装の簡単な材質を割り当てる。横帯の間隔等は仮の外観表現であり、旧写真テクスチャを再配布しない。入口庇の格子、植栽、手すり、低層部の細かい窓割りまで再現したものではない。

## 再現

```sh
python scripts/review.py --blender BLENDER --input LEGACY_BLEND --lock manifests/legacy-baseline.json --cameras areas/tokyo-tower/mori-podium-cameras.json --features areas/tokyo-tower/features.json --patch patches/mori-podium-v2.json --geometry-source SOURCE_MORI_NPZ --output runs/mori-podium-v2 --device OPTIX --width 960 --height 540 --samples 16 --timeout 1200
```

`--geometry-source`は復元opがある場合だけ必須。runnerとworkerの両方がサイズ・hashを確認し、NPZのpickle読み込みは無効。出力後にも入力hashを再照合する。archive本体とblendは配布権確認前のため本repositoryに含めない。

## レビューと検証

従来4視点に低層部の南西側・北西側を追加する。ローカル比較の左は直前に確認された暗いガラスの候補、右は今回の復元。追加2視点も同じ旧候補から新規renderする。共通runnerの数値Beforeは固定原本である。

[実行記録](mori-podium-v2-run.json) / [元三角形との照合・対象外不変の検査](mori-podium-v2-validation.json)。写真に対する形状の人間レビューは未完了。復元範囲は低層部の大きな輪郭・段差であり、足元全体の高精細な再現完了とはしない。

Python契約テスト18件、Blender統合テスト2ケース（正常系・素材欠落の検出）が成功。保存した667三角形は固定archiveの選択結果とfloat32座標で完全一致し、全て非ゼロ面積。直前の確認済み候補との差分は旧podium stoneの1objectのみで、画像依存も一致した。6視点12枚を生成し、原本とgeometry sourceのhashは不変。
