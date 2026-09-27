# 入口側の園路と旧道路の接続高さの修正候補

[PR #43の診断](mori-plaza-level-audit.md)で見つかった19cm・35cmの段差について、入口に近い2測点を含む接続部を修正します。**PR #40の採用モデルから作るレビュー候補です。共通city基準版への採用・登録は行っていません。**

## 対象と根拠

固定OSMのway `1443867478` は `highway=footway / surface=paving_stones`、version 3、更新日時2026-03-07T08:44:14Zです。旧生成式の幅4.1mと2mの矩形を再現し、保存道路seedのXYと上面高に各15面が一致します。この接続部では、広場輪郭way `1443867470` を道路化した面と歩道の矩形が重なり、PR #39で保護した部分に0.30mの道路面と0.46mの歩道片が残っています。

現地の地盤高や縁石の寸法を確定する資料ではありません。0.11mは採用済み園路から引き継ぐモデル内の高さです。遷移の位置・長さも暫定的な選択であり、実在するスロープの復元、測量、経路案内、バリアフリー適合とは扱いません。

## 変更範囲

入口ローカル座標の中心 `(-22,50)`、8m四方の中心部で道路・歩道の上面を0.11mへ揃え、周囲4mの帯で元の高さへ連続的につなぎます。外縁は16m四方です。対象はその範囲に交差する `asphalt 15s road detail`、`gutter 15s road detail`、`pavement_0 unified road` の面だけです。

道路のXY輪郭と元頂点を保持し、完全に範囲外の面はindex・材質番号・smooth属性まで保持します。境界をまたぐ面は分割します。高さを変えた歩行面は上向きとし、外側の断片は元の向きを保持します。中心部で高さがなくなる旧縁石の側面は除去します。既存の範囲外道路の下向き法線は修正しません。

追加する1部品 `OTW Mori entrance junction / seam fill` は、園路と道路の間に元から存在する数mmの計算上の隙間を埋めます。両側の既存面から各1cm以内、中心部の内側2cmまでに限定した約0.0428m²の閉じた薄い舗装です。既存の手続き型pavement材質を利用します。

建物、採用済み入口、中央広場の舗装本体、芝生、汎用地面、道路のpaint、素材・画像は保持します。全道路の高さ変更や地形の復元は行いません。

## 保存後の確認

Blender 4.5.1 LTSでBefore/Afterを別ファイルへ保存し、別processで再読み込みします。runnerは変更3部品・追加1部品だけを許可し、その他のobject・素材・画像の指紋を比較します。追加validatorはShapelyによるXY輪郭の比較、対象外の面の完全一致、新規面の面積・向き、継ぎ足し舗装の閉形状と範囲を確認します。

元の舗装境界1,820点の両側、周辺の0.5m間隔の格子、入口12点を測定します。優先する2測点では境界を横断する6cmを2mm間隔で検査し、19cm・35cmの段差と数mmの隙間を確認します。中心部の歩行面は上方からも検査します。測点の成功は範囲全体の連続した衝突保証ではありません。

既存7視点に近接2視点を加え、1280×720、Cycles OptiX、32 samples、seed 0、frame 1で比較します。数値・入力hash・実行コードのhashは[実行記録](mori-plaza-connection-v1-run.json)と[保存後検証](mori-plaza-connection-v1-validation.json)に記録します。画像とblendはローカルに保持し、人間による景観・採用判断は未完了です。


2026-09-27の保存候補では、優先2測点の段差が0m／約0.00000036mとなりました。境界の2mm間隔の62測点は全て0.11mで、地面が露出していた6測点も補修できました。道路878測点のうち中心部142点、範囲外565点を確認し、入口12点と中心部の上方243点も成功しています。対象外の道路444,700面を完全一致で保持しました。

回帰検査214件は209成功・5省略、Shapelyを用いる対象テスト8件、Blender統合2ケース、compileallが成功しました。既存のmodifier等の警告36件はBefore/Afterで同一、新しい警告は0件です。9組の比較画像はAIが確認しました。

## 再実行

`CITY_BLEND` は[PR #40の固定lock](../manifests/mori-plaza-landscape-accepted.json)と一致する街全体（558,877,024 bytes、SHA-256 `2e2cce08aa581ef6a99d60c9fe993b8c4e53ff7f5cffb687f9d9c4cee19dc544`）です。`ROAD_INPUTS` は[回収済み制作入力](city-input-recovery.md)のルートで、固定した `work/osm.xml` と `work/twin_towers/tower_surfaces.json` を使います。

`PRODUCTION_PYTHON` はPython 3.12・NumPy 2.3.5・Shapely 2.1.2・GEOS 3.13.1です。`NEW_PLAN`、`NEW_RUN`、`NEW_AUDIT` は未作成ディレクトリを指定します。原本・既存出力を上書きしません。

```sh
python -m unittest discover -s tests
PRODUCTION_PYTHON -m unittest discover -s tests -p test_mori_plaza_connection.py
PRODUCTION_PYTHON scripts/prepare_mori_plaza_connection.py --blender BLENDER --input CITY_BLEND --output NEW_PLAN
python scripts/review.py --blender BLENDER --input CITY_BLEND --lock manifests/mori-plaza-landscape-accepted.json --features areas/tokyo-tower/mori-plaza-landscape-accepted-features.json --cameras areas/tokyo-tower/mori-plaza-connection-cameras.json --patch patches/mori-plaza-connection-v1.json --road-inputs ROAD_INPUTS --connection-plan NEW_PLAN/plan.json --output NEW_RUN --device OPTIX --width 1280 --height 720 --samples 32 --timeout 1200
PRODUCTION_PYTHON scripts/validate_mori_plaza_connection.py --blender BLENDER --before NEW_RUN/before.blend --after NEW_RUN/after.blend --output NEW_AUDIT
```

PowerShellで引用した実行ファイルを起動するときは先頭に `&` を付けます。OptiXがない場合は明示的に `--device CPU` を選びます。planのSHA-256は `8f3380d31e9f12bc6e81709b544ec1a917d40cd5e9d9520e62bc581de1c2b9bb` に固定します。別入力・plan不一致・二重適用は拒否します。

公開物は独自コード・設定・選別した検証metadataです。都市blend、既存画像、OSM、詳細mesh、ローカルplanに新しい配布許諾を与えません。旧都市を含まない公開Moriスターターとは別の制作・検証です。

## 残ること

中心部の外へ続く旧道路と園路の段差、既存の不規則な歩道輪郭・材質、現地の起伏、建物と地図の位置合わせは残ります。暫定的な高さ調整の画像確認と採用判断が必要です。採用後の共通city更新は別途、入力hash・版・登録を揃えて行います。
