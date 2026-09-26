# 樹木・低木の基本形状と数式材質

イチョウ3種類・ケヤキ3種類の幹と葉（12メッシュ）、低木4メッシュ、数式材質31種を、[CC BY 4.0](ASSET-LICENSE.md)で利用できるようにしました。2026-09-27のアカウント保有者の同意と正確な対象は [provenance.json](provenance.json)、作者表示と制作元は [NOTICE.md](NOTICE.md) に記録しています。

旧都市の座標・地図・建物・集約形状・画像・旧制作コードは含みません。部品は特定の現地樹木の測量モデルではありません。

![イチョウ3種類・ケヤキ3種類と低木4種類](preview.png)

## 配布物の状態

**[v0.1.0 プレリリース](https://github.com/OurJapan/open-tokyo-world/releases/tag/procedural-components-v0.1.0)を公開しました。** [モデル入りZIP（約10.4MB）](https://github.com/OurJapan/open-tokyo-world/releases/download/procedural-components-v0.1.0/procedural-components-v0.1.0.zip)を新しいフォルダーへ展開し、Blender 4.5.1 LTSで `kit.blend` を開いてください。追加アドオンや旧都市ファイルは不要です。[同梱の使い方](PACKAGE-README.md)

[配布物と梱包の記録](package-v0.1.0.json)、[版情報](release-v0.1.0.json)、[公開取得の検証](public-download-verification.json)にサイズ・SHA-256・内容・採用済みソースcommitを固定しています。ReleaseにはZIP、`release.json`、`SHA256SUMS.txt` の3ファイルがあります。GitHubが自動生成するSource code ZIPとは別です。

共通CLIからは `.\otw.ps1 district setup --common procedural-components` で取得・展開・Blender読み込み確認まで実行できます。森JP周辺も必要な場合は `--district mori` を加えてください。[地区別の詳しい手順](../../docs/district-distribution.md)

## 確認した内容

元候補から許諾表示と描画出力先だけを更新し、形状・smooth・変換・材質と専用カメラ・照明の設定を比較しました。別プロセスで再読み込み・描画し、ZIPのCRC・全ファイルhashを確認後、新しいフォルダーへの展開物も再読み込み・描画しました。16メッシュ・31材質は一致し、画像・library参照・埋め込みTextは0件、プレビューの全画素は元候補と同じでした。元候補は変更していません。

公開した3ファイルをGitHubの認証情報なしで新規取得し、手元とバイト単位で一致することを確認しました。取得したZIPからの再読み込み・描画でも16部品・31材質とプレビュー全画素が一致しています。同じWindows PCでの検査です。別PC・他OS、全都市モデルの配布は別の作業です。

## メンテナー向けの梱包

許諾対象の固定候補とプレビューを用意して実行します。これは配布用ZIPの生成手順です。受け取った方はBlenderで開くだけで利用できます。

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe' scripts/package_procedural_components.py build --input data/local/candidates/procedural-components-20260927/kit.blend --preview data/local/candidates/procedural-components-20260927/preview.png --blender 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --output data/local/packages/procedural-components-new
```

新しい出力先を指定してください。候補のbytes/hashと許諾範囲を検査し、ZIPにはモデル・プレビュー・README・ライセンス・NOTICE・許諾台帳・検証結果・ファイル一覧の8ファイルだけを同梱します。旧blend、旧コード、ログ、未知のファイルは梱包しません。出力先の `SHA256SUMS.txt` はZIPの照合用です。自動アップロード・マージは行いません。
