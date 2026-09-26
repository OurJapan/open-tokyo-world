# 共通city基準版をPR #40へ更新

2026-09-27、採用済みの道路・芝生・園路の修正を、街全体を開く共通 `city` プロファイルへ反映しました。これから作る編集コピーと基準画像はPR #40の保存モデルを起点にします。都市形状をさらに変更する更新ではありません。

| 採用内容 | mainへの取り込み |
|---|---|
| 中央広場を道路化した残存面の除去 | [PR #39](https://github.com/OurJapan/open-tokyo-world/pull/39)、`66df406e9f6235698d3ab28d180b710a0238f343` |
| 芝生輪郭の復元・広場の舗装・入口からの推定接続 | [PR #40](https://github.com/OurJapan/open-tokyo-world/pull/40)、`85abf0aac59cad57ca97836ac458115ccbfa28d0` |

## 固定した基準モデル

| 項目 | 値 |
|---|---|
| ファイル容量 | 558,877,024 bytes |
| SHA-256 | `2e2cce08aa581ef6a99d60c9fe993b8c4e53ff7f5cffb687f9d9c4cee19dc544` |
| 内容 | 3,306 objects / 3,256 meshes / 383 packed images |
| Blender参照版 | 4.5.1 LTS |
| 登録先 | `data/local/assets/tokyo-city/<SHA-256>/city.blend` |
| 基準画像 | 中央広場・入口・周囲の道路の固定7視点 |

[共通台帳](../manifests/contributor-workspace.json)、[採用モデルのlock](../manifests/mori-plaza-landscape-accepted.json)、[新しい入力に対応するfeature設定](../areas/tokyo-tower/mori-plaza-landscape-accepted-features.json)で固定します。モデルのhashは[PR #40の実行記録](mori-plaza-landscape-v1-run.json)の `after.blend` と一致します。以前から存在する東京タワーの空メッシュ5件の例外は、そのまま対象を限定して引き継ぎます。

## 以前の登録から更新する

この変更を含むコード版を取得し、正当な提供元から受け取った上記の採用ファイルを指定します。

```powershell
.\otw.ps1 status
.\otw.ps1 import-city --input 'C:\Received\city-pr40.blend'
.\otw.ps1 verify --profile city
.\otw.ps1 edit --profile city --open
```

旧版が登録されていると `status` は `ready_locally: false`、`update_required: true` を返し、現行版の取り込みを案内します。更新前のモデルから、新しい基準に合格した編集コピーを作ることはできません。

取り込みでは入力とコピーのbytes・SHA-256を照合し、Blenderで読み込みと画像・library参照、メッシュ数を確認した後に登録を切り替えます。検査に失敗した場合は以前の登録を保持します。同じ採用版を再登録する場合は、同じhashの保存先を再検査して使います。既存の異なる内容を上書きしません。

旧 `data/local/assets/tokyo-city-pr12/city.blend` と既存の `data/local/edits/` は残ります。過去の編集差分を新しいモデルへ自動移植しません。作業途中の変更は、旧編集コピーとその `edit.json` を参照し、新しい編集コピーへ必要な差分だけを反映して再検証してください。更新直後に作る編集コピーも `validated_edit: false` であり、以後の手編集には独立した検証が必要です。

街全体の公開取得先は引き続き未整備です。cloneだけではモデルを入手できません。[配布準備状況](asset-distribution-readiness.md)を参照してください。

## 実機で確認したこと

同じWindows PCで、旧PR #12の登録状態から更新を実行しました。

- 旧登録の更新案内、PR #40版の別パスへの取り込み、Blenderでの再読み込みが成功しました。
- 3,256 meshes・383 packed imagesを確認し、欠落画像・外部画像・linked libraryはありませんでした。
- 新しい編集コピーは採用モデルのbytesと一致し、編集後未検証の状態で作成されました。
- 元のPR #12モデルと、取り込み元のPR #40ファイルのhashは変わっていません。
- 共通CLIから7視点×Before/Afterを生成しました。640×360、Cycles OptiX、8 samples、seed 0で、変更objectは0です。
- 回帰テスト199件中194件が成功、Blenderを要する単体テスト5件は通常実行ではskipしました。上記の街全体の実機確認は別途実施しています。

[機械可読の検証記録](city-baseline-pr40-verification.json)に入力、実行コード、結果のhashと確認範囲を残しています。旧モデル・画像・編集コピー・絶対パスを含むログはローカルに保持します。

同じ設定で再描画しても画像bytesは完全一致していません。各視点230,400画素中21〜35画素に、RGBA8の1チャンネルで最大1の差がありました。カメラと保存モデルの検査指紋は一致しています。画像の完全一致を、同じ制作環境であることの条件にはしていません。

## 過去の調査と残る課題

[画像照合](city-image-audit.md)、[部品カタログ](city-catalog.md)、[外壁材質の比較候補](city-facades-v1.md)はPR #12を入力とした記録です。その入力lockと再実行経路は維持し、今回の3,256メッシュに対する新規監査とは扱いません。過去の検証JSONも実行時点の記録として保持します。

今回の検査は別PCでの全都市の取得・操作や、モデル全域の正確さを保証しません。実際の階段・傾斜、周囲の道路との高さの接続、旧建物と地図の位置合わせ、混在資産の再配布条件は残っています。次の形状修正は、今回の基準から対象・根拠・変更範囲を決めて比較します。
