# 東京タワーの許諾範囲と独立モデルへの切り出し

対象の独自モデル・材質77部品をCC BY 4.0、履歴コード9スナップショットと切り出し・検証コードをMITで提供する。対象外の第三者データ、旧都市全体にこの許諾を適用しない。[許諾](ASSET-LICENSE.md) / [出典](NOTICE.md) / [対象版・コードhash・同意](provenance.json)

`legacy-source/`は生成・修正履歴のテキスト保存。完全な独立生成runnerではない。東京タワーをソースだけから組み直すには、段階別依存の解消が必要。

## 部品を指定して改修するためのID

`provenance.json`の77部品に`tokyo-tower-part-001`〜`077`を固定しています。切り出した各meshの`otw_part_id`と`parts.json`の`part_id`に同じ値を保存し、別processで再openした際にID・旧部品名・feature ID・許諾の対応を照合します。表示名や配列順を変えてもIDを維持し、廃止したIDを再利用・採番し直さないでください。`source_object`は固定入力との対応名です。

形状の照合は表示名から部品IDに切り替えています。IDの欠落・重複・他の部品への付け替えは検証失敗になります。以前のIDなしの独立blendを検証する場合は、その版の旧exporterを使用してください。新しいexporterでは固定入力から新規出力へ切り出し直します。[実機での比較記録](../../docs/tokyo-tower-part-ids.md)

これは個別改修のための識別情報の追加です。形状の改修、共通registryへの都市組立接続、公開パッケージ、独立生成runnerは今後の工程です。

## 固定baselineを持つ担当者の切り出し

```sh
python assets/tokyo-tower/export.py --blender BLENDER --input LEGACY_BLEND --output runs/tower-isolated
```

PythonとBlender 4.5.1 LTSが必要。原本はprovenance.jsonのhashと一致するものに限る。新しい出力ディレクトリを指定し、原本は変更しない。評価済みメッシュ、手続き的材質、対象IDだけを独立sceneへ保存し、別processで再open・検証・3視点をrenderする。切り出し後のtower.blendは旧都市入力を参照せずに開ける。

このPRはコード・許諾・出典・検証記録のみ。巨大な旧blend、切り出したblend、公式写真はGitへ登録しない。画像・blendの外部配布先はまだ設定していない。既存baselineを持たない参加者のための取得経路・配布パッケージは次の作業になる。

旧5空オブジェクトは除外する。未確認の外部画像、shader script、材質animationが見つかれば停止する。切り出し後の画像・library・Text・soundがゼロであり、77部品が一致することを検証する。有限座標と保存mesh指紋を検査するが、全トポロジー・現実との精度・視点ごとの視認性の完全保証ではない。
