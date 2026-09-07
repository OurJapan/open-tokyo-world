# 低層部の屋根・壁の欠落を修正

入口の比較画像に対し、人間レビューで「屋根と壁が開いているように見える」と報告された。調査の結果、低層部を復元したv2の選択条件に不備があった。

## 原因

v2は「三角形の全頂点が高さ40m以下」の面だけを採用していた。実際のsource archiveには、低層部の屋根・壁が約40.681m、45.683m、46.947mまで続いている。境界をまたぐ面を丸ごと捨てたため、屋根と壁がつながらなくなっていた。

前回の「元データの選択結果と一致」「全三角形の面積が非ゼロ」という検査だけでは、選択条件そのものの誤りを検出できなかった。以前の検証成功は、低層部が閉じていることの証明ではない。入口追加が原因ではなく、その前の低層部復元に含まれた不具合。

## 修正と根拠

入力archiveとhashは[v2](mori-podium-v2.md)と同一。batch 5の面高さを調べ、低層部の最高点約46.947mと、その次の高層タワー面約319mの間に大きな空白があることを確認した。v3はこの空白内の50mを選択上限に使い、低層部の1,070三角形を採用する。高さ50mで面を切断・変形する処理ではない。欠けていた403面を元データの座標のまま追加する。

変更対象は`Mori JP podium / stone`のみ。頂部、暗いガラス、縦帯、直前に追加した庇・柱・扉枠、周辺都市objectを保持する。元データ・画像の配布方針も変えない。

## 再発防止

1cm単位で重複頂点を照合し、採用した面の隣に、誤って捨てた低層部の面がないか検査する。40m条件では83辺で検出し、修正条件では0辺になった。同じ誤りを再現する小さな屋根fixtureもテストへ追加した。

高層タワーの元面は詳細タワーで置換するため、この低層部の隣接検査から除外する。したがって全sceneのwatertightnessを保証する検査ではない。建物の正確さや置換タワーとの接合は、別途画像と地物単位で確認する。

## 再現と比較

`mori_podium_v3`を含む累積patchを固定原本へ適用する。原本やarchiveを上書きしない。

```sh
python scripts/review.py --blender BLENDER --input LEGACY_BLEND --lock manifests/legacy-baseline.json --cameras areas/tokyo-tower/mori-entrance-cameras.json --features areas/tokyo-tower/features.json --patch patches/mori-podium-repair-v3.json --geometry-source SOURCE_MORI_NPZ --output runs/podium-repair --device OPTIX --width 960 --height 540 --samples 24 --timeout 1200
```

人間向け比較では、左に不具合を含んだ直前の入口候補、右に今回の修正を置く。同一の8カメラ・照明・seed・24 samples。数値Beforeは共通runnerの固定原本であり、画像の左とは異なる。

[実行記録](mori-podium-repair-v3-run.json) / [保存形状・追加面・隣接検査](mori-podium-repair-v3-validation.json)

検証結果：Pythonテスト22件、Blender統合テスト2ケースが成功。8視点の比較画像を生成し、保存後の別process照合で1,070三角形が元データの選択結果とfloat32で完全一致、全polygonが非ゼロ面積であることを確認した。直前の入口候補から変わったobjectは`Mori JP podium / stone`だけで、上部タワー・入口3部品・全周辺object・画像依存は不変。実行コードのhashも記録する。実都市の画像・blend・archiveはローカルのみ。
