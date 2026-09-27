# 入口接続修正版を共通city基準へ反映

main `b346d26dd6bda41cbf1057741b1ec50dcefda172` に含まれる[入口接続修正](mori-plaza-connection-v1.md)の保存済みモデルを、共通 `city` の入力に指定します。形状を再生成せず、既存の保存後検証と9視点の比較を再利用します。[前のPR #40基準](city-baseline-pr40.md)と過去の検証記録は保持します。

| 項目 | 採用値 |
|---|---|
| bytes | 559,040,261 |
| SHA-256 | `9c142f54cc85689cb8a8bc00794dfe8e9b6bc9098f121c9fb02cdbc1aa3dbbc4` |
| 内容 | 3,307 objects / 3,257 meshes / 383 packed images |
| Blender | 4.5.1 LTS |
| 比較視点 | 従来7視点＋入口接続の近接2視点 |

[固定lock](../manifests/mori-plaza-connection-accepted.json)、[共通台帳](../manifests/contributor-workspace.json)、[feature設定](../areas/tokyo-tower/mori-plaza-connection-accepted-features.json)を揃えました。空メッシュの例外は従来の5部品に限定し、入力hashだけを更新します。

## 更新

この変更が入ったコード版で、正当な提供元の採用ファイルを指定します。

```powershell
.\otw.ps1 import-city --input 'C:\Received\city-connection.blend'
.\otw.ps1 verify --profile city
.\otw.ps1 edit --profile city --open
```

旧登録は更新が必要な状態になります。importはhash別パスにコピーし、Blenderで読み込み・参照・mesh数を検査してから登録を切り替えます。旧ファイルと編集コピーは残り、編集中の差分は自動移植されません。

## 低コストで確認した範囲

形状・材質・カメラ・描画設定を変えていないため、[既存の実行記録](mori-plaza-connection-v1-run.json)と[保存後検証](mori-plaza-connection-v1-validation.json)を再利用します。再モデリングと再レンダリングは行いません。今回の登録・読み込み・編集コピーとコードの検証は[更新検証記録](city-baseline-connection-verification.json)に記録します。

mainへ取り込む前の実機確認は独立したローカルworkspaceで行い、普段の旧登録を変更しません。共通コードを更新した後に上記のimportで普段の登録も更新できます。

これはモデル内の暫定的な接続改善です。実際の地形・スロープの復元や都市全域の連続性は保証しません。街全体の公開配布は未整備であり、今回の版指定は新しい配布許諾ではありません。
