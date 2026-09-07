# 品質・Render・Validation

## 判定の考え方

技術的に開けることと現実に正しいことを分けます。Agentによる視覚評価は候補指摘として利用し、人間のレビューで根拠との一致を判断します。品質はgeometry、placement、material、temporal freshness、provenanceを別々に記録します。

Quality Areaは `base / enhanced / reviewed` を場所ごとに保持し、PLATEAUのLOD値と混同しません。観測日の違う建物を含む都市を「ある一日時点の完全再現」と表示しません。

## 検証段階

| 検査 | 内容 | 初期の失敗条件 |
|---|---|---|
| 静的metadata | schema、ID一意性、依存先、source、license、hash、path逸脱 | 必須項目欠落・重複ID・未解決依存 |
| 再open | 保存candidateを別Blender processで開く | 非zero exit、timeout、対象Scene欠落 |
| asset | image decode、packed/相対参照、library/font/volume/cache、material slots | 必須asset欠落・破損 |
| geometry | 有限座標、妥当なindex、ゼロ面積・異常bounds・極端なscale、必要箇所の法線 | 非有限・空の必須mesh・修正部位の破損 |
| 地理 | source→local変換、既知点、height、tile継ぎ目、置換対象 | 変換不明・位置ずれ・重複置換 |
| camera | evaluated pose、lens、sensor、clip、対象bbox、markerによる切替 | 非有限・clip逆転・指定cameraなし・対象が映らない |
| render | fresh PNG読込、期待寸法、全black/透明の異常、対象coverage | 出力無し・decode失敗・不正寸法 |
| 非対象回帰 | ID別geometry/material/transform指紋、context画像 | 許可外の変更が発生 |
| performance | 同hardware/presetのtime・peak RAM/VRAM・polygon・asset量 | 資源上限超過、重大悪化 |

non-manifoldを全都市一律の失敗条件にはしません。地面や開いたfacadeなど意図した非閉曲面をpartごとに許可します。密閉glass等は別条件にします。検証時にmesh.validate等で黙って修復して保存しないよう、検査と修復jobを分けます。

既存baselineの問題はID・範囲・理由付きwaiverとして登録し、新規問題の増加を止めます。全体の技術負債を解消するまで最初の変更を永久に止めない一方、変更部位の失敗をlegacy扱いで逃がしません。

## 初期レビューカメラ

| ID案 | 既存資産からの候補 | 用途 |
|---|---|---|
| tower-exterior | Review 02 • Tokyo Tower | 塔全体・シルエット |
| deck-to-mori | 展望室内で森JPタワーを向く固定poseを抽出 | 最初のIssueの利用者視点 |
| mori-facade | Review 05 • Mori JP Tower / Review 06 • Mori glass detail | facadeの修正箇所 |
| context | Review 01 • Both landmarks / Review • low aerial | 周辺・対象外回帰 |

名前は実在を確認していますが、最終pose・遮蔽・画角の受入はM1で行います。film用の24–34秒の12mm飛行画角だけで外観精度を判定しません。review-cameras.jsonにmatrix、lens_mm、sensor、clip、frame、target_idを固定し、markerや既存animationが上書きしない独立cameraを使います。

## 実行環境と予算案

最初の参照toolchainは既存と同じBlender 4.5.1 LTS。Blender patch version、Python依存、converter、GPU driver、OSを記録し、更新は別PRで比較します。

Smokeは小さな対象AreaでCPUでも動く低解像度。通常レビューはCycles 1280×720・32 samples・seed固定・motion blur offを初期案とし、ガラスが判断できない場合は64 samples以上に上げてpresetを固定します。Filmの48 samplesとレビューpresetは別です。値は性能実測前の提案で、既存巨大sceneのCPU動作時間を保証しません。

performanceは同一workerでwarm-up後の代表renderを測り、初回は3回の中央値をbaselineへ。時間+20%またはpolygon/texture bytes+10%で警告、時間/peak memory+50%またはworker資源上限超過で停止、という暫定値を提案します。正当なdetail追加にはMaintainerが理由と新予算を記録します。機種が違う測定値同士を比較しません。

静的CIは全PR、対象Areaのopen/geometry/renderは対象変更時、隣接Areaは依存関係変更時、長尺filmはcamera変更・release時に実施します。カメラ変更時には1248frameのevaluated transform/lens回帰と、カット境界前後の短尺renderを追加。位置固定の見回し等、意図した停止と不具合の停止を区別します。

## 判定結果と将来の視覚比較

検証JSONはcheck ID、対象ID、pass/warn/fail、expected/actual、環境、実行headを記録。非zero exitとjob timeoutをrunner側でも確認し、report無しを成功にしません。PRへの表示は一枚の比較sheetと失敗・警告一覧を先頭にします。

Reference Image比較は撮影位置、焦点距離、撮影日、季節、遮蔽物の違いを扱える段階で導入します。silhouette、landmark位置、window分割、色など対象を限定し、単純な画像類似度を現実の正しさの総合スコアにしません。reference画像を再配布できない場合は許諾された場所での比較か、根拠テキストとリンクによる人間レビューにします。
