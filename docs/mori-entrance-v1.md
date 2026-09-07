# 森JPタワー：広場側の入口庇・丸柱

確認済みの低層部に、三角格子のガラス庇、銀色の丸柱7本、入口の縦フレーム・扉枠、庇の付け根の軒天と小さな舗装帯を追加する候補。上部タワーの暗いガラス・四隅・縦帯、復元した低層部の667三角形は保持する。

## 根拠と推定

- [PCPAの公式入口写真](https://pcparch.com/media/pages/work/azabudai-hills/a7d08d332d-1737998439/azabudai-hills-main-entrance-crop-960x-q80.jpg)：三角格子、ガラス庇、銀色の丸柱、軒天と縦長の入口ガラスを視覚確認。撮影日時・実寸は未確認。写真は再配布せずリンクのみ。
- [麻布台ヒルズ公式1Fフロアマップ](https://www.azabudai-hills.com/floor_map/mori-jp_tower-plaza_1f.html)と[PCPA敷地図](https://pcparch.com/media/pages/work/azabudai-hills/b6d9153697-1737998458/cross-section-plan-en-remake-03-1440x-q80.jpg)：オフィス入口と中央広場の関係を参照。異なる向きの図面をそのままBlenderのXYへ適用しない。
- 元archiveの広場側壁面は、およそ `(-435.57,298.70)` から `(-404.03,282.94)` の線分。今回の配置はこの壁面に沿わせた**写真ベースの仮説**であり、写真の入口を測量座標へ独立照合した結果ではない。

照合日：2026-09-07。生成：AI Agent。写真の形の観察と、現シーンへの寸法・位置合わせを区別する。庇の長さ32m、奥行7m、高さ約10.8m、柱径1.44m、柱間隔5m、格子割り・扉割り・材料定数は推定。入口の自動ドア機構や内部空間は再現しない。夜の写真に見える照明は昼景へ持ち込まず、追加材質のEmission Strengthはすべて0。

## 変更範囲

`mori_entrance_v1`は以下の既存objectだけのmesh・専用材質を置換して表示する。旧モデルで非表示だった仮基壇の部品名を、限定変更のためのobject slotとして再利用している。意味は`otw_part`に記録する。

- `Mori JP podium / aluminum`：格子・外周枠・入口フレーム。
- `Mori JP podium / ceiling`：丸柱・軒天・舗装帯。
- `Mori JP podium / clear glass`：厚み付き三角形の庇ガラス。

周辺建物の削除や非表示化は行わない。原本・source archiveを不変の入力とし、累積patchは承認済みの頂部・外装・低層部を再生成した後、上記3部品を追加する。対象object・feature ID・変更前mesh hashが一致しなければ停止する。

## 再現

`docs/review-harness.md`の環境で以下を実行する。外部の原本とarchiveの取得・配布権については[低層部の説明](mori-podium-v2.md)を参照。

```sh
python scripts/review.py --blender BLENDER --input LEGACY_BLEND --lock manifests/legacy-baseline.json --cameras areas/tokyo-tower/mori-entrance-cameras.json --features areas/tokyo-tower/features.json --patch patches/mori-entrance-v1.json --geometry-source SOURCE_MORI_NPZ --output runs/mori-entrance --device OPTIX --width 960 --height 540 --samples 24 --timeout 1200
```

接写2視点と従来6視点を同一設定で比較する。共通runnerの数値Beforeは固定原本。人間向けHTMLは、前回の低層部復元候補を今回と同じ8カメラ・24 samplesで再レンダリングして左に置く。

## 検証と残課題

生成部材の閉じた面接続・有限座標・非ゼロ面積と、許可外objectへのpatch拒否をテストする。別Blender processで保存meshと生成結果を照合し、確認済みの塔・低層部・全周辺objectの指紋、画像依存が不変であることを確認する。具体的な実行結果はrun・validation JSONに記録する。

入口位置と寸法の人間レビュー、軒先曲線の追加照合、植栽・手すり、周辺地盤の絶対高さ、詳細な干渉・歩行経路検査は残る。今回の幾何検証は、構造計算や現実への完全一致を意味しない。

### 今回の実行結果

Pythonテスト20件、Blender統合テスト2ケース（正常系・画像欠落の検出）が成功。960×540・24 samples・OptiXで8視点のBefore/Afterを生成し、前回候補の比較用8画像も同一設定で再生成した。保存後の別process照合で、上記3部品だけが前回候補から変わり、復元済みpodium・上部タワー・全周辺objectと画像依存は不変。追加meshの保存座標は生成結果のfloat32と完全一致し、全polygonの面積が非ゼロ、追加材質の発光が0であることを確認した。

[実行記録](mori-entrance-v1-run.json) / [保存mesh・変更範囲の検証](mori-entrance-v1-validation.json)

人間向けの比較HTML・実都市画像・blend・元archiveはローカルに保管し、公開PRには独自コード・パッチ・出典リンクと数値検証記録のみを掲載する。
