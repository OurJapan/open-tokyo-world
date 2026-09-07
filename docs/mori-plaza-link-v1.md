# 入口前から広場側への接続候補

Issue #9。PR #8を取り込んだmain `b4824a83887d4dabf15843daed33f78981064435` を起点に、入口中央の舗装を広場側へ10m延ばす。先端へ向かって幅14mから10mへ絞る120m²の台形だけを修正し、両脇に低い植栽と細い石縁を置く。前回承認された3つの地上object、建物、入口、屋上テラスは保持する。

## 根拠と位置合わせ

2026-09-07に[公式1F平面図](https://www.azabudai-hills.com/floor_map/mori-jp_tower-plaza_1f.html)と[図面画像](https://www.azabudai-hills.com/assets/images/floor_map/floor_1f.jpg)、[日本設計のプロジェクト資料](https://www.nihonsekkei.co.jp/projects/19811/)および[広場写真](https://www.nihonsekkei.co.jp/wp-content/uploads/2025/03/1600x1066_092_71A3817.jpg)を確認した。平面図の森JPタワー、タワープラザ、中央広場の隣接関係と、写真にある舗装・緑地の組合せを参考にした。画像は再配布しない。

位置の基準は、採用済み入口中央と舗装外縁、および保存OSMに対応する広場の地上面。入口の既存座標系 `origin=(-419.80,290.82)`、u方向 `(2,-1)/sqrt(5)`、広場側v方向 `(1,2)/sqrt(5)` を継承した。公式図を測量座標へ変換したものではない。方角は画面の上下では判断せず、既存入口と広場側地表を照合した。写真には広場全体の起伏や階段も見えるが、この10m区間の実測高低差を特定できたわけではない。

調査49地点の下向きrayでは、v=22..38に旧道路、pavement、`park mapped land use`、左側のPLATEAU面が混在した。そこで新しい範囲を中央の台形 `(-7,22),(7,22),(5,32),(-5,32)` に限定する。周辺道路の全体置換はしない。保存OSM由来の旧道路誤表現の根拠は [前回audit](mori-plaza-source-audit.json) を継承する。今回も現在のOSM APIの再照合ではない。

入力は `manifests/mori-plaza-accepted.json` に固定。featureは `otw:jp:tokyo:minato:azabudai-mori-jp`、追加partは `OTW Mori plaza link / paving`、`planters`、`planting` の3個。コード・patchに対象objectと入力mesh hashを明示する。

## 推定と限界

10m、幅14→10m、台形形状、舗装目地、低木の配置と種類は推定。舗装基面は既存端z=.30から既存芝面z=.11へ接続する1.9%勾配で、実物の勾配ではない。タイル表面には3mmの凹凸を付ける。端は既存モデルの緑地で終わり、実物のCentral Green全体の園路再現ではない。

許可範囲外には旧道路の不自然な形状が残る。公開画像の権利、正確な地形・階段、現実の植栽、全域の歩行経路やバリアフリー基準への適合は未解決。原本を一括削除してこれらを隠さない。

## 再実行

Blender 4.5.1と前回採用blendを別途用意する。`BLENDER`、`ACCEPTED_BLEND`、`NEW_RUN` は実際のパスへ置換し、出力先は新規にする。

```sh
python -m unittest discover -s tests
python scripts/review.py --blender BLENDER --input ACCEPTED_BLEND --lock manifests/mori-plaza-accepted.json --features areas/tokyo-tower/mori-plaza-link-features.json --cameras areas/tokyo-tower/mori-plaza-link-cameras.json --patch patches/mori-plaza-link-v1.json --output NEW_RUN --device OPTIX --width 960 --height 540 --samples 24 --timeout 1200
BLENDER --factory-startup --background --disable-autoexec --python-exit-code 1 --python scripts/validate_mori_plaza_link.py -- --before NEW_RUN/before.blend --after NEW_RUN/after.blend --output NEW_AUDIT.json
```

保存後の別processで元の路面頂点の完全保持、対象外面の保持と面積誤差、追加meshの閉じた辺・非ゼロ面・範囲・非発光を検査する。通路3列×6地点のrayで、既存舗装→今回舗装→既存芝の表面が見えるかと高さを検査する。全既存objectと画像素材の変更範囲はreview runnerで検査する。検証結果は `mori-plaza-link-v1-validation.json`、描画とcode hashは `mori-plaza-link-v1-run.json` に記録する。

実行結果：32契約テスト、Blender統合2ケース、6視点12画像、保存後geometry検査が成功。既存変更は路面3object、新規は指定した3objectだけ。路面の範囲外面積誤差は最大0.000019m²未満。通路18地点のrayは期待したobjectと高さを確認できた。先端タイルと芝の差は約3mm。描画はBefore 50.969秒／After 40.672秒で大きな悪化は観測しなかったが、1回の実行であり性能改善の保証ではない。
