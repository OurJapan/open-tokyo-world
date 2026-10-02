# 東京タワー直下・フットタウンの外観

均等な小窓を並べた旧候補から、写真で確認できる正面玄関、上層壁、駐車場側出入口、屋上中央棟へ置き換える増分です。トップデッキ昇降設備を詳細化した [PR #59](https://github.com/OurJapan/open-tokyo-world/pull/59) の保存候補を入力にしています。

## 変更

- 主正面の下部を淡色パネル壁にし、奥まったガラス入口群、横長の上階開口、幅広い薄い庇、縦長のガラス帯がある角柱を配置。
- 濃茶色の大きな上層壁、上端の上下にずれた小正方形窓、中央の淡色スクリーンを再構成。
- 駐車場側に別の出入口、低い庇、外壁の銀色角ダクトを配置。
- 一律の四隅HVACを撤去し、昇降路の根元に茶色い中央棟、小窓、ルーバー、金属扉、ステー付き庇を追加。外周には立ち上がり壁と縦桟の柵を設ける。
- 旧FootTownの4メッシュを置換し、仕上げ用3メッシュを追加。共有されていたガラス・金属素材は変更せず、7種類の専用素材を使用。
- 正面の1F床・入口・柱を既存地表へ接地。旧床の約50cmの浮きを解消し、庇下の床からガラス扉の敷居まで連続させる。

## 根拠と推定

[資料台帳](../areas/tokyo-tower/foottown-v2-sources.json)に、運営者のフロア案内、TOKYO TOWER提供写真、撮影者本人の正面・屋上写真、観察範囲、参照原本のhashを記録しています。古い写真の店舗看板やイベント装飾は再現しません。参考写真・PDF・テクスチャ原本は公開しません。

73×58mの外形と屋上高さ16.2mは既存モデルの近似寸法です。写真から確認できる構成をこの外形に合わせており、測量モデルではありません。庇、柱割り、窓位置、中央棟の寸法と仕上げ色は推定です。中央の淡色面の正確な製品・材質は確認できていません。

正面・南側の入口付近は保存シーンの下向きraycastで地表Z=0を確認しました。1F床上をZ=0.02に合わせています。これはシーン内の接地検査で、現地標高の測量値ではありません。離れた右側の既存歩道にはZ=0.46の区間が残ります。

東京都の案内に記載された有効幅155cmは1F正面玄関の値です。本候補で他の扉へ同じ幅を適用した部分は制作上の推定であり、全6組を実測したものではありません。

公式1F図のNorth/East階段表示と全体案内から、実物の主正面は北東側と判断しています。本候補では既存の軸に沿った塔・建物配置を保持し、正面を+Y側へ近似登録しています。実際の敷地回転、地形の高低、道路との位置合わせを復元したという意味ではありません。

南側出入口は公式に2Fと案内されています。本候補ではこの高さを保ち、平坦な既存地盤から入るための直階段を付加しています。実物の駐車場地盤の復元ではなく、既存シーンへの推定接続です。内装・店舗、扉の開閉動作、設備の工学的寸法は対象外です。

## 固定入力と再実行

入力は `7a5cd95d2223092a1a2931131eeadd3978605d8e7293b5908aada3b13f301350`、631,833,930 bytesのPR #59候補です。一般のcity登録入力や公開Mori profileとは別の入力で、blendは再配布しません。正当なローカル入力を持つ環境で、毎回新しい出力先を指定します。

```powershell
python scripts/review.py --blender BLENDER --input PR59_CANDIDATE --lock manifests/foottown-v2-input.json --cameras areas/tokyo-tower/foottown-v2-cameras.json --features areas/tokyo-tower/foottown-v2-features.json --patch areas/tokyo-tower/foottown-v2-patch.json --output data/local/reviews/foottown-v2-review --device OPTIX --width 1280 --height 848 --samples 32 --timeout 1200
```

入力hash、4対象のmesh hash、7部品の名前、追加数を固定し、別入力や二重適用は拒否します。元入力へ保存せず、出力を別Blenderプロセスで開き直して検査します。検証成功と実物精度・人間の採用判断は区別します。

保存モデルの独立検査も、新しいJSON出力先を指定して実行します。

```powershell
python scripts/validate_tower_foottown.py --blender BLENDER --input data/local/reviews/foottown-v2-review/after.blend --original PR59_CANDIDATE --output data/local/reviews/foottown-v2-review/saved-geometry-validation.json --timeout 1200
```

## 検証結果と画像

[同条件の8視点・16枚](../renders/previews/foottown-v2/README.md) / [保存後検証の記録](foottown-v2-validation.json) / [画像とコードのhash](../renders/previews/foottown-v2/evidence.json)

2026-10-03、Blender 4.5.1 LTS・OptiX、1280×848・32 samples・seed 0で確認しました。実装と描画時のcommitは `ba72fa0f471013db3836fd50b9719c84d1f7ae74` です。

- portable checks 398件：390成功、任意依存8省略。構文検査も成功。
- 別プロセスで保存候補を開き直し、7部品の閉形状、入口6組、正面床と柱の接地、南25段階段、屋上昇降路、既存階段50床面の頭上空間を確認。
- FootTown以外の既存3,354 objects、元の素材・画像資産・metadataと表示状態は不変。原本と保存候補のhashも検査前後で不変。
- 公開PNGはテキストmetadataだけを除去し、圧縮画像データと復号後の画素が元レンダーと同一であることを確認。

既存入力には5個の空メッシュとmodifier指紋の検査制限があり、その警告は変更前後で同じです。地理位置・寸法・敷地高低の推定は上記の通り残ります。人間の画像レビューと採用判断は未完了です。
