# Web Spatial Viewer 技術リスク

調査日：2026-09-07。優先度P0は実地/公開に進む前に確認、P1はPoC中に測定、P2は本格化前の確認。担当は今後の実装上の役割であり、別Agentやサービスを起動した意味ではない。

| 優先度 | リスク・具体的な失敗 | 根拠 | 最小検証・緩和 | 残余リスク / 判定者 |
|---|---|---|---|---|
| P0 | SafariにWebXRがあるつもりで実装し起動不能 | [Safari調査](iphone-web-ar-research.md) | camera+WebGLを主経路、通常設定実機の能力検出 | OS更新ごとに再確認 / Web担当 |
| P0 | 旧sceneの高さを標高と誤認し建物が浮く | [既存監査](current-state-audit.md)、[manifest](../manifests/legacy-baseline.json) | legacy/geodetic frame分離、地物別offset、独立検証点 | 未測量部分は概略のみ / 座標担当 |
| P0 | Y/Z軸、北方向、camera逆行列、glTF二重変換 | [座標契約](web-spatial-viewer-architecture.md) | 東北上3軸・既知camera・export往復fixture | 実世界登録誤差は別 / export担当 |
| P0 | pendingな都市texture/meshをWeb配信 | [data-sources.md](data-sources.md)、asset manifests | 1〜3 assetの個別許諾、source/出力hash、公開allowlist | 権利未解決は公開gate停止 / 運営 |
| P0 | 公開スターターを300m圏内と誤認 | [provenance](../starter/plaza/provenance.json) | 約511mの配置を確認。fixture利用と現地対象を分ける | 対象asset準備は別作業 / 運営 |
| P0 | 写真/正確な位置が公開Issueやログから漏れる | [Observation設計](reality-observation.md) | 非公開store、log除外、公開派生物review、未認証取得テスト | 写真自体で場所が分かる / API担当 |
| P1 | cameraのK/crop/レンズ差でposeが継続的にずれる | [Media Capture](https://www.w3.org/TR/mediacapture-streams/) | stream実寸と校正、レンズ切替で無効化、既知点投影 | 全iPhoneへ同じKを流用不可 / CV担当 |
| P1 | GPS都市峡谷・コンパス磁気擾乱 | [位置/方位調査](iphone-web-ar-research.md) | raw accuracyと時刻を残し、5地点で誤差測定。概略表示ラベル | 平滑化だけではbiasを除けない / Web担当 |
| P1 | 昔のserver poseで現在のcameraを補正 | [localizer設計](visual-localization.md) | frame ID/撮影時刻照合、2秒期限、停止中のみ受理 | 歩行6DoFは別途tracking / CV担当 |
| P1 | 繰返し窓や似た建物に誤localize | [hloc](https://github.com/cvg/Hierarchical-Localization) | 空間分散・曖昧候補・GPS gate、独立query評価 | low再投影誤差でも誤答あり / CV担当 |
| P1 | OTWの演出形状/材質と実写が一致しない | [current-state-audit.md](current-state-audit.md) | 実写→syntheticと実写→SfMを分けて比較 | 季節/夜/工事でmap劣化 / CV担当 |
| P1 | pose誤差で別の地物へ修正依頼を確定 | [ID設計](reality-observation.md) | candidatesと確定IDを分離、unknownを許可、人間triage | 単画像に複数対象 / 運営 |
| P1 | LOD/mesh統合で地物IDが消える | [Architecture](web-spatial-viewer-architecture.md) | node/primitive sidecar、全配布ID往復、重複置換検査 | 未対応batchはunknown / export担当 |
| P1 | 画像upload・matching待ちで操作が固まる | [性能試算](visual-localization.md) | 非同期、1 in-flight、制限・timeout、1Mbps試験 | 圏外では補正不能 / API担当 |
| P1 | iPhoneの熱・メモリでtabが落ちる | [PoC目標](poc-plan.md) | 5MB/10万tri目標、1K texture、10分試験、dispose | 配布bytesからRAMは予測不能 / Web担当 |
| P1 | SNS内browser、権限拒否、復帰で黒画面 | [Safari開始手順](iphone-web-ar-research.md) | Safari導線、個別permission状態、stream再開試験 | SNSアプリごとに差 / Web担当 |
| P1 | 投稿再送で重複受付・採用、保存失敗を成功表示 | [保存契約](reality-observation.md) | idempotency ID+hash、DB確定後201、障害注入 | offline後送は保証しない / API担当 |
| P1 | 未信頼写真/commentがAIやworkerへ命令として入る | [ai-workflow.md](ai-workflow.md) | 証拠と指示分離、運営scope確定、任意コード実行禁止 | 自動AI pipelineは後続 / 運営 |
| P1 | 観測削除後もdescriptor/mapに残る | [データ依存設計](reality-observation.md) | source_observation_idsから派生物削除/無効化、backup期限 | 外部vendorにも削除能力が必要 / API担当 |
| P2 | 他社VPS coverage/終了/課金変更 | [Immersal](https://developers.immersal.com/docs/rest-api/)、[8th Wall FAQ](https://8thwall.org/docs/migration/faq) | provider adapter、地元mapで試験、料金とlicenseを採用時固定 | 地域coverageは未確認 / 運営 |
| P2 | Visual Mapへの悪意ある投稿・古い画像混入 | [map設計](visual-localization.md) | review前map追加禁止、独立基準、版固定、rollback | 数だけで信用を増やさない / 運営 |
| P2 | viewerとOTWの内部構造が密結合 | [repo境界](web-spatial-viewer-architecture.md) | Web単独build、JSON fixture、versioned API、禁止import検査 | schema進化の移行運用が必要 / Web担当 |
| P2 | geometry更新と旧Observationのversion不一致 | [Observation](reality-observation.md) | 撮影時snapshot不変、world/map/frame版分離、再判定revision | 古い証拠の解釈が必要 / 運営 |
| P2 | NeRF/3DGSを導入して準備・計算量が膨張 | [位置推定比較](visual-localization.md) | PnP方式の測定後に独立実験 | 大規模実装は今回対象外 / CV担当 |

## 実装開始時に解決する順序

1. Safari実機でcamera/permission/描画を確認する。対応しなければasset作成やVPSへ投資する前に停止。
2. 東京タワー圏内の使えるasset、安定ID、座標登録を一件確定。配布権と測地精度を独立に判定。
3. 写真受付を非公開・再送可能にし、既存運営への引き継ぎを一件机上実行。
4. 単画像localizerを比較し、精度・受理率・遅延を実測。失敗しても概略表示/報告の結果を残す。
5. 画像補正が成立した後に、連続tracking、3D Tiles、実写Visual Map拡張を判断する。

## まだ言えないこと

現地での精度、任意iPhoneでのFPS、東京タワーの商用VPS coverage、原本からのGLB配布可否、利用者写真による継続的な位置推定改善は未検証。文書・既存CLIテストの成功をこれらの達成証拠にはしない。最終判断は[PoC成功条件](poc-plan.md)の各gateを使う。
