# 街全体の出典表示案 — 配布条件の確認中

この文書は配布パッケージに同梱するNOTICEの下書きです。対象版はPR #12採用版と、その外壁材質の差し替え候補です。個別データの条件と全構成部品の対応が未確定のため、全体の配布許可を表しません。

## 建物データ・画像

国土交通省 Project PLATEAUの次のデータを解析・加工して利用（OurJapan）。

- [港区2025年度](https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025)：LOD3配信。
- [千代田区2025年度](https://www.geospatial.jp/ckan/dataset/plateau-13101-chiyoda-ku-2025)：LOD2配信。
- [中央区2025年度](https://www.geospatial.jp/ckan/dataset/plateau-13102-chuo-ku-2025)：LOD2配信。

[PLATEAUサイトポリシー](https://www.mlit.go.jp/plateau/site-policy/)を参照。入力のURL・固定hashは [image source lock](city-pr12-image-source-lock.json)、画像同一性の照合は [image audit](city-pr12-image-audit.json) に記録しています。3区の個別条件・例外の最終確認は未完了です。

確認した加工：画像のBlender材質への利用、168画像の縮小後RGBA8一致。形状側の座標変換・底面移動等の既存記録はありますが、街全体の全メッシュを元形状へ照合したものではありません。本モデルはOurJapanによる加工物であり、公式モデルや国土交通省の承認を意味しません。

## 地図由来の道路・配置

地図データ：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)。[Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/)。

保存OSMとその加工経路、配布する派生データの範囲・取得先は未確定です。最終配布物では該当データのNOTICE・ライセンスと、公開形態に必要な表示を保持します。

## 個別に許諾を記録した独自部品

- 東京タワー77部品：[資産ライセンス](../assets/tokyo-tower/ASSET-LICENSE.md)、[対象版](../assets/tokyo-tower/provenance.json)。
- 森JPの独自13部品：[資産ライセンス](../starter/mori/ASSET-LICENSE.md)、[対象版](../starter/mori/provenance.json)。
- 広場6部品：[資産ライセンス](../starter/plaza/ASSET-LICENSE.md)、[対象版](../starter/plaza/provenance.json)。

指定された独自部分はark4ez / OurJapan、CC BY 4.0。第三者の基礎データは元の条件を保持します。全体blend中の部品と許諾済み版の対応付けは別途必要です。

外壁差し替え候補は `scripts/city_facades.py` の独自の数式材質を用い、未確認画像 `facade_atlas.png` を含みません。元の登録版には同画像が残ります。コードのライセンス範囲は [LICENSE.md](../LICENSE.md) を参照してください。

## 確定時に埋める項目

- 採用candidateのhash、全ファイル一覧、公開取得先。
- 各datasetの個別条件・第三者権利に関する確認記録。
- OSM由来の元データ・派生データ・表示物の提供範囲。
- 簡易建物・植栽・車両など、残る構成要素の由来と許諾。
