# カメラと素材出典の追加調査（2026-09-07）

## 比較カメラ

従来4視点を保持し、`deck-to-mori` と `mori-full` を追加した。前者は原本のメインデッキ床高145.1mに対してカメラ高146.8m、後者は森JPタワーの基壇から頂部までを見る28mmの全景。地理的に測量された視点ではなく、既存モデルの座標に基づくレビュー候補である。

6視点×Before/Afterを960×540、16 samples、OptiXで再生成。原本のhashは一致し、対象物の変更はゼロ、別processでの再open・検証も成功した。これはカメラ改善のbaseline-captureであり、建物の現実差分を修正した実績ではない。

[実行結果JSON](review-six-views-run.json)に設定・入力hash・処理時間を保持する。再openを含む検証は各約36秒／39秒、6視点のrenderは各約38秒／32秒。単回測定である。

画像を確認し、全景では基壇と頂部がフレーム内に収まることを確認。展望台視点では森JPタワーが見えるが、窓枠が外観の一部に重なる。室内視点、外観詳細、遮蔽のない全景を併用する。人間による視点の受入は未完了。

## 画像の追跡

`scripts/audit_image_sources.py` は原本を保存せず、画像のpacked SHA-256、使用object、objectに記録されたsource/source_urlを出力する。材質node groupも探索する。実行例：

```sh
BLENDER --factory-startup --disable-autoexec --background LEGACY_BLEND --python-exit-code 1 --python scripts/audit_image_sources.py -- sources/image-inventory.json
```

出力先は新しいパスを指定する。結果は [画像一覧](../sources/image-inventory.json)。384 image datablockのうち382件に使用objectの出典URLがあり、残りは `Render Result` と `facade_atlas.png`。URLの存在は、画像bytesと取得元との一致や利用許諾の証明ではない。

`facade_atlas.png` は8 objectで使用される。旧プロジェクトの `work/sky_detail/atlas_finish.py` は、これを個々の実在建物の写真ではないAI生成の再利用用アトラスと記録している。生成元・参照入力・採用条件は未確認。

旧 `work/detail_upgrade/selected_tiles.json` は港区2025年、仕様5.0、LOD3 texture datasetを指し、`build_upgrade.py` がobjectに取得URLを設定していた。都市基盤には建物底面を既存道路面へ平坦化する加工もあるため、取得データそのままの標高とは扱わない。

## 利用条件と次の作業

[PLATEAUサイトポリシー](https://www.mlit.go.jp/plateau/site-policy/)は、権利表記のない対象コンテンツについてPDL1.0を基本とし、出典と加工の明記を求め、CC BY 4.0での利用も認めている。ただし今回の画像ごとの元ファイル照合は未実施。[港区2025年の個別カタログ](https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025)は今回直接取得できなかった。適用条件の最終確認と画像の再配布判断は未完了。

次は、取得済みtile内画像とpacked hashを照合し、アトラスの生成記録を確認する。公開する画像・モデルごとに出典と加工履歴を記載する。今回のGitHub追加には画像bytesやblendを含めない。
