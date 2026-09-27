# 東京タワー77部品の固定ID（2026-09-27）

鉄骨・展望台・窓・ガラス床などを個別に改修する準備として、許諾対象77部品へ固定IDを追加しました。`provenance.json`を正本とし、独立blendの`otw_part_id`、`parts.json`の`part_id`、旧入力の部品名を対応付けます。表示名・配列順に依存せず、保存後の別Blender processでIDと部品の対応を検査します。形状の作り込みは今回の変更に含みません。

## 再実行

[切り出しCLI](../assets/tokyo-tower/README.md)を使用します。固定した旧PR #12入力が必要です。現行の共通cityはPR #40版のままです。切り出し専用の旧入力を現行cityへ再登録しないでください。

```powershell
python assets/tokyo-tower/export.py --blender BLENDER --input data/local/assets/tokyo-city-pr12/city.blend --output data/local/checks/tower-part-ids-new
python -m unittest discover -s tests
```

`tokyo-tower-part-001`〜`077`は今回一度だけ採番した識別子です。改名・並べ替え・モデル更新で振り直さず、廃止したIDも再利用しません。対象部品の旧名は固定入力のaliasとして保持します。共通registryとの接続・座標検証は未実装です。

## 確認結果

- 起点：main `9d5f1ff`。Windows、Blender 4.5.1 LTS、付属Python 3.11.11。
- 入力：558,751,758 bytes、SHA-256 `98a3932e6dc972d4ae702d264c1e894d77765a9a3a5e57c8a75591eafd42e926`。原本不変を確認。
- 従来exporterと今回exporterを同一入力・設定でそれぞれ実行。77 mesh・1,740,732 triangles、各meshの形状hash・頂点数・面数は一致。
- 保存した独立blendを別processで開き、77 IDの対応、形状hash、外部画像・library・Text・soundがゼロであることを確認。
- 全体・ガラス床・内装の3視点をCycles CPU、960×720、16 samples、seed 0で比較。PNGのファイルhashは異なりますが、Blenderでdecodeした全RGBA画素は3視点とも完全一致しました。
- portable tests：202件実行、197件成功、5件スキップ。欠落・重複・ID取り違え・feature/許諾不一致の拒否、表示名変更・順序変更への耐性を含みます。

[入力・コードhashと結果](tokyo-tower-part-ids-verification.json)。全ログ、Before/Afterのblend・画像・run.jsonはGit対象外の`data/local/checks/tower-part-ids-20260927/`に保存しました。従来exporterは起点commitからローカルへ取り出して使用しています。旧IDなしモデルを新validatorで検査する互換性は提供していません。

現実の寸法や外観精度を新たに確認したものではありません。既存の補助植栽を含む切り出し範囲、推定寸法・内装、周辺都市が含まれない制約を引き継ぎます。次は固定IDを使った対象部品の改修、または配布パッケージと資産hashの固定へ進められます。
