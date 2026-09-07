# 移行ロードマップ

日程ではなく受入条件で段階を区切ります。M0の設計・一次棚卸しを公開し、M1のローカル検証・比較CLIを実装しています。日本語Issue Formも導入済みです。M1の配布権確認とカメラ承認、M2の現実差分修正・人間レビューは未完です。実行方法は [review-harness.md](review-harness.md) を参照してください。

| 段階 | 作業 | 出口条件 |
|---|---|---|
| M0 調査・設計 | 本資料、既存asset/code調査、read-only open、権利リスク特定 | 起点commit/hash、再利用マップ、未確認点が明示される。今回作成 |
| M1 固定baseline | 旧資産保全、license台帳、地物ID、4 review cameras、render/validation分離 | コピーからfresh render成功、camera固定、必要assetの配布条件確認、性能baseline取得 |
| M2 最初のE2E | 1 Issueを単一Agentでresearch→変更→検証→PR→review | 新しい作業環境で同じ入力から再現、人間がmerge判断可能 |
| M3 組立の再現性 | 旧コード抽出、parameter化、source lock、baselineの分割 | 対象Areaを取得済みソースから再組立、重複地物なし、旧filmが保全される |
| M4 参加とCI | Issue Forms、required checks、隔離worker、PR publish、guide | 別Contributorが写真/Issueだけで参加でき、別担当が修正を再現 |
| M5 Area拡張 | 芝公園→麻布台→六本木、tile/地物依存、Quality map | 隣接境界が一致し、増分buildで既存Areaが退行しない |
| M6 多用途 | glTF export→viewer検証、LOD/collision、必要ならUSD | 指定対象アプリで読み込め、ID/出典/座標情報が追跡可能 |

M2はlegacy baseline依存でも合格とし、ソースからの完全再生成はM3の条件に分けます。これにより既存制作資産を保ちつつ、最短で共同開発の流れを検証できます。

## M1の具体的な作業順

1. legacy-baseline.jsonに既存commit、blend hash、ファイルサイズ、toolchainを登録。原本と完成動画は保持し、歴史を書き換えない。
2. 埋め込み画像のsource対応・OSM派生・BGMを監査。未解決素材は公開buildから外す。既存にlicenseが無い状態で一括OSS宣言しない。
3. Tokyo Tower / Mori JPのcollectionとobjectにstable IDを付け、旧名aliasを保存。基盤tile内の対応featureを確定。
4. review cameraを4つ保存しfresh render。sceneの古いpreview metadataを整理し、実測・推定・演出を分類。
5. scripts/render.pyを引数化し、検証はread-onlyの別processへ。少量fixtureと対象Areaで検証契約を確認。
6. 管理対象pathsを `.gitignore` へ追加し、別ディレクトリへのclone・LFS/外部asset取得・hash照合を試験。

## 最初のIssue案

「東京タワー展望室から見た麻布台ヒルズ森JPタワー北寄りの外観について、投稿資料との違いを調査し、確認できた一箇所を修正する」。これは報告の具体化例で、現時点で特定の外観誤りを認定したものではありません。

対象は `otw:jp:tokyo:minato:azabudai-mori-jp` のfacadeまたはcrownの一部。まず資料の向きと撮影時点を照合し、受入条件を「対象面の窓割り」「輪郭」「色」から一つに限定します。現実に誤差が確認できなければ根拠付きでIssueを調査完了とし、無意味なgeometry変更でE2E成功を装いません。修正を伴うE2E用には別の検証可能な差分を選びます。

## M2のDefinition of Done

- GitHub Issueに対象地点、期待、許諾済み根拠、観測時点があり、地物IDに解決できる。
- research noteが部位別claimと推定を分け、参照URL・日付・licenseを記録している。
- 修正は対象IDに限定したコード/parameterまたは独立assetとして残る。
- pinned baselineから新しい作業directoryで再実行できる。既存中間blendの偶然の存在に依存しない。
- 保存後再open、asset/geometry/camera検証が成功。許可外の変更がない。
- 同条件のBefore/Afterが4視点あり、base/head/input/camera hashが記録される。
- 性能が予算内、または測定値と理由付きで予算変更が承認される。
- PRにIssue、出典、変更、比較画像、検証結果、既知の制約を掲載する。
- 人間が追加指示でき、その場合は新headで再検証する。人間の承認後にmergeする。
- 採用versionとrunを長期保存し、revertで元資産に戻せる。

## 最初の実装backlog

| 優先 | 作業単位 | 担当 |
|---|---|---|
| P0 | 入力資産・埋め込み画像のlicense/source manifest | Agentが調査、Maintainerが配布判断 |
| P0 | baseline lock・source/feature schema | Agent |
| P0 | read-only validatorと4 camera review harness | Agent、Reviewerが画像確認 |
| P0 | 森JPタワーのID対応と局所修正adapter | Agent |
| P1 | Issue Form / PR template / CONTRIBUTING導入 | Agent |
| P1 | 隔離render workerとartifact publisher | Agent、Maintainerが運用環境設定 |
| P2 | CityGML変換経路を1tileで評価 | Agent |
| P2 | Quality Area地図と増分build | Agent |

本格着手時に決める事項は公開ライセンス、配布対象asset、GPU worker/ストレージ予算、最初の報告根拠です。設計作成を止める条件にはせず、各段階の着手・公開条件として明示しました。
