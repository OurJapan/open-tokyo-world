# 東京タワーの地盤・塔脚外装の比較

同じカメラ・照明で描画した12視点・24枚の変更前後です。車両の2視点だけは、元からレンダー非表示の車両を一時表示した接地確認用の診断画像です。Before/Afterに同じ表示を適用し、blendの表示設定は保存変更していません。南側駐車場・入口舗装・車路と地面を共通の高さで接続し、台座を鉄骨軸に沿って傾斜させました。保存OSMと矛盾した北側階段の手すりを非表示にしました。台座高さ・階段の蹴上げ・部材寸法は推定を含み、実測済みの完成モデルではありません。

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
| 南側車両の接地（診断表示） | [![変更前](before-south-road-vehicle.png)](before-south-road-vehicle.png) | [![変更後](after-south-road-vehicle.png)](after-south-road-vehicle.png) |
| 西側車両の接地（診断表示） | [![変更前](before-west-road-vehicle.png)](before-west-road-vehicle.png) | [![変更後](after-west-road-vehicle.png)](after-west-road-vehicle.png) |

Blender 4.5.1 LTS、OptiX、1280×848、32 samples、seed 0。実装・描画時commit: `4a8071eeeeeea89ad86f5cd87fd0d1f8fbaa3cdb`。PNGのテキストmetadataだけを除去し、圧縮データと復号画素を保持しています。

[変更内容・推定箇所](../../../docs/tower-site-v8.md) / [保存後検証](../../../docs/tower-site-v8-validation.json) / [画像・コードのhash](evidence.json)。人間による採用判断は未完了です。

## 出典・公開範囲

- 地図由来部分：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)、[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)。
- 国土地理院の標高データを加工して前版の南側相対高さを維持し、周辺舗装へ接続しています。個々の段差・敷居の実測値ではありません。
- 建物・画像には国土交通省 Project PLATEAU由来の加工データとark4ez / OurJapanの独自制作物を含みます。[NOTICE](../../../NOTICE.md)、[都市の出典表示案](../../../sources/city-distribution-NOTICE.draft.md)、[個別ライセンス](../../../LICENSE.md)を参照してください。
- [参照資料台帳](../../../areas/tokyo-tower/tower-site-v8-sources.json)。写真・PDFの貼り込み、テクスチャ転用、原本同梱はありません。

公開対象はPRレビュー用PNG24枚と説明・検証metadataです。都市blend・素材原本の配布や、画像全体へのMIT／CC BY等の一括許諾を意味しません。第三者素材の条件と既存の確認中事項を保持します。
