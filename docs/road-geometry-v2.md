# 東京タワー周辺の道路・歩道の接続と細部

PR #68の採用候補を不変入力として、西側と南側の道路・歩道を連続した輪郭へ整えます。旧生成の線分ごとの長方形に残る切れ目・尖った接合部を、保存OSMの中心線とタグ幅または既存の既定幅を維持した輪郭へ置換します。車道、側溝、歩道と駐車場を分割し、重なる路面を整理します。タワー・FootTown・階段・植栽・交通の表示状態と形状は保持します。

編集範囲はタワー制作座標の `(-72,-65)–(-37,38)` と `(-37,-100)–(40,-55)` です。新しい測量基準を設けず、採用済みv8の相対地盤を引き継ぎます。舗装輪郭は1mm格子、曲線は四半円24分割、地盤の三角形は1m格子で生成します。歩道の上下面・側面は共通の境界で閉じた形状にします。範囲外の元の面と属性、元頂点を保持します。

新しい歩道の制作上の基本高は車道から16cmです。編集境界の内側2mでは保存入力の歩道上面へ滑らかに戻し、旧モデルの高さとの新しい段差を避けます。二つの編集矩形の共通辺は内部として扱います。旧歩道の切れ目で上面を検出できない頂点には、旧モデルの地域別の暫定高さを使用し、その件数を記録します。現地の切り下げ位置・造成勾配を確定したものではありません。

旧路面の一部には下向きの面法線があります。下向きrayの最初の交差位置で幾何学的な上面高を計測し、法線が下向きという理由だけで高さを捨てません。原モデルの面向きを全域で変更したものではありません。

歩道・側溝の新しい面に、近いOSM中心線からの延長距離・左右距離に基づくUVを付け、目地を経路に沿わせます。既存の元材質とPR #68の仕上げ材質を保持し、UVを読む専用材質2個を追加します。目地の実物の割り付けや歩道・側溝寸法を測量したものではありません。

既存の蓋・排水口の金属部品と駐車区画の白線について、変更範囲内の既存位置を保ち、保存された路面への接地を調整します。道路標示やマンホールを想像した位置へ新設しません。位置そのものは旧制作の推定配置であり、現地写真による全件の位置確認は未完了です。白線は既存の駐車場・入口舗装上でのみ調整します。

## 入力・出典

- 入力：`data/local/reviews/road-finish-v1-final-01/after.blend`、SHA-256 `959610fc3c3b1f6eca725de5666a2c5fd218f7ea33cc90b8bf5f7300e65bb877`。
- 保存OSM：SHA-256 `f04e8e70ab24a61ca749375d1ef37401feb0fdc840cc506b670ef71454a6a8ab`。© OpenStreetMap contributors、ODbL 1.0。取得日時不明の固定版です。
- 地盤・塔脚の根拠と推定：[v8の記録](tower-site-v8.md)。入力の全都市公開配布は未整備です。
- 近景設備は[旧制作の出典](city-production-sources.md)に記録された推定配置を継承します。
- [東京タワー公式の南側出入口](https://www.tokyotower.co.jp/foottown/uq76y55913.html)は駐車場への直結を説明しています。今回、南側出入口の敷居は変更しません。
- [東京都の施設調査](https://www.daredemo-tokyo.metro.tokyo.lg.jp/facility/leisure/40137/)は2024-12-11調査で1階正面玄関の段差2cm未満を記載しています。周辺全歩道の段差・勾配の資料ではなく、新しい縁石切り下げ位置の根拠には使用していません。

## 再生成・検証

Shapely 2.1.2で固定OSMと固定入力から抽出した路面輪郭を読み、[計画](../areas/tokyo-tower/road-geometry-v2-plan.json)を生成します。[固定入力](../areas/tokyo-tower/road-geometry-v2-input.json)がplanをhashに固定します。[実装](../scripts/road_geometry_v2.py)の各phaseをBlender 4.5.1 LTSの別プロセスで実行します。出力先は毎回新しいフォルダーです。

[路面抽出](../scripts/export_road_geometry_v2.py)をBlenderから `--input INPUT --output LOCAL_SURFACES_JSON` で実行します。[plan生成](../scripts/prepare_road_geometry_v2.py)には `--osm SAVED_OSM --surfaces LOCAL_SURFACES_JSON --output NEW_PLAN` を渡します。抽出JSONはローカルに保持し、原シーンへの保存は行いません。

```powershell
& BLENDER --factory-startup -b --threads 2 --disable-autoexec --python-exit-code 1 --python scripts/road_geometry_v2.py -- --phase PHASE --input INPUT --output NEW_RUN
# build → validate → render-before → render-after
python -m unittest discover -s tests
```

検証は全都市の対象外指紋・メタデータ・材質・画像依存・データ数、範囲外の面と元頂点、planとの一致、歩道の閉鎖性、路面細部の接地を確認します。既存modifier・animation・ネストしたノードグループの完全な指紋には対応していません。点検査を全域の安全性・バリアフリー性能の認証とは扱いません。

公開対象は独自コード、派生metadata、PR比較PNGです。都市blend、原素材、音源、参照写真・PDFは同梱しません。人間による採用判断は未完了です。

比較画像のうち `surface-details-close` だけは、元から描画非表示の近景設備コレクションで金属の蓋・排水口の2材質オブジェクトを一時表示します。Before/Afterに同じ診断表示を適用し、他の6視点の通常表示と区別します。この表示操作はblendへ保存しません。
