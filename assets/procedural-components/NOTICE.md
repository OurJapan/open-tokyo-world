# 制作元と変更内容

作者表示：ark4ez / OurJapan。

対象は旧東京タワー周辺モデルから切り出した、イチョウ3種類・ケヤキ3種類の幹と葉、低木4種類、数式材質31種です。固定した制作コード・保存入力との照合後、街の配置を除いて新しい展示用配置を作りました。形状の詳細な指定と材質のhashは `provenance.json` にあります。

- 元コードの固定版：`ark4ez/tokyo-tower-blender`、commit `defac576e076f40bf3bc4fddcdcefe30f9a009f7`。元コード本文は同梱していません。
- 比較・切り出しの記録：Open Tokyo Worldの `docs/city-component-verification.md` と `sources/city-pr12-component-verification.json`。
- 許諾時の候補：SHA-256 `78ea637f9b154274c62fd20160995b649139c191a09056f8696ec5baee10595a`。同梱版はこの候補の許諾表示を更新したコピーです。
- 変更：形状・材質・展示配置を保持し、scene/objectの許諾表示をCC BY 4.0へ更新。描画の保存先を同じフォルダーの `preview.png` に設定しました。元の街・候補ファイルは変更しません。

このパッケージに地図、建物、元の都市座標、外部画像、旧スクリプトは含まれません。樹木・低木は手続き生成の表現であり、特定の現地樹木や植生調査を正確に再現するものではありません。塗装・灯具・設備用の材質も含みますが、それらの街の集約形状は含みません。

プロジェクト：[Open Tokyo World](https://github.com/OurJapan/open-tokyo-world)。利用条件は同梱の `ASSET-LICENSE.md` を参照してください。
