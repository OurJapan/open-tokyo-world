# 東京タワー：足元・昇降路の比較画像

左が変更前、右が変更後です。フットタウン、外階段、展望台間の開放型昇降路を補った候補です。寸法・細部配置は推定を含みます。

| 視点 | Before | After |
|---|---|---|
| 塔全体 | [![変更前：塔全体](before-tower-context.png)](before-tower-context.png) | [![変更後：塔全体](after-tower-context.png)](after-tower-context.png) |
| 足元のフットタウン | [![変更前：足元のフットタウン](before-foottown-oblique.png)](before-foottown-oblique.png) | [![変更後：足元のフットタウン](after-foottown-oblique.png)](after-foottown-oblique.png) |
| 地上からの外観 | [![変更前：地上からの外観](before-foottown-ground.png)](before-foottown-ground.png) | [![変更後：地上からの外観](after-foottown-ground.png)](after-foottown-ground.png) |
| 塔脚と台座の接点 | [![変更前：塔脚と台座の接点](before-base-connection.png)](before-base-connection.png) | [![変更後：塔脚と台座の接点](after-base-connection.png)](after-base-connection.png) |
| 屋上と階段入口 | [![変更前：屋上と階段入口](before-roof-access.png)](before-roof-access.png) | [![変更後：屋上と階段入口](after-roof-access.png)](after-roof-access.png) |
| 外階段と下部昇降路 | [![変更前：外階段と下部昇降路](before-exterior-stairs.png)](before-exterior-stairs.png) | [![変更後：外階段と下部昇降路](after-exterior-stairs.png)](after-exterior-stairs.png) |
| メインデッキからトップデッキへの昇降路 | [![変更前：メインデッキからトップデッキへの昇降路](before-upper-shaft.png)](before-upper-shaft.png) | [![変更後：メインデッキからトップデッキへの昇降路](after-upper-shaft.png)](after-upper-shaft.png) |
| 上部昇降路の近接 | [![変更前：上部昇降路の近接](before-upper-lift-detail.png)](before-upper-lift-detail.png) | [![変更後：上部昇降路の近接](after-upper-lift-detail.png)](after-upper-lift-detail.png) |
| トップデッキ下の接続 | [![変更前：トップデッキ下の接続](before-top-connection.png)](before-top-connection.png) | [![変更後：トップデッキ下の接続](after-top-connection.png)](after-top-connection.png) |

Blender 4.5.1 LTS、OptiX、1280×848、32 samples、seed 0。同じカメラ・照明・描画条件の18枚です。形状と描画コードは `0254578b2a25cad1a7dac881b2435b5c2da74636`。画素・圧縮データをそのまま保持し、ローカルパス等を含むPNGテキストmetadataだけを除去しています。

[画像・実装のhash](evidence.json) / [保存後の検証](../../../docs/tower-structure-v1-validation.json) / [変更内容と根拠](../../../docs/tower-structure-v1.md)。人間による採用判断は未完了です。

## 出典・利用条件

- 既存都市の地図由来部分：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)、[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)。
- 建物・画像には国土交通省 Project PLATEAU由来の加工データ、独自部品にはark4ez / OurJapanの制作物を含みます。[NOTICE](../../../NOTICE.md)、[都市の出典表示案](../../../sources/city-distribution-NOTICE.draft.md)、[個別ライセンス](../../../LICENSE.md)を参照してください。
- 東京タワー公式・メーカー・施工会社の写真とPDFは参照のみです。[資料一覧](../../../areas/tokyo-tower/tower-structure-sources.json)。画像への貼り込み、テクスチャ転用、原本同梱はありません。

公開対象はPRレビュー用の比較PNG18枚と説明・検証metadataです。都市blend・素材原本の配布や、画像全体へのMIT／CC BY等の一括許諾を意味しません。第三者素材の条件と既存の確認中事項を保持します。
