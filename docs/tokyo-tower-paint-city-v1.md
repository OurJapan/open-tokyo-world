# 東京タワー塗装帯：現行cityへの限定統合

この文書はPR #47＋#49への初回統合時点の記録です。PR #51の樹木と接合修正を含む最新検証・公開状況は[都市統合記録](tokyo-tower-city-repairs-v1.md)を参照してください。

元の独立モデル制作commit `568a9e76106b2354c94616e6c62d6c8b9ac3ac38` を保持し、その子branchで統合パッチを作成しました。共有city・通常登録・他のworktreeへは書き込んでいません。公開push・PR・mergeは未実施です。

## 既存4視点の再確認

親からの依頼を受け、独立モデルの既存8枚を画像表示機能で再確認しました。この再確認のための描画し直しはしていません。

| 視点 | 具体的に確認した変更・状態 |
|---|---|
| 全景 | 上部のオレンジ／白の帯幅が揃う。先端、展望台、4脚、アーチの輪郭に崩れや位置ずれは見当たらない。既存補助植栽も同じ配置。全景では小さな変更で、細部の判定は近景による。 |
| 230.7m付近 | Beforeでは白い水平リング付近へオレンジの斜材先端が三角形状に突き出す。Afterではその先端と柱の上端が白くなり、複数の鉄骨を横断する同じ標高で帯が切り替わる。部材欠落、穴、二重梁は見当たらない。カメラが斜めなので画面上の切替線が一律の水平画素列になるわけではない。 |
| 205.1m付近 | Beforeではオレンジの水平材直下に白い斜材・柱が残る。Afterではその上部がオレンジへ揃う。斜材の向き・接続位置・下側のリングに変形は見当たらない。 |
| 下部 | 展望台下、脚、アーチ、階段、周辺補助植栽に見える変化は認めない。データは保持されているが、画像は50画素・最大4/255の微小差があり、完全一致とは扱わない。差の個別原因は未特定。 |

7等分という考え方は[東京タワー公式の塗装説明](https://www.tokyotower.co.jp/plan/towerpedia/)によります。**154mの下端と正確な境界標高は、既存モデルの推定値**を引き継いでいます。実測・設計図から新たに確定した高さではありません。

## 現行モデルとの対応と統合方法

検査時のremote mainは `05026ec9de08b25e15e8e77c2ad2e2a43a1b5f6d`（PR #49取り込み済み）。登録用manifestはPR #46の `9c142f54…` のままでした。両者を混同しないため、登録cityも読み取り照合したうえで、統合入力には採用済みPR #47＋#49の保存モデル `09977e34…` を使いました。[固定入力](../assets/tokyo-tower/paint-bands-city-v1.json)。並行中の樹木候補は混ぜていません。

どちらのcityでも `Tokyo Tower structure / orange`・`white` の編集表示における評価後メッシュが、固定ID付き独立入力の005・006と完全一致しました。位置・回転は0、尺度は1、world行列は単位行列。形状・UV・属性・コーナー法線のハッシュと材質ノードも一致しました。元のcityには `otw_part_id` がないため、入力ファイルhash、provenanceの固定alias、既存feature ID、形状の一致で同定しています。

ただしcityの `Small manufactured edge radius` ベベルは **show_viewport=true / show_render=false** です。独立モデルは編集表示で評価したベベルが焼き込まれており、そのまま置換すると従来レンダーの形状が変わります。さらに元cityの面を分割する試行では、ベベルの再評価で保存後の編集表示幅に最大7.332mmの変化が出ました。重なり制限の影響と推定しています。検査がこれを検出したため、その候補（03）は不採用です。

[統合スクリプト](../scripts/tokyo_tower_paint_city.py)の最終方式は、元メッシュ・ベベルを変更せず、対象2部品専用の材質で同じ高さ境界を表現するものです。Object座標のZを6境界と比較し、元のオレンジ／白のBase ColorとRoughnessを切り替えます。下部の白い階段は元の白を保持。元2材質のノードがこの2入力以外は同一であることを確認しており、金属度・微細な凹凸などは保持します。独立候補の面分割版は元commitのまま変更していません。

変更は2オブジェクトの材質スロットと対応確認済みの `otw_part_id`・`source_object`、専用の新材質2個です。元材質は未使用の第2スロットに保持し、保存時にも失われないようにします。他部品へのID付与はしていません。

| 対象 | 未評価の頂点（不変） | 未評価の面（不変） |
|---|---:|---:|
| 005 / orange | 75,064 | 55,222 |
| 006 / white | 18,432 | 13,724 |

対象を含む全メッシュの座標・接続・UV・属性・法線を保持し、編集表示の評価後メッシュも同じハッシュになることを検査します。描画・Material Preview用のBlender手続き材質です。Solid表示の材質色やglTF等へ焼き出した結果を同等とは扱わず、汎用形式への変換は未検証です。

## 保存後検証と成果

別プロセスで保存後検証に成功しました。3,309オブジェクト中、対象外3,307オブジェクトを保持。対象を含む全未評価メッシュ、対象2部品の評価後メッシュ、383枚のpacked画像、既存551材質、17 collections、23 actions、World、カメラ・照明を照合しています。変更は専用2材質とその割当・識別属性に限定されました。

検証の詳細と最終状態は [機械可読記録](tokyo-tower-paint-city-v1-verification.json) に記録します。`data/local/tower-city-04/` がレビュー対象で、`before.blend` は固定city入力の完全コピー、`after.blend` は2部品を改修した街全体の候補です。候補SHA-256は `73031afe18232ae8e101a683816a39374f6cf7c7cf669bc60cb0325f763fd689`。01・02は検査器の開発中に停止、03は上記のベベル変形検出により不採用です。

スナップショットはmesh座標・接続・UV・属性・法線、配置・表示・custom properties、modifier・constraint、材質ノード、packed画像hash、World、カメラ・照明、collection構成、actionのkeyframe等を照合します。一般的な全Blender機能や任意driver変数を網羅する検証器ではありません。原本hashと対象外objectの一致を併せて確認します。

統合レンダーは街全体の候補を開き、全景と205m付近の2視点を同一条件で比較しました。全景は足元を含める55mmへ画角を調整し、その視点だけ描画を更新。80mmの近景は再利用しています。CPU 2 threads、Cycles、640×640、8 samples、seed 0、denoising ON。4枚を目視確認し、近景の斜材・柱の帯が同じ高さで揃い、全景の脚部・展望台・先端と周辺街区に形状崩れや位置ずれが見当たらないことを確認しました。低コストの外観検査であり、GPU描画や全都市の全視点を保証するものではありません。PNGと比較HTMLはローカル限定で、街全体の再配布許諾を追加しません。

portable testsは242件（235成功、既存任意依存の7件スキップ）。Blenderの追加試験ではスナップショットがcustom propertiesを作成しないことと、実際のシェーダー描画16サンプルが元パレットに一致することを確認しました。サンプルを全てworld Z=0へ移し、Object座標の高さで正しく塗り分けることも検査しています。既存のVIEWER画像カラー設定enum警告とextension cache書込み警告がログにありますが、工程はexit 0で完了し、素材の設定や通常登録を修復・変更する操作はしていません。

## 再実行

Blender 4.5.1と固定入力2ファイルが必要です。以下は専用worktree内で実行し、出力先は未作成のディレクトリにします。原本や登録は更新しません。

```powershell
$blenderPath = 'C:/Program Files/Blender Foundation/Blender 4.5/blender.exe'
$cityInput = 'RECEIVED_PR47_PR49_CITY.blend'
$towerReference = 'RECEIVED_FIXED_ID_TOWER.blend'
$cityOutput = 'data/local/tower-city-new'
foreach ($phase in @('build','validate','render-before','render-after','compare')) {
  & $blenderPath --background --factory-startup --threads 2 --disable-autoexec --python-exit-code 1 --python scripts/tokyo_tower_paint_city.py -- --phase $phase --city $cityInput --reference $towerReference --output $cityOutput
  if ($LASTEXITCODE -ne 0) { throw "City paint phase failed: $phase" }
}
python -m unittest discover -s tests
& $blenderPath --background --factory-startup --threads 2 --disable-autoexec --python-exit-code 1 --python tests/blender_tower_paint_city_smoke.py -- $cityInput
```

次は親レビューで、推定境界の扱いとcity既存ベベルの保持を確認してから公開を判断します。樹木候補との合成は、その候補の入力・出力hashと変更範囲が確定した後の別工程です。
