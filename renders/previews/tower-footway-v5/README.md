# 東京タワーの歩道・側溝の比較

同じカメラ・照明で描画した8視点・16枚の変更前後です。局所的な歩道・側溝の断片と継ぎ目を修正しています。保存OSMの経路に基づきますが、歩道幅・地盤高はモデル上の推定です。地図上の階段の実際の段差高は今回復元していません。

| 視点 | 変更前 | 変更後 |
|---|---|---|
| 正面全景 | [![変更前](before-foottown-front.png)](before-foottown-front.png) | [![変更後](after-foottown-front.png)](after-foottown-front.png) |
| 塔全体 | [![変更前](before-tower-context.png)](before-tower-context.png) | [![変更後](after-tower-context.png)](after-tower-context.png) |
| 敷地俯瞰 | [![変更前](before-site-overhead.png)](before-site-overhead.png) | [![変更後](after-site-overhead.png)](after-site-overhead.png) |
| 南側舗装 | [![変更前](before-south-grade.png)](before-south-grade.png) | [![変更後](after-south-grade.png)](after-south-grade.png) |
| 南側の基礎と車路 | [![変更前](before-foundation-close.png)](before-foundation-close.png) | [![変更後](after-foundation-close.png)](after-foundation-close.png) |
| 北側の対向する基礎 | [![変更前](before-foundation-opposite.png)](before-foundation-opposite.png) | [![変更後](after-foundation-opposite.png)](after-foundation-opposite.png) |
| 北側の歩道 | [![変更前](before-foundation-north.png)](before-foundation-north.png) | [![変更後](after-foundation-north.png)](after-foundation-north.png) |
| 南側の対向する基礎 | [![変更前](before-foundation-west.png)](before-foundation-west.png) | [![変更後](after-foundation-west.png)](after-foundation-west.png) |

Blender 4.5.1 LTS、OptiX、1280×848、32 samples、seed 0。実装・描画時commit: `001f1bc4ada50a3c2e7f8caf5bccee91876375b3`。PNGのテキストmetadataだけを除去し、圧縮データと復号画素を保持しています。

[変更内容・推定箇所](../../../docs/tower-footway-v5.md) / [保存後検証](../../../docs/tower-footway-v5-validation.json) / [画像・コードのhash](evidence.json)。人間による採用判断は未完了です。

## 出典・公開範囲

- 地図由来部分：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)、[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)。
- 前回の国土地理院標高データによる相対地盤高の照合を継承し、今回は既存都市の表面へ局所接続しています。
- 建物・画像には国土交通省 Project PLATEAU由来の加工データとark4ez / OurJapanの独自制作物を含みます。[NOTICE](../../../NOTICE.md)、[都市の出典表示案](../../../sources/city-distribution-NOTICE.draft.md)、[個別ライセンス](../../../LICENSE.md)を参照してください。
- [参照資料台帳](../../../areas/tokyo-tower/tower-footway-v5-sources.json)。写真・PDFの貼り込み、テクスチャ転用、原本同梱はありません。

公開対象はPRレビュー用PNG16枚と説明・検証metadataです。都市blend・素材原本の配布や、画像全体へのMIT／CC BY等の一括許諾を意味しません。第三者素材の条件と既存の確認中事項を保持します。
