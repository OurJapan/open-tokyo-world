# Web Spatial Viewer — P0 実装

既存`OurJapan/open-tokyo-world`内の独立Web package。camera + WebGL + GPS/方位 + 生写真/観測下書きの端末保存を実装した。ブラウザはこのpackageの配布contractだけを読み、Blender/Python/GitHubへ接続しない。

## 起動

Node.js 24、pnpm 11.19.0。

```sh
cd web/spatial-viewer
pnpm install --frozen-lockfile
pnpm test
pnpm dev
```

表示されたlocalhost URLをPCで開く。`pnpm build`で`dist/`に静的配布物、`pnpm preview`でbuild確認。baseは相対URLのためGitHub Pagesのrepo subpathでも動作する。browserのURLはディレクトリ末尾`/`で開く。

**iPhoneではHTTPSが必要。** PCのlocalhostはiPhoneから参照できず、LANのHTTPもカメラの実機試験には使えない。`dist/`を信頼できるHTTPS static hostに配信する。自己署名certificateを自動インストールしたり、セキュリティ無効化を求める構成にはしない。

既存repo向けに[手動Pages workflowの設置用テンプレート](deployment/web-spatial-pages.yml)と[Web CIテンプレート](deployment/web-spatial.yml)を用意した。現在のGitHub認証にworkflow更新権限がないため、`.github/workflows/`には未設置で自動実行されない。Maintainerがreview後、各ファイルを同名で`.github/workflows/`へ配置する。人間review/merge後、既存Pagesサイトとの競合を確認し、repository Settings → Pages → GitHub Actionsを選び、main上の`Publish web spatial viewer to Pages`を手動実行。公開されるのは検証コードと独自fixtureだけで、写真は含まれない。既存のPagesサイトがある場合は、このworkflowで置き換える前に配信先を調整する。今回公開実行は行っていない。

## 実装済みの操作

- 通常3D Viewer：ドラッグ/ピンチと視点リセット、opacity変更。
- 「カメラで試す」：背面camera、位置、方向の許可を要求。camera以外の拒否でも重畳テスト可。Motion加速度は利用しないため要求しない。
- 「どこでも試す」：開始時の前方25mに仮配置。方向イベントがなければ画面固定。metric trackingではない。
- 「東京タワー周辺」：既存原点35.65858 / 139.74543から水平ECEF/ENU換算。範囲300m以内、位置誤差50m以下、新しい北基準方向が揃う場合のみ概略表示。
- 50/100/300mの範囲選択：現在地からfixture原点までの距離で表示を選別。**全国周辺取得APIではなく1点のstatic manifest**。
- 写真撮影：videoの生画像を長辺2,048px以下のJPEGにし、同時点の位置/方位/表示版をsnapshot。3D overlayを含まない。
- 下書き：5分類、コメント、ZIP download。`observation.json`、`photo.jpg`、説明をまとめる。SHA-256で写真とmetadataを紐付ける。
- camera終了、background、pagehideでtrackとgeolocation watchを解除。復帰は明示操作。閉じた下書きはcamera停止後も再表示・保存可能。

写真は明示保存までメモリのみ。外部upload/analytics/CDN request、localStorage/IndexedDB保存、service workerは実装しない。ZIPがdownloadされたことをOSから確実に検出できないため、UIは「保存用ZIPを作成」と表示する。下書き削除は既にdownloadしたZIPを消さない。

## 既存資産との接続

[build_web_fixture.py](../../adapters/open-tokyo-world/build_web_fixture.py)が既存`manifests/legacy-baseline.json`の原点と`areas/tokyo-tower/features.json`の安定IDを読んで`public/data/manifest.json`を生成する。

```sh
python adapters/open-tokyo-world/build_web_fixture.py
```

生成される`device-test.glb`は独自の単純構造物で、東京タワー/森JPタワーのmesh・textureを含まない。実在地物IDをfixtureへ割り当てない。`known_features`は既存IDの参照情報であり、表示geometryとの対応ではない。rootのライセンス方針を維持し、この追加コードで既存素材への包括licenseを変更しない。

Webからは上記Pythonや親directoryをimportしない。package一式だけを別の一時directoryへコピーして`pnpm install --frozen-lockfile && pnpm test && pnpm build`できる。実際のrepo切り出しはしない。

## 観測contract

`schema_version=otw-observation-draft/0.1`は[設計上のserver v1](../../docs/reality-observation.md)と区別したローカル下書き。受付前なので`observation_id/received_at=null`、`review_status=local_draft`。実poseと地物は`camera_pose/feature_id=null`、仮の描画matrixは`display_pose`に分離する。

高さ1.6mと横画角60°は表示仮定であり、sensor計測値ではない。未知高度を0で保存しない。位置は10秒、方向は2秒を超える古い値や未来timestampを写真metadataへ付けない。既存originの`vertical_datum=unknown`を維持する。

今後のbackendは、この下書きを検査してserver IDと保存状態を付与する。現時点ではZIPの保存によってIssue/AI修正が起動することはない。

## 未達・実機で確認すること

実都市GLBの権利確認・測地登録、VPS、画像照合、連続6DoF、正確なocclusion、校正済みintrinsics、server受付は未実装。iPhoneの権限/映像/方向/ZIP保存、SNS内browser、横向き、10分の発熱とメモリは実機確認待ち。Desktopのmodule試験やbuildをSafari動作の証拠にしない。

最小の実機手順：HTTPS URL→「カメラで試す」→許可→左右上下へ向ける→写真→分類/コメント→ZIP保存→camera終了→ZIPに生写真とJSONが入ることを確認。続いて位置/方位拒否、画面lock/復帰、下書き削除を試す。現地geo modeは最後に確認する。
