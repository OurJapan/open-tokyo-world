# Web Spatial Viewer P0 実装記録

2026-09-07、`feat/web-spatial-poc`。既存`OurJapan/open-tokyo-world`の作業branchに実装。新規Git repositoryは作成していない。

## 動く範囲

[独立Web package](../web/spatial-viewer/README.md)にThree.js/Viteでcamera重畳、GPS/方位、3D Viewer、撮影、観測分類、ローカルZIP保存を実装。写真や位置の外部送信はない。下書きはメモリだけに保存し、利用者が明示downloadできる。

[OTW adapter](../adapters/open-tokyo-world/build_web_fixture.py)は既存の原点と地物ID registryを読み、配布manifestと独自GLB fixtureを生成する。Web runtimeが読むのはこの静的contractだけ。ID registryとfixtureの実在地物対応は別で、fixtureに現実の地物IDを割り当てない。

「どこでも試す」は端末前方25mへの仮配置。「東京タワー周辺」は既存原点を使う概略配置で、300m圏内・位置誤差50m以下・新しい北基準方位が揃う場合だけ表示。仮の地面からのカメラ高さ1.6m/画角60°の仮定を診断に残す。生観測の`camera_pose=null`と描画用`display_pose`を分離する。

## 実行した検証

| 検証 | 結果 |
|---|---|
| Web module tests (`pnpm test`) | 18件成功：ENU方向、camera四方、landscape、値欠損/古い時刻、geo gate、video contain、snapshot不変、ZIP/hash、GLB ID非割当、permission race/拒否、track/watch解除 |
| production build (`pnpm build`) | 成功。JS約646KB / gzip約167KB、CSS約7KB、fixture GLB 3,036 bytes |
| 既存Python unittest | 42件成功。既存3D変更処理の回帰検査 |
| localhost HTTP | rootとmanifestの200応答を確認 |
| package境界 | Web packageだけを新しい一時folderへコピーし、固定lockfile・既存cacheでoffline install。18件のtestとbuild成功。親repoのscripts/areas/manifestsはコピーせず、配布contractだけ使用 |

初回の境界試験ではWindowsの長いパスとcache実行ユーザーの違いでinstall/copyが失敗したため、短い一時パス・依存取得時と同じcacheでやり直した。Webコード変更による回避ではない。

unit testはAPIをmockしており、実際のiPhone sensor値の精度を示さない。今回ブラウザUIの自動操作、iPhone camera/ZIP download実測、現地登録、10分の発熱試験は未実施。

## 配信とレビュー

[Web CI](../.github/workflows/web-spatial.yml)を設置し、fixture再生成差分、tests、build、静的artifactを検証する。[Pages workflow](../.github/workflows/web-spatial-pages.yml)はmainに限る手動配信。最初はOAuth認証のworkflow scope不足で設置できなかったが、2026-09-07に本人承認で権限追加を確認し、既存PRに設置した。人間review/mergeと既存Pagesサイトの競合確認後に公開する。権限追加だけではmerge・サイト公開は行わない。

Sitesのhosting手順は別のソースrepositoryを要求するため、今回の「新規repositoryを作らない」方針に合わせて採用しなかった。HTTP localhostのpreviewはPC用で、iPhoneのcamera検証には公開/アクセス制限付きのHTTPS配置が必要。公開URLを作成済みとは扱わない。

## 次の実装境界

1. iPhone実測でpermission・端末回転・ZIP保存・復帰を確認。
2. 対象assetの権利/座標が確定したらfixture専用manifestを実地物のversioned manifestへ拡張する。
3. 投稿保存APIを別serviceとして追加し、local draftをserverで検査して受付IDを発行する。写真の利用同意・削除・冪等性を実装するまでは送信ボタンを追加しない。
4. Localizerはさらに別interface。VPSがなくてもP0の利用を阻害しない。
