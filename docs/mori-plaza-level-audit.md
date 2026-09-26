# 中央広場と旧道路の接続高さの調査

2026-09-27、[共通city基準版](city-baseline-pr40.md)を反映する[PR #41](https://github.com/OurJapan/open-tokyo-world/pull/41)がmain `7492c9e` に取り込まれました。その固定モデルで、中央広場の舗装と旧道路の境界を読み取り専用で調べました。**この変更は計測ツールと診断記録の追加です。都市形状はまだ変更していません。**

## 確認できた高さの差

中央広場の舗装はモデル内の高さ `z=0.11m`、旧道路面は `z=0.30m`、旧歩道面は `z=0.46m` でした。舗装の上面境界に沿って1,820点を選び、その両側2cmの位置から下向きに測定しました。

| 舗装の隣で検出したobject | 相手の高さ | 舗装からの高さの差 | 測点の組数 |
|---|---:|---:|---:|
| `asphalt 15s road detail` | 0.30m | 19cm | 508 |
| `gutter 15s road detail` | 0.30m | 19cm | 31 |
| `pavement_0 unified road` | 0.46m | 35cm | 30 |

569組は近接する測点の組数であり、569箇所の独立した不具合ではありません。道路との境界すべてが歩行者の接続箇所とも限りません。境界の内外4cmを挟んだ表面の差を測っており、実物の縁石寸法を測定した値ではありません。

入口から左へ曲がる推定園路の末端に近い境界でも、19cmと35cmの差を検出しました。測点は既存入口座標系の `(u,v)=(-21.8642,50.2447)` と `(-22.7547,49.8004)` です。固定モデルから2視点を追加描画し、園路の前に旧道路面と不規則な歩道片が高く残っていることを確認しました。画像と詳細座標はローカルに保持します。

## 高さの根拠を分ける

旧制作commit `defac576e076f40bf3bc4fddcdcefe30f9a009f7` の固定コードを読み、[制作コード台帳](../manifests/legacy-production-sources.json)とファイルhashが一致することを確認しました。

- `work/wide_detail/roads.py` は地上道路の高さを0.30mに固定し、pavementには0.16mを加えています。
- `work/tower15_env/surfaces.py` はasphaltとgutterの上面を0.30mに固定しています。
- PR #40の芝生・舗装は、既存芝生と入口末端に合わせた0.11mです。これも現地測量による地盤高ではありません。

今回の測定値は、この高さの設定と一致します。コード上の相対高さを実際の地形として扱うことはできません。

[設計者の説明](https://www.nihonsekkei.co.jp/think/ideas/case-study_20892/)では、麻布台ヒルズの敷地全体に東西約18mの高低差があります。[森ビルの計画説明](https://www.mori.co.jp/projects/azabudaihills/concept/)も地形を生かしたランドスケープを示しています。これらは敷地の起伏の根拠になりますが、今回の2測点で階段・縁石・傾斜を何cmにするかの根拠にはなりません。確認日は2026-09-27です。

## 同じ基準で再計測する

入力はPR #40採用版（558,877,024 bytes、SHA-256 `2e2cce08aa581ef6a99d60c9fe993b8c4e53ff7f5cffb687f9d9c4cee19dc544`）です。[固定lock](../manifests/mori-plaza-landscape-accepted.json)で照合します。

```powershell
$blender = 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe'
$python = 'C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe'

& $python scripts/audit_mori_plaza_levels.py --blender $blender --input 'C:\Received\city-pr40.blend' --output data/local/audits/plaza-levels-new
```

出力先は未作成のディレクトリを指定します。入力版が違う場合や出力先が既存の場合は停止します。Blenderの自動スクリプト実行を無効化し、frame 1で調べ、処理後に入力hashが不変であることを確認します。blendを保存する処理はありません。

`summary.json` は集計、`samples.json` は両側の測点と検出surface、`contacts.json` は舗装と道路の測定組、`run.json` は実行コード・入力hashと結果です。詳細座標・絶対パスを含むログはGitへ追加しません。[公開する検証metadata](mori-plaza-level-audit-verification.json)には集計・hash・確認範囲だけを記録します。

[入口近くの2視点](../areas/tokyo-tower/mori-plaza-level-cameras.json)も固定しました。画像を再生成する場合は既存のreview runnerへこのカメラ設定、PR #40の採用lock、`mori-plaza-landscape-accepted-features.json` を指定し、patchを付けずに実行できます。今回の観察画像は960×540、Cycles OptiX、24 samples、seed 0です。画像の閲覧はローカルで行い、都市モデルや画像をこのPRへ同梱しません。

検査の成功は「計測が完了し入力が変わらなかった」という意味です。段差の解消や都市モデルの合格を意味しません。高さ2mから下にあるsurfaceのみを見ており、頭上障害物、境界全体の連続性、他の道路・芝生境界、現実の歩行経路の正しさは対象外です。既存の道路上面には下向き法線もありますが、ray hitの高さは測定でき、ここでは法線を修正していません。

## 次の形状修正の対象

入口からの導線に近い上記2測点を含む接続部を優先します。旧道路面が現地の車道・園路・縁石のどれに対応するかを固定入力へ照合し、変更範囲を限定します。現地の高さが未確定な場合は、現実地形の復元と、既存モデル内での暫定的な接続の改善を区別してレビューします。

全道路を一括で下げたり、測定値だけで実在の階段・スロープを追加したりはしません。次の候補では今回の固定測点を引き継ぎ、入口と対象外道路の保持、保存後の再読み込み、同条件Before/Afterを確認します。採用モデルと既存の編集コピーはそのままです。
