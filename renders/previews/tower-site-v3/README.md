# 東京タワーの敷地・屋上・階段接続の比較

同じカメラ・照明で描画した変更前後です。方位変更のため対象の向きは変わりますが、カメラは固定しています。既存8視点と追加5視点の全26枚です。寸法・地形境界・内装通路には推定を含みます。

| 視点 | 変更前 | 変更後 |
|---|---|---|
| 正面全景 | [![変更前](before-foottown-front.png)](before-foottown-front.png) | [![変更後](after-foottown-front.png)](after-foottown-front.png) |
| 正面の庇と入口 | [![変更前](before-foottown-entrance.png)](before-foottown-entrance.png) | [![変更後](after-foottown-entrance.png)](after-foottown-entrance.png) |
| 塔脚と建物 | [![変更前](before-foottown-context.png)](before-foottown-context.png) | [![変更後](after-foottown-context.png)](after-foottown-context.png) |
| 南側外観 | [![変更前](before-foottown-south.png)](before-foottown-south.png) | [![変更後](after-foottown-south.png)](after-foottown-south.png) |
| 屋上全体 | [![変更前](before-foottown-roof.png)](before-foottown-roof.png) | [![変更後](after-foottown-roof.png)](after-foottown-roof.png) |
| 屋上中央棟 | [![変更前](before-foottown-roof-core.png)](before-foottown-roof-core.png) | [![変更後](after-foottown-roof-core.png)](after-foottown-roof-core.png) |
| 屋上階段への通路 | [![変更前](before-foottown-roof-access.png)](before-foottown-roof-access.png) | [![変更後](after-foottown-roof-access.png)](after-foottown-roof-access.png) |
| 塔全体 | [![変更前](before-tower-context.png)](before-tower-context.png) | [![変更後](after-tower-context.png)](after-tower-context.png) |
| 敷地方向と周辺 | [![変更前](before-site-overhead.png)](before-site-overhead.png) | [![変更後](after-site-overhead.png)](after-site-overhead.png) |
| 南2階入口と舗装 | [![変更前](before-site-south.png)](before-site-south.png) | [![変更後](after-site-south.png)](after-site-south.png) |
| 屋上周辺棟と設備 | [![変更前](before-roof-equipment.png)](before-roof-equipment.png) | [![変更後](after-roof-equipment.png)](after-roof-equipment.png) |
| 屋外階段から客用床への接続 | [![変更前](before-deck-connection.png)](before-deck-connection.png) | [![変更後](after-deck-connection.png)](after-deck-connection.png) |
| 上部架構（形状は維持） | [![変更前](before-upper-context.png)](before-upper-context.png) | [![変更後](after-upper-context.png)](after-upper-context.png) |

Blender 4.5.1 LTS、OptiX、1280×848、32 samples、seed 0。実装・描画時commit: `e15531182fa7c55687b8fdab1c13d546c67d3d0c`。PNGのテキストmetadataだけを除去し、圧縮データと復号画素を保持しています。

[変更内容・推定箇所](../../../docs/tower-site-v3.md) / [保存後検証](../../../docs/tower-site-v3-validation.json) / [画像・コードのhash](evidence.json)。人間による採用判断は未完了です。

## 出典・公開範囲

- 地図由来部分：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)、[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)。
- 国土地理院の標高データを相対地盤高の照合に使用しています。
- 建物・画像には国土交通省 Project PLATEAU由来の加工データとark4ez / OurJapanの独自制作物を含みます。[NOTICE](../../../NOTICE.md)、[都市の出典表示案](../../../sources/city-distribution-NOTICE.draft.md)、[個別ライセンス](../../../LICENSE.md)を参照してください。
- [参照資料台帳](../../../areas/tokyo-tower/tower-site-v3-sources.json)。写真・PDFの貼り込み、テクスチャ転用、原本同梱はありません。

公開対象はPRレビュー用PNG26枚と説明・検証metadataです。都市blend・素材原本の配布や、画像全体へのMIT／CC BY等の一括許諾を意味しません。第三者素材の条件と既存の確認中事項を保持します。
