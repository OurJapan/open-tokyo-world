# 入力と加工の出典

出典：[3D都市モデル（Project PLATEAU）港区（2025年度）](https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025)を解析・加工して作成（OurJapan）。[個別リソース](https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025/resource/08755b94-7b2e-4c9c-bf35-6c4d0768a463)は[PLATEAUサイトポリシー](https://www.mlit.go.jp/plateau/site-policy/)に従うと記載。確認日2026-09-07。第三者データにコードのMITライセンスを適用しません。

加工：b3dmのDraco復号、地物IDごとの分割、glTFからECEF・局所ENUへの変換、各地物の底面を0.32mへ移動する旧表示互換処理、WebPとUVのBlender材質への変換、カメラ・照明設定。標高属性との独立照合は未完了です。元座標の境界と地物別移動量はgeoreference.jsonに記録します。

広場6部品：ark4ez / OurJapan、CC BY 4.0。出力フォルダーのPLAZA-LICENSE.mdとplaza-provenance.json、またはリポジトリのstarter/plaza/ASSET-LICENSE.mdとprovenance.jsonを参照してください。配置と形状には推定が含まれます。

Blender 4.5.1同梱のDracoデコーダーを呼び出します。Blender・glTF importer・Draco・元テクスチャをコードとして再配布するものではありません。デコーダーAPIの参照元：Blender glTF importerのblender/imp/draco_compression_extension.py（The glTF-Blender-IO authors、Apache-2.0）。バイナリは同梱せず、実行したライブラリのハッシュを記録します。

この試験は公式タイル24地物と独自広場6部品のみです。従来の高精細な東京タワー・森JPタワー、OSM道路、音楽、写真資料は入力にしません。作成されたファイル全体の再配布は、各入力の条件・表示と公開対象を確認してから行ってください。
