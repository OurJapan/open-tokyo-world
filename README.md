# Open Tokyo World

> AI agents continuously build Tokyo.

人間が要望・資料・現実との差分を提示し、AIが調査・3D実装・検証を行い、人間がレビューする、実在都市の継続開発プロジェクトです。最初の対象は東京タワー周辺。高精細な領域を芝公園、麻布台、六本木へ順に広げます。

**状態：M1のレビュー基盤を実装中。** 設計資料、日本語の報告フォーム、ローカルで動かすBlender検証・比較CLIと軽量CIを含みます。Issueからの自動修正・自動PR作成、都市の完全再構築は未実装です。既存モデルや動画は同梱していません。

[比較CLIの実行方法と制約](docs/review-harness.md)

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
- [レンダリング・品質・Validation](docs/quality-guidelines.md)
- [移行ロードマップと最初の受入条件](docs/roadmap.md)
- [類似プロジェクト調査・再利用候補](docs/related-projects.md)
- [参加体験・貢献の記録・コミュニティ連携](docs/community.md)
- [Blender検証・Before/Afterの実行方法](docs/review-harness.md)
- [Agent作業指示の初版](agents/instructions/AGENT.md)

## ライセンスの状態

目標は、独自コードMIT、独自文書・権利確認済み独自アセットCC BY 4.0、第三者データは取得元の条件を保持する構成です。**これは採用提案であり、既存データへのライセンス付与ではありません。** 埋め込み画像、OSM派生データ、BGM等の監査後に正式なLICENSEと出典一覧を配置します。現時点で資産全体を自由に再配布できるOSSとして扱わないでください。
