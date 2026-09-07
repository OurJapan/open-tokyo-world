# Open Tokyo World

> AI agents continuously build Tokyo.

人間が要望・資料・現実との差分を提示し、AIが調査・3D実装・検証を行い、人間がレビューする、実在都市の継続開発プロジェクトです。最初の対象は東京タワー周辺。高精細な領域を芝公園、麻布台、六本木へ順に広げます。

**状態：最初の現実差分修正について、人間の画像レビューとmainへの取り込みが完了しました。** 森JPタワーの頂部・外装・低層部・入口を修正し、レビューで見つかった屋根と壁の欠落も再修正しました。設計資料、日本語の報告フォーム、Blender検証・比較CLIと軽量CIを含みます。Issueからの自動修正・自動PR作成、都市の完全再構築は未実装です。既存モデルや動画は同梱していません。

[採用した形状・検証結果・取り込み手順](docs/mori-review-acceptance.md) / [現在の進捗と次の作業](docs/roadmap.md)

[植栽・手すりの制作記録](docs/mori-terrace-v1.md) / [比較CLIの実行方法と制約](docs/review-harness.md)

## 自分のPCで試す

[森JPタワーの独立生成・置換試験](starter/mori/README.md)：旧都市ファイルなしで公式PLATEAUから詳細外装・低層部を生成し、4視点のBefore/Afterを作成します。技術試験であり、詳細モデル全体の配布許諾は未確定です。

[公式PLATEAU 1タイルの取込試験](starter/plateau/README.md)：固定した公式データを取得し、地物ID付きの建物24件と広場6部品を生成・保存・検証します。旧都市blendは不要。表示は旧座標に合わせた試験用です。

[Web Spatial Viewer 実機検証版](web/spatial-viewer/README.md)：カメラ＋3D表示、GPS/方位の概略配置、写真と観測下書きの端末保存を実装しました。既存repo内の独立Web packageです。表示は独自の検証モデルで、実都市モデルの地理整合、VPS、サーバー投稿、iPhone実測は未完了です。[実装・検証記録](docs/web-spatial-p0-implementation.md)

[固定版スターターのダウンロード・更新方法](starter/plaza/releases.md)：比較画像・検証・ソースをまとめた v0.1.0 プレビューを配布しています。画像を見るだけならBlenderは不要です。

[初めての参加ガイド](starter/plaza/first-contribution.md)：画像を見る、AIと試す、結果を紹介するところまで順に案内します。

[6部品のスターター](starter/plaza/README.md)で、元の都市ファイルなしに生成・保存・検証・Before/After比較を実行できます。PythonとBlenderが必要です。独自部品はCC BY 4.0、対象の生成コードはMITで利用できます。

## 最初に実現すること

一件の現実との差分について、次の流れを最後まで通します。

`Issue → 地物特定 → 根拠調査 → Blender修正 → Validation → Before/After → PR → 人間のレビュー → Merge`

最初は単一AgentとMaintainerで運用します。建物数より、修正の再現性、根拠の追跡、人間が判断できる比較画像、第三者の参加しやすさを優先します。

## 起点となる資産

[既存東京タワープロジェクト](https://github.com/DoiTakayoshi/tokyo-tower-blender)には、東京タワーの外観・展望室・ガラス床、麻布台ヒルズ森JPタワー、PLATEAU由来の街並み、道路・植生、52秒の完成映像、Blender Pythonが存在します。

調査対象commitは `defac576e076f40bf3bc4fddcdcefe30f9a009f7`。完成シーンはBlender 4.5.1 LTSで正常に開きました。現状は完成シーンから再レンダリングする構成であり、全制作過程を新しいPCで再実行できる構成にはなっていません。

## 都市の構成

- 都市基盤：版を固定したPLATEAU等の地理データ。
- Landmark：基盤の同一地物を置換する詳細モデル。
- 道路・植生・設備：出典と推定箇所を記録した追加モデル。
- Material：根拠に基づく修正と演出設定を分離。
- Film：既存の完成映像と演出を保管する独立した構成。

地物のID、座標系、出典、観測時点、変更履歴をBlender外にも保持し、将来のglTF/USD出力へ引き継ぎます。都市モデルの精度は場所・属性ごとに表示します。測量精度やDigital Twinとしての適合性は現段階では保証しません。

## 参加する

Blenderの操作経験は不要です。Observerは違いを発見し、Reporterは場所と根拠を報告し、Reviewerは比較画像を確認します。3D Contributorは必要な箇所を直接編集できます。実装と検証はAI Agentが担当します。

[参加方法](CONTRIBUTING.md) / [報告テンプレート](issues/templates/reality-difference.md)

## 設計資料

- [既存資産の調査と再利用マップ](docs/current-state-audit.md)
- [Architecture・座標・metadata](docs/architecture.md)
- [都市データ・PLATEAU・権利と容量](docs/data-sources.md)
- [IssueからPRまでのAgent Workflow](docs/ai-workflow.md)
- [運営の受付・AIへの引き継ぎ・判断の残し方](docs/maintainer-workflow.md)
- [レンダリング・品質・Validation](docs/quality-guidelines.md)
- [移行ロードマップと最初の受入条件](docs/roadmap.md)
- [類似プロジェクト調査・再利用候補](docs/related-projects.md)
- [参加体験・貢献の記録・コミュニティ連携](docs/community.md)
- [Blender検証・Before/Afterの実行方法](docs/review-harness.md)
- [Agent作業指示の初版](agents/instructions/AGENT.md)

## ライセンスの状態

**対象の独自生成コード・スターター用コード・梱包テストにMIT、6部品のスターターにCC BY 4.0を適用しました。リポジトリ全体への適用ではありません。** 対象は [LICENSE.md](LICENSE.md)、コード許諾文は [MIT-LICENSE.txt](MIT-LICENSE.txt)、モデルの条件は [ASSET-LICENSE.md](starter/plaza/ASSET-LICENSE.md)、出典は [NOTICE.md](NOTICE.md) と [provenance.json](starter/plaza/provenance.json) を参照してください。

元の都市blend、その他の生成モデル、PLATEAU・OSMデータ、参考写真・Texture・音楽、その他のコード・文書へ一括したライセンスを付与するものではありません。第三者の条件は保持します。
