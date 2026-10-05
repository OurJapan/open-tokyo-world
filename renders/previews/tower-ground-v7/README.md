# 東京タワーの地盤・塔脚外装の比較

同じカメラ・照明で描画した10視点・20枚の変更前後です。重なる駐車区画を除去し、北側階段・地盤と南側舗装を修正しました。台座の上広がり外装と下部鉄骨の接合部を追加しています。台座高さ・階段の蹴上げ・部材寸法は推定を含み、実測済みの完成モデルではありません。

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
| 北側の8段階段 | [![変更前](before-north-stairs.png)](before-north-stairs.png) | [![変更後](after-north-stairs.png)](after-north-stairs.png) |
| 下部鉄骨の接合部 | [![変更前](before-base-joints.png)](before-base-joints.png) | [![変更後](after-base-joints.png)](after-base-joints.png) |

Blender 4.5.1 LTS、OptiX、1280×848、32 samples、seed 0。実装・描画時commit: `08aa1585910930ef1a53c60564ecb04a9319998e`。PNGのテキストmetadataだけを除去し、圧縮データと復号画素を保持しています。

[変更内容・推定箇所](../../../docs/tower-ground-v7.md) / [保存後検証](../../../docs/tower-ground-v7-validation.json) / [画像・コードのhash](evidence.json)。人間による採用判断は未完了です。

## 出典・公開範囲

- 地図由来部分：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)、[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)。
- 国土地理院の標高データを加工して北側階段の高低差と南側舗装を暫定再構成しています。個々の段差・敷居の実測値ではありません。
- 建物・画像には国土交通省 Project PLATEAU由来の加工データとark4ez / OurJapanの独自制作物を含みます。[NOTICE](../../../NOTICE.md)、[都市の出典表示案](../../../sources/city-distribution-NOTICE.draft.md)、[個別ライセンス](../../../LICENSE.md)を参照してください。
- [参照資料台帳](../../../areas/tokyo-tower/tower-ground-v7-sources.json)。写真・PDFの貼り込み、テクスチャ転用、原本同梱はありません。

公開対象はPRレビュー用PNG20枚と説明・検証metadataです。都市blend・素材原本の配布や、画像全体へのMIT／CC BY等の一括許諾を意味しません。第三者素材の条件と既存の確認中事項を保持します。
