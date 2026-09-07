# データソース・ライセンス・容量

公式情報の確認日：2026-09-07。以下は採用設計であり、個別assetの権利監査完了を示すものではありません。

## PLATEAUは既に利用されている

ローカル `work/detail_upgrade/selected_tiles.json` は港区、year=2025、spec=5.0、3D Tiles 1.0、texture=true、LOD表記3、file_size=369,231,400を記録しています。これは保存済みcatalog値であり、現在の配信容量・全地物LOD3を保証しません。実装自身もmixed source detailと記録しています。

記録されたtilesetは [港区2025の配信入口](https://api.plateauview.mlit.go.jp/datacatalog/3dtiles/13103-bldg-lod3-texture-2025/tileset.json)。再利用時は配信URL、実データhash、年度、地物の実LODを固定します。G空間の候補ページ取得は今回403等で失敗し、2025港区の個別resource利用条件をオンラインで確定できていません。PLATEAUサイト全体の条件だけで個別textureの配布を承認しません。

## 取込経路の比較

| 経路 | 採用判断 | 検証すべき点 |
|---|---|---|
| 既存3D Tiles→b3dm→GLB→Blender | 最初の互換経路。既存Pythonを再利用 | tile階層transform、RTC、glTF軸変換、batch地物対応、texture、重複LOD |
| CityGML→PLATEAU GIS Converter→glTF→Blender | 中期の正規化経路候補 | 属性の保持、地物ID、穴・面、CRS、texture、CLIの版固定 |
| Unity SDKで取込・export | Unity用途や比較検証時の代替 | 中間工程と環境依存が増える。初期の必須依存にはしない |

[PLATEAU GIS Converter公式repo](https://github.com/Project-PLATEAU/PLATEAU-GIS-Converter)はCityGMLのglTF/OBJ等への変換とGUI/CLIを説明しています。[Unity SDK](https://github.com/Project-PLATEAU/PLATEAU-SDK-for-Unity)にもCityGML取込・3D形式exportがあります。今回これらをインストール・実行していないため、既存Blenderとの互換性は試験対象です。

初回取込試験は東京タワー近傍の一つのmesh/resourceに限定。権利確認→対象範囲・LOD選択→download/hash→変換→地物対応sidecar→単位・方向・既知点検査→texture検査→Blender open/renderまで通します。遠景は低LOD、重要landmarkは置換し、PLATEAU LODと本プロジェクトの視覚品質ランクは別に管理します。

## 出典・権利の扱い

| 入力 | 現状 / 必要な対応 |
|---|---|
| PLATEAU | 個別dataset/resourceのlicense、著作権者、年度、表示文、第三者権利注記を保存。加工内容も表示 |
| OSM | 既存build・SceneにODbL出典あり。道路・配置の派生関係を追跡し、配布databaseとrendered workを区別 |
| 国土地理院写真 | 旧取得処理あり。現行Scene方針は地面への写真表示なし。参考取得履歴も台帳へ |
| 公式施設・設計者写真 | 寸法等の記載事実と写真ファイルの再配布を分ける。閲覧可能だけではtexture利用可としない |
| 投稿者写真 | 撮影者・撮影日・利用範囲・license申告を求め、権利が明確なものを採用 |
| BGM | 提供元の許諾が未確認。都市baselineとPR比較は音楽を必要としない |
| AI生成asset | 生成サービス条件、入力資料の許諾、生成日・実行IDを記録。生成したことだけを配布権の証拠にしない |

[PLATEAUサイトポリシー](https://www.mlit.go.jp/plateau/site-policy/)は現在PDL1.0とCC BY互換性を説明していますが、個別データと権利表記を優先します。[OSMの公式著作権説明](https://www.openstreetmap.org/copyright)はODbLとattributionを示しています。フォルダ分割だけで派生databaseの条件が消えるわけではなく、再配布形態ごとに確認します。

Google Street ViewのURLは報告の手がかりとして受け付けられますが、自動取込・画像抽出・trace・texture化の入力にはしない運用を提案します。[Google公式Geo Guidelines](https://about.google/brand-resource-center/products-and-services/geo-guidelines/)にはStreet Viewからのデータ生成・解析抽出・サービス外downloadの制限があります。Agentは独立した許諾済み資料で裏付けます。

公開前に `NOTICE.md` とasset別license manifestを生成し、code MIT、独自文書/asset CC BY 4.0案をmaintainerが確定します。既存blend全体を一括MITにしません。不明素材はlegacyとして保管し、公開buildでは除外または置換。正式LICENSEの未配置は意図的な公開前ゲートです。

## ストレージ方針

| データ | 保存先 | 方針 |
|---|---|---|
| Python、JSON、schema、出典台帳 | 通常Git | diffとレビューの正本 |
| 手編集landmark、固定baseline | LFSまたはhash指定外部object storage | 更新頻度と個別容量で選ぶ。全sceneをPRごとに履歴追加しない |
| PLATEAU原本・変換cache | 原配信＋許諾されたmirror | 必要tileだけ取得。URL、bytes、hash、licenseをGitに保持 |
| 一時blend・連番 | 作業cache | Git対象外、失敗再開用に保持期間を設定 |
| PRの比較画像・検証JSON | CI artifacts | 例：90日保持。merge採用分は長期保存先へ昇格 |
| 完成動画・大型release | 外部配布またはRelease | 同じ動画を通常GitとLFSへ重複保管しない |

GitHubは通常Gitで100 MiB超のファイルをblockします。[公式制限](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。Git LFSの1ファイル上限はFree/Pro 2 GB、Team 4 GB、Enterprise Cloud 5 GBです。[LFS公式](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage)。現在のsceneは容量上この範囲内ですが、契約枠と利用料金は別です。

LFSは変更版のファイル全体が保存量に計上され、downloadは帯域消費になります。[LFS課金](https://docs.github.com/en/billing/concepts/product-billing/git-lfs)。約0.978 GBのsceneを20版保存すると、そのsceneだけで概算19.6 GB。base/headを10回新規downloadすれば概算19.6 GBの転送です。料金・無料枠は実際の契約確認後に予算化します。

PoCでは静止画4カメラ×base/headを標準とし、52秒・1248枚は毎PRの必須条件から外します。容量見積はdownload圧縮量、展開後、変換中間、blend、texture、before/after連番を別集計。作業用空き容量はまず固定sceneを含む小規模試験で実測し、東京全域の必要量を現在の圧縮blendから推定しません。

既存 `.gitignore` は新docs等も除外するallowlistなので移行時に明示修正が必要です。LFS登録は最初の追加前に行い、clone後の取得試験を必須化。cache欠落時は固定hashを再取得し、取得不可なら明示失敗します。別年度へ黙って置換しません。
